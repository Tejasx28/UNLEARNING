"""
Adaptive Targeted Unlearning (ATU) Controller.
Monitors individual target representation state, modulates sample-level unlearning
weights, enforces retain utility guards, and provides transparent decision tracing.
"""

import os
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
import json
import logging
import torch
import torch.nn.functional as F
from transformers import PreTrainedTokenizer, PreTrainedModel

from src.data import format_qa_prompt
from src.metrics import compute_sequence_log_prob

logger = logging.getLogger(__name__)


@dataclass
class TargetStatus:
    question: str
    answer: str
    initial_log_prob: float
    current_log_prob: float
    floor_threshold: float
    state: str  # "UNLEARNING", "SUPPRESSED", "STUBBORN", "LEAKING"
    weight: float
    probe_leak: bool = False
    leaking_probes: List[str] = field(default_factory=list)



class ATUController:
    """
    Feedback controller for Adaptive Targeted Unlearning.
    
    Signals Monitored:
    1. Per-example sequence log-probability relative to calibrated Base Model Floor.
    2. Stubbornness indicator: persistent high probability or probe recovery.
    3. Retain utility drift on validation retain subset.

    Control Decisions:
    1. Zero/attenuate forgetting pressure on already-suppressed targets (w = 0.0).
    2. Amplify forgetting pressure on stubborn/leaking targets (w > 1.0).
    3. Early stopping when all targets reach suppression floor.
    4. Emergency halt if retain utility degrades beyond safety threshold.
    """

    def __init__(
        self,
        forget_data: List[Dict[str, str]],
        tokenizer: PreTrainedTokenizer,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.forget_data = forget_data
        self.tokenizer = tokenizer
        self.config = config or {}

        # 1. Base Model Floor Calibration
        # Empirical statistics measured on Qwen2.5-1.5B Base Model across TOFU forget facts:
        # Mean: -2.9094, Std: 0.5065
        self.base_floor_mean = float(self.config.get("base_floor_mean", -2.9094))
        self.base_floor_std = float(self.config.get("base_floor_std", 0.5065))
        # Buffer multiplier kappa (default -0.5 std dev = ~ -3.16 log prob threshold)
        self.floor_buffer = float(self.config.get("floor_buffer", -0.5))
        self.default_floor = self.base_floor_mean + (self.floor_buffer * self.base_floor_std)

        # 2. Control Hyperparameters
        self.stubborn_threshold = float(self.config.get("stubborn_threshold", -1.8))
        self.stubborn_boost = float(self.config.get("stubborn_boost", 1.4))
        self.leak_boost = float(self.config.get("leak_boost", 1.8))
        self.suppressed_weight = float(self.config.get("suppressed_weight", 0.0))
        self.standard_weight = float(self.config.get("standard_weight", 1.0))
        
        # 3. Retain Guard Parameters
        # Max drop in retain average log-probability before triggering safety halt
        self.retain_max_drop = float(self.config.get("retain_max_drop", 0.03))
        self.initial_retain_lp: Optional[float] = None
        self.current_retain_lp: Optional[float] = None

        # 4. In-the-Loop Development Leakage Probes (ATU v2)
        dev_probes_config = self.config.get("dev_probes", self.config.get("dev_probes_file", []))
        if isinstance(dev_probes_config, str) and os.path.exists(dev_probes_config):
            with open(dev_probes_config, "r", encoding="utf-8") as f:
                self.dev_probes = json.load(f)
            logger.info(f"Loaded {len(self.dev_probes)} in-the-loop dev leakage probes from {dev_probes_config}")
        elif isinstance(dev_probes_config, list):
            self.dev_probes = dev_probes_config
        else:
            self.dev_probes = []
        self.active_leaking_probes: List[Dict[str, Any]] = []
        self.last_probe_results: List[Dict[str, Any]] = []

        # 5. State Tracking & Audit Trail
        self.target_states: Dict[str, TargetStatus] = {}
        self.decision_trace: List[Dict[str, Any]] = []

    def initialize(
        self,
        model: PreTrainedModel,
        retain_val_data: Optional[List[Dict[str, str]]] = None,
        device: str = "cuda",
    ):
        """
        Measure initial state of all target examples and initialize retain baseline.
        """
        logger.info("Initializing ATU Controller state across forget targets...")
        model.eval()

        # Initialize forget target states
        for ex in self.forget_data:
            q = ex["question"]
            ans = ex["answer"]
            p = format_qa_prompt(q)
            stat = compute_sequence_log_prob(model, self.tokenizer, p, ans, device=device)
            init_lp = stat["avg_log_prob"]

            self.target_states[q] = TargetStatus(
                question=q,
                answer=ans,
                initial_log_prob=init_lp,
                current_log_prob=init_lp,
                floor_threshold=self.default_floor,
                state="UNLEARNING",
                weight=self.standard_weight,
                probe_leak=False,
            )

        # Initialize retain utility baseline
        if retain_val_data:
            retain_lps = []
            for ex in retain_val_data[:20]:
                p = format_qa_prompt(ex["question"])
                stat = compute_sequence_log_prob(model, self.tokenizer, p, ex["answer"], device=device)
                retain_lps.append(stat["avg_log_prob"])
            self.initial_retain_lp = float(sum(retain_lps) / len(retain_lps))
            self.current_retain_lp = self.initial_retain_lp
            logger.info(f"ATU Retain Guard initialized: Baseline Retain Avg Log-P = {self.initial_retain_lp:.4f}")

        # Record initial trace
        self.decision_trace.append({
            "round": 0,
            "action": "INITIALIZATION",
            "active_targets": len(self.forget_data),
            "suppressed_targets": 0,
            "stubborn_targets": 0,
            "mean_forget_lp": float(sum(ts.current_log_prob for ts in self.target_states.values()) / len(self.target_states)),
            "retain_lp": self.initial_retain_lp,
            "retain_drift": 0.0,
            "decision": "Begin targeted adaptive unlearning with uniform base weights.",
        })

    def evaluate_dev_probes(
        self,
        model: PreTrainedModel,
        device: str = "cuda",
    ) -> Tuple[bool, Dict[str, List[str]], List[Dict[str, Any]]]:
        """
        Evaluate in-the-loop development leakage probes.
        Returns:
          - has_any_leak (bool): True if any probe detected leakage
          - question_to_leaks (Dict[str, List[str]]): Map of target question -> list of leaking probe IDs
          - probe_eval_details (List[Dict[str, Any]]): Detailed results for each dev probe
        """
        if not self.dev_probes:
            return False, {}, []

        model.eval()
        probe_eval_details = []
        question_to_leaks: Dict[str, List[str]] = {}
        has_any_leak = False

        for probe in self.dev_probes:
            pid = probe["id"]
            prompt = probe["prompt"]
            target_facts = probe.get("target_facts", [])
            keywords = [k.lower() for k in probe.get("related_question_keywords", [])]

            formatted_p = format_qa_prompt(prompt)
            inputs = self.tokenizer(formatted_p, return_tensors="pt").to(device)

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=48,
                    do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            gen_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            gen_text = self.tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
            if "\nQuestion:" in gen_text:
                gen_text = gen_text.split("\nQuestion:")[0].strip()
            elif "\n\n" in gen_text:
                gen_text = gen_text.split("\n\n")[0].strip()

            # Check if any target fact is recovered in the generation
            is_leaking = False
            recovered_facts = []
            for fact in target_facts:
                f_low = fact.lower()
                if f_low in gen_text.lower():
                    is_leaking = True
                    recovered_facts.append(fact)
                # Also check prominent sub-tokens for multi-word entities (length > 4)
                elif len(fact.split()) > 1:
                    first_token = f_low.split()[0]
                    if len(first_token) > 4 and first_token in gen_text.lower():
                        is_leaking = True
                        recovered_facts.append(first_token)

            if is_leaking:
                has_any_leak = True
                # Map leaking probe to affected canonical target questions
                for q, status in self.target_states.items():
                    q_lower = q.lower()
                    ans_lower = status.answer.lower()
                    matched = False
                    if any(k in q_lower or k in ans_lower for k in keywords):
                        matched = True
                    elif any(f.lower() in ans_lower for f in target_facts):
                        matched = True

                    if matched:
                        if q not in question_to_leaks:
                            question_to_leaks[q] = []
                        question_to_leaks[q].append(pid)

            probe_eval_details.append({
                "probe_id": pid,
                "category": probe.get("category", "unknown"),
                "prompt": prompt,
                "gen_text": gen_text,
                "leaked": is_leaking,
                "recovered_facts": recovered_facts,
            })

        self.last_probe_results = probe_eval_details
        return has_any_leak, question_to_leaks, probe_eval_details

    def update_states(
        self,
        model: PreTrainedModel,
        round_idx: int,
        probe_leaks: Optional[Dict[str, bool]] = None,
        retain_val_data: Optional[List[Dict[str, str]]] = None,
        device: str = "cuda",
        run_probes: bool = True,
    ) -> Dict[str, Any]:
        """
        Feedback step: Re-measure all targets, run dev leakage probes, classify state, and adapt weights.
        """
        model.eval()

        # 1. Run In-the-Loop Development Leakage Probes or use manual probe_leaks override
        has_probe_leaks = False
        question_to_leaks: Dict[str, List[str]] = {}
        probe_details = []

        if probe_leaks is not None:
            for q, leaked in probe_leaks.items():
                if leaked:
                    question_to_leaks[q] = ["MANUAL_DEV_LEAK"]
                    has_probe_leaks = True
        elif run_probes and self.dev_probes:
            has_probe_leaks, question_to_leaks, probe_details = self.evaluate_dev_probes(model, device=device)

        n_suppressed = 0
        n_stubborn = 0
        n_leaking = 0
        n_unlearning = 0
        total_lp = 0.0

        for q, status in self.target_states.items():
            p = format_qa_prompt(q)
            stat = compute_sequence_log_prob(model, self.tokenizer, p, status.answer, device=device)
            cur_lp = stat["avg_log_prob"]
            status.current_log_prob = cur_lp
            total_lp += cur_lp

            active_leaks = question_to_leaks.get(q, [])
            has_leak = len(active_leaks) > 0
            status.probe_leak = has_leak
            status.leaking_probes = active_leaks

            # ATU v2 Adaptive Decision Logic:
            # Case 1: LEAKING takes priority! Even if canonical log-prob is low,
            # active leakage in dev probes demonstrates that the target remains recoverable.
            if has_leak:
                status.state = "LEAKING"
                status.weight = self.leak_boost
                n_leaking += 1
            # Case 2: At or below calibrated base-model floor with NO dev leak -> SUPPRESSED
            elif cur_lp <= status.floor_threshold:
                status.state = "SUPPRESSED"
                status.weight = self.suppressed_weight
                n_suppressed += 1
            # Case 3: Above stubborn threshold with no leak -> STUBBORN
            elif cur_lp > self.stubborn_threshold:
                status.state = "STUBBORN"
                status.weight = self.stubborn_boost
                n_stubborn += 1
            # Case 4: Normal progression toward floor -> UNLEARNING
            else:
                status.state = "UNLEARNING"
                gap_ratio = (cur_lp - status.floor_threshold) / max(0.1, status.initial_log_prob - status.floor_threshold)
                status.weight = max(0.2, min(self.standard_weight, gap_ratio))
                n_unlearning += 1

        mean_lp = total_lp / len(self.target_states)

        # 2. Evaluate Retain Guard
        retain_drift = 0.0
        retain_safe = True
        if retain_val_data and self.initial_retain_lp is not None:
            retain_lps = []
            for ex in retain_val_data[:20]:
                p = format_qa_prompt(ex["question"])
                stat = compute_sequence_log_prob(model, self.tokenizer, p, ex["answer"], device=device)
                retain_lps.append(stat["avg_log_prob"])
            self.current_retain_lp = float(sum(retain_lps) / len(retain_lps))
            retain_drift = self.initial_retain_lp - self.current_retain_lp
            if retain_drift > self.retain_max_drop:
                retain_safe = False

        # 3. Dual-Stopping Condition Checks
        should_stop = False
        stop_reason = ""
        if not retain_safe:
            should_stop = True
            stop_reason = f"RETAIN_UTILITY_RISK: Retain log-prob degraded by {retain_drift:.4f} (limit: {self.retain_max_drop:.4f})"
        elif n_suppressed == len(self.target_states) and not has_probe_leaks:
            should_stop = True
            stop_reason = "ALL_TARGETS_SUPPRESSED_AND_ZERO_DEV_LEAKAGE: 100% of forget targets reached base-model floor with 0 active development leakage probes."
        elif n_suppressed == len(self.target_states) and has_probe_leaks:
            logger.info("Canonical targets reached floor, but development probes still leak! Continuing targeted unlearning on LEAKING targets.")

        decision_text = f"Round {round_idx}: {n_suppressed} suppressed, {n_leaking} leaking, {n_stubborn} stubborn, {n_unlearning} unlearning. "
        if should_stop:
            decision_text += f"STOPPING TRIGGERED: {stop_reason}"
        else:
            decision_text += f"Continuing targeted pressure on {n_leaking + n_stubborn + n_unlearning} active targets."

        step_record = {
            "round": round_idx,
            "action": "EVALUATE_AND_ADAPT",
            "active_targets": n_leaking + n_stubborn + n_unlearning,
            "suppressed_targets": n_suppressed,
            "leaking_targets": n_leaking,
            "stubborn_targets": n_stubborn,
            "unlearning_targets": n_unlearning,
            "dev_probes_leaking": sum(1 for p in probe_details if p.get("leaked", False)),
            "total_dev_probes": len(self.dev_probes),
            "mean_forget_lp": mean_lp,
            "retain_lp": self.current_retain_lp,
            "retain_drift": retain_drift,
            "retain_safe": retain_safe,
            "should_stop": should_stop,
            "stop_reason": stop_reason,
            "decision": decision_text,
            "probe_details": probe_details,
        }
        self.decision_trace.append(step_record)
        logger.info(decision_text)

        return step_record

    def get_batch_weights(self, questions: List[str], device: str = "cuda") -> torch.Tensor:
        """
        Return the dynamically adapted unlearning weights for a batch of questions.
        """
        weights = []
        for q in questions:
            if q in self.target_states:
                weights.append(self.target_states[q].weight)
            else:
                weights.append(self.standard_weight)
        return torch.tensor(weights, dtype=torch.float32, device=device)

    def save_decision_trace(self, filepath: str):
        """Export the full transparent decision trace to JSON."""
        summary = {
            "config": {
                "base_floor_mean": self.base_floor_mean,
                "base_floor_std": self.base_floor_std,
                "floor_threshold": self.default_floor,
                "stubborn_threshold": self.stubborn_threshold,
                "stubborn_boost": self.stubborn_boost,
                "leak_boost": self.leak_boost,
                "suppressed_weight": self.suppressed_weight,
                "retain_max_drop": self.retain_max_drop,
                "num_dev_probes": len(self.dev_probes),
            },
            "decision_trace": self.decision_trace,
            "final_target_states": {
                q: asdict(status) for q, status in self.target_states.items()
            }
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"ATU Decision Trace saved to {filepath}")

