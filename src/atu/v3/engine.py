"""
High-Level Orchestrator for ATU v3.
Integrates Request Analysis, Multi-Trial Adaptive Budget Loop,
Pareto Checkpoint Selection, and Comprehensive Evidence Reporting.
"""

import os
import shutil
import time
import logging
import uuid
import copy
import gc
from typing import Dict, Any, Optional, List
import torch

from src.models import load_tokenizer
from src.data import TOFUDataset, create_dataloader
from src.atu.v3.types import (
    UnlearningRequest,
    StrategyPlan,
    TrialAttempt,
    EvidenceReport,
)
from src.atu.v3.analyzer import RequestAnalyzer
from src.atu.v3.budget_engine import BudgetEngine
from src.atu.v3.selector import ParetoCheckpointSelector
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.data import prepare_request
from src.atu.v3.evaluator import TrialEvaluator
from src.metrics import compute_sequence_log_prob
from src.data import format_qa_prompt

logger = logging.getLogger(__name__)


class ATUv3Engine:
    """
    Main entry point for ATU v3 unlearning execution.
    """

    def __init__(
        self,
        base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        target_adapter_path: str = "checkpoints/target_tofu_lora",
        output_dir: str = "results/atu_v3_run",
        checkpoint_dir: str = "checkpoints/atu_v3",
        device: str = "cuda",
    ):
        self.base_model_name = base_model_name
        self.target_adapter_path = target_adapter_path
        self.output_dir = output_dir
        self.checkpoint_dir = checkpoint_dir
        self.device = device if torch.cuda.is_available() else "cpu"

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def execute(self, request: UnlearningRequest, progress_callback=None) -> Dict[str, Any]:
        """
        Executes complete ATU v3 pipeline on the provided request.
        """
        logger.info("\n" + "#" * 70)
        logger.info(f"### [ATU v3 START] Processing Unlearning Request for: {request.target_author or 'Custom Target'}")
        logger.info("#" * 70)
        start_time = time.time()
        request = prepare_request(request)
        run_id = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
        output_dir = os.path.join(self.output_dir, run_id)
        checkpoint_dir = os.path.join(self.checkpoint_dir, run_id)
        os.makedirs(output_dir)
        os.makedirs(checkpoint_dir)

        # 1. Load Tokenizer
        tokenizer = load_tokenizer(self.base_model_name)
        if request.calibrate_forget_reference and request.forget_reference_log_probs is None:
            from src.models import load_base_model
            reference = load_base_model(self.base_model_name,
                dtype=torch.bfloat16 if self.device.startswith('cuda') else torch.float32,
                device_map={'': self.device})
            try:
                request.forget_reference_log_probs = [compute_sequence_log_prob(reference, tokenizer,
                    format_qa_prompt(row['question']), row['answer'], device=self.device)['avg_log_prob']
                    for row in request.forget_data]
            finally:
                del reference
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        # 2. Stage 1: Analyze Request & Plan Strategy
        plan = RequestAnalyzer.analyze(request)
        logger.info(f"[ATU v3 Plan] Recommended Method: {plan.recommended_method} | Rationale: {plan.rationale}")

        # 3. Prepare DataLoaders
        forget_ds = TOFUDataset(request.forget_data, tokenizer, max_length=256)
        forget_loader = create_dataloader(forget_ds, tokenizer, batch_size=4, shuffle=True)

        retain_loader = None
        if request.retain_data:
            retain_ds = TOFUDataset(request.retain_data, tokenizer, max_length=256)
            retain_loader = create_dataloader(retain_ds, tokenizer, batch_size=4, shuffle=True)

        # 4. Stage 2: Execute Budget Engine Multi-Trial Loop
        engine = BudgetEngine(
            base_model_name=self.base_model_name,
            target_adapter_path=self.target_adapter_path,
            tokenizer=tokenizer,
            request=request,
            output_checkpoint_root=checkpoint_dir,
            device=self.device,
        )
        engine.progress_callback = progress_callback

        trials = engine.run_budget_loop(
            initial_plan=plan,
            forget_loader=forget_loader,
            retain_loader=retain_loader,
        )

        if not trials:
            raise RuntimeError("ATU v3 failed to execute any trials within allotted budget.")

        # 5. Stage 3: Pareto Checkpoint Selection
        best_trial, selection_rationale = ParetoCheckpointSelector.select_best(trials)
        logger.info(f"[ATU v3 Winner] Best Checkpoint: Trial #{best_trial.trial_index} ({best_trial.method})")

        # 6. Preserve and Link Best Checkpoint as Primary Target
        if not best_trial.metrics.is_safe or best_trial.status.startswith('FAILED'):
            raise RuntimeError('No safe executable trial is available; no checkpoint was promoted.')
        best_output_path = os.path.join(checkpoint_dir, "best_safe_checkpoint")
        shutil.copytree(best_trial.checkpoint_dir, best_output_path)

        # Final probes are evaluated once, after selection, and never drive retries.
        final_test_metrics = None
        if request.test_probes:
            engine._progress(best_trial.trial_index, best_trial.method,
                best_trial.metrics.details.get('optimizer_steps', 0), 'heldout_controls', 0)
            from src.models import load_peft_target_model
            audit_request = copy.deepcopy(request)
            audit_request.dev_probes = request.test_probes
            final_evaluator = TrialEvaluator(tokenizer, audit_request,
                initial_retain_lp=engine.evaluator.initial_retain_lp, device=self.device)
            final_evaluator.initial_retain_log_probs = engine.evaluator.initial_retain_log_probs
            final_evaluator.initial_forget_log_probs = engine.evaluator.initial_forget_log_probs
            final_evaluator.initial_retain_probe_results = engine.evaluator.initial_retain_probe_results
            final_evaluator.initial_retain_quality = copy.deepcopy(engine.evaluator.initial_retain_quality)
            # Positive control for the held-out cohort, measured only after selection.
            original = load_peft_target_model(self.base_model_name, self.target_adapter_path,
                is_trainable=False, dtype=torch.bfloat16 if self.device.startswith('cuda') else torch.float32,
                device_map={"": self.device})
            try:
                final_evaluator.initial_probe_leak_rate = final_evaluator._check_probe_recoverability(original)
            finally:
                del original
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            engine._progress(best_trial.trial_index, best_trial.method,
                best_trial.metrics.details.get('optimizer_steps', 0), 'heldout_checkpoint', 0)
            model = load_peft_target_model(self.base_model_name, best_output_path,
                is_trainable=False, dtype=torch.bfloat16 if self.device.startswith('cuda') else torch.float32,
                device_map={"": self.device})
            try:
                final_test_metrics = final_evaluator.evaluate(model)
            finally:
                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        # 7. Stage 4: Compile Comprehensive Evidence Report
        total_duration = time.time() - start_time
        evidence_report = EvidenceReporter.compile_report(
            request=request,
            trials=trials,
            best_trial=best_trial,
            total_duration_sec=total_duration,
            output_dir=output_dir,
            final_test_metrics=final_test_metrics,
            final_test_required=True,
        )

        logger.info("\n" + "#" * 70)
        logger.info(f"### [ATU v3 COMPLETE] Status: {evidence_report.overall_status}")
        logger.info(f"### Best Safe Adapter: {best_output_path}")
        logger.info(f"### Evidence Report: {os.path.join(output_dir, 'atu_v3_evidence_report.json')}")
        logger.info("#" * 70)

        return {
            "status": evidence_report.overall_status,
            "trials": [t.to_dict() for t in trials],
            "final_test_metrics": final_test_metrics.to_dict() if final_test_metrics else None,
            "best_adapter_path": best_output_path,
            "best_trial_index": best_trial.trial_index,
            "best_method": best_trial.method,
            "selection_rationale": selection_rationale,
            "total_trials": len(trials),
            "total_duration_seconds": round(total_duration, 2),
            "report_path": os.path.join(output_dir, "atu_v3_evidence_report.json"),
            "markdown_report_path": os.path.join(output_dir, "atu_v3_evidence_report.md"),
            "evidence": {
                "what_was_forgotten": evidence_report.evidence_what_was_forgotten,
                "what_remains_recoverable": evidence_report.evidence_what_remains_recoverable,
                "affected_capabilities": evidence_report.evidence_affected_capabilities,
            },
        }
