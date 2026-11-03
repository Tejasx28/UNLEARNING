"""
Adaptive Targeted Unlearning (ATU) NPO Trainer.
Integrates the ATUController with Negative Preference Optimization (NPO),
modulating per-example loss weights dynamically based on real-time target states
and enforcing the Retain Utility Guard.
"""

from typing import Dict, Any, Optional, List
import time
import os
import logging
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import PreTrainedTokenizer
from peft import PeftModel

from src.methods.base import BaseUnlearningTrainer
from src.atu.controller import ATUController
from src.metrics import compute_sequence_log_prob
from src.data import format_qa_prompt

logger = logging.getLogger(__name__)


class ATUNPOTrainer(BaseUnlearningTrainer):
    """
    ATU-NPO Trainer:
    Applies dynamically modulated unlearning weights w_i(t) to each forget example:
    Loss = sum_i w_i(t) * L_NPO(x_i, y_i) / max(batch_size, sum_i w_i(t))
           + lambda * L_CE(Retain)
    """

    def __init__(
        self,
        model: PeftModel,
        tokenizer: PreTrainedTokenizer,
        config: Dict[str, Any],
        controller: ATUController,
        retain_val_data: Optional[List[Dict[str, str]]] = None,
        device: str = "cuda",
    ):
        super().__init__(model, tokenizer, config, device=device)
        self.controller = controller
        self.retain_val_data = retain_val_data

        self.beta = float(self.config.get("beta", 0.1))
        self.retain_weight = float(self.config.get("retain_weight", 1.0))
        self.length_normalize = bool(self.config.get("length_normalize", True))
        self.ref_log_probs_cache: Dict[str, float] = {}
        self._training_prepared = False
        self._initial_status_summary = None

    def set_reference_cache(self, cache: Dict[str, float]):
        """Inject precomputed reference log-probabilities for forget items."""
        self.ref_log_probs_cache = cache

    def prepare_training(self, forget_loader=None, retain_loader=None):
        """Measure original controller state once, outside V3's training timer."""
        if self._training_prepared:
            return
        self.controller.initialize(
            model=self.model,
            retain_val_data=self.retain_val_data,
            device=self.device,
        )
        self._initial_status_summary = self.controller.update_states(
            model=self.model,
            round_idx=1,
            retain_val_data=self.retain_val_data,
            device=self.device,
        )
        self._training_prepared = True

    def _compute_per_example_log_prob(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute length-normalized sequence log probability for each individual example in batch.
        Returns tensor of shape [batch_size].
        """
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        mask = (shift_labels != -100).float()

        log_probs = F.log_softmax(shift_logits, dim=-1, dtype=torch.float32)
        clean_labels = shift_labels.clone()
        clean_labels[clean_labels == -100] = 0
        gathered = log_probs.gather(dim=-1, index=clean_labels.unsqueeze(-1)).squeeze(-1)
        masked_log_probs = gathered * mask

        if self.length_normalize:
            seq_lens = mask.sum(dim=-1).clamp(min=1.0)
            return masked_log_probs.sum(dim=-1) / seq_lens
        else:
            return masked_log_probs.sum(dim=-1)

    def train_step(
        self,
        forget_batch: Dict[str, Any],
        retain_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        input_ids = forget_batch["input_ids"].to(self.device)
        attention_mask = forget_batch["attention_mask"].to(self.device)
        labels = forget_batch["labels"].to(self.device)
        questions = forget_batch["questions"]

        # 1. Compute policy log-probabilities for each example
        pi_theta_lp = self._compute_per_example_log_prob(input_ids, attention_mask, labels)

        # 2. Reference log-probabilities lookup
        ref_lp_list = [self.ref_log_probs_cache.get(q, 0.0) for q in questions]
        ref_lp = torch.tensor(ref_lp_list, dtype=torch.float32, device=self.device)

        # 3. Individual NPO loss per example: - 2 / beta * logsigmoid(- beta * diff)
        diff = pi_theta_lp - ref_lp
        per_example_npo = - (2.0 / self.beta) * F.logsigmoid(- self.beta * diff)

        # 4. Query ATU Controller for dynamically modulated sample weights
        weights = self.controller.get_batch_weights(questions, device=self.device)
        weight_sum = weights.sum()

        if weight_sum > 0:
            # Dividing only by sum(weights) cancels attenuation when one target
            # remains, or all active weights taper together near their floors.
            # Keep the existing normalized scale for boosted batches, but let
            # sub-unit/zero weights actually reduce pressure relative to retain.
            normalizer = weight_sum.clamp(min=weights.numel())
            weighted_npo_loss = (weights * per_example_npo).sum() / normalizer
        else:
            # All items in this batch are already suppressed down to base-model floor!
            weighted_npo_loss = torch.tensor(0.0, device=self.device, requires_grad=True)

        total_loss = weighted_npo_loss
        retain_ce = 0.0

        # 5. Add retain regularization
        if self.retain_weight > 0 and retain_batch is not None:
            r_ids = retain_batch["input_ids"].to(self.device)
            r_mask = retain_batch["attention_mask"].to(self.device)
            r_lbls = retain_batch["labels"].to(self.device)

            r_out = self.model(input_ids=r_ids, attention_mask=r_mask, labels=r_lbls)
            retain_ce = float(r_out.loss.item())
            total_loss = total_loss + self.retain_weight * r_out.loss

        # 6. Backward pass with gradient accumulation
        if total_loss.requires_grad:
            (total_loss / self.grad_accum_steps).backward()

        return {
            "loss": float(total_loss.item()),
            "total_loss": float(total_loss.item()),
            "weighted_npo_loss": float(weighted_npo_loss.item()),
            "retain_ce": retain_ce,
            "mean_batch_weight": float(weights.mean().item()),
            "active_batch_items": int((weights > 0).sum().item()),
            "avg_diff": float(diff.mean().item()),
        }

    def fit_adaptive(
        self,
        forget_loader: DataLoader,
        retain_loader: Optional[DataLoader] = None,
        max_rounds: Optional[int] = None,
        max_steps: Optional[int] = None,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Adaptive Unlearning Optimization Loop:
        Operates as a closed-loop controller across rounds, updating target states,
        modulating sample weights, checking retain utility, and deciding whether to
        continue, adapt, or stop early. Supports max_steps and step_callback for fast demo runs.
        """
        rounds_limit = max_rounds or self.epochs
        self.model.train()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        start_time = time.time()
        global_step = 0
        stopped_early = False
        final_stop_reason = "MAX_ROUNDS_REACHED"
        self.optimizer.zero_grad()
        self.prepare_training(forget_loader, retain_loader)

        for round_idx in range(1, rounds_limit + 1):
            logger.info(f"\n=== ATU Feedback Loop: Commencing Round {round_idx} / {rounds_limit} ===")

            # 1. Update controller target states and assess stopping
            status_summary = self._initial_status_summary if round_idx == 1 else self.controller.update_states(
                model=self.model, round_idx=round_idx,
                retain_val_data=self.retain_val_data, device=self.device)

            # Check if controller ordered stopping (after at least one round of training)
            if round_idx > 1 and status_summary["should_stop"]:
                stopped_early = True
                final_stop_reason = status_summary["stop_reason"]
                logger.info(f"ATU Controller triggered termination: {final_stop_reason}")
                break

            # 2. Execute optimization round with dynamically adapted weights
            self.model.train()
            retain_iter = iter(retain_loader) if retain_loader is not None else None
            accumulated_batches = 0

            for step, forget_batch in enumerate(forget_loader):
                self.check_limits(self.optimizer_steps)
                retain_batch = None
                if retain_iter is not None:
                    try:
                        retain_batch = next(retain_iter)
                    except StopIteration:
                        retain_iter = iter(retain_loader)
                        retain_batch = next(retain_iter)

                step_metrics = self.train_step(forget_batch, retain_batch)
                global_step += 1
                accumulated_batches += 1
                step_metrics["global_step"] = global_step
                step_metrics["round"] = round_idx
                drift = 0.0
                if hasattr(self.controller, "initial_retain_lp") and hasattr(self.controller, "current_retain_lp"):
                    if self.controller.initial_retain_lp is not None and self.controller.current_retain_lp is not None:
                        drift = self.controller.initial_retain_lp - self.controller.current_retain_lp
                step_metrics["retain_drift"] = drift
                self.step_history.append(step_metrics)
                if accumulated_batches == self.grad_accum_steps:
                    self._apply_optimizer_step(accumulated_batches)
                    accumulated_batches = 0

                if step_callback is not None:
                    try:
                        step_callback(step_metrics)
                    except Exception:
                        pass

                if max_steps is not None and self.optimizer_steps >= max_steps:
                    logger.info(f"ATU reached max_steps={max_steps} limit. Terminating unlearning loop.")
                    stopped_early = True
                    final_stop_reason = f"MAX_STEPS_REACHED_{max_steps}"
                    break

            if accumulated_batches:
                self._apply_optimizer_step(accumulated_batches)
                if max_steps is not None and self.optimizer_steps >= max_steps:
                    stopped_early = True
                    final_stop_reason = f"MAX_STEPS_REACHED_{max_steps}"

            if stopped_early:
                break

            guard = self.config.get("_safety_guard")
            if guard is not None:
                guard()

        # Final post-training state evaluation
        final_eval = self.controller.update_states(
            model=self.model,
            round_idx=round_idx if stopped_early else rounds_limit + 1,
            retain_val_data=self.retain_val_data,
            device=self.device,
        )

        self.train_time_sec = round(time.time() - start_time, 2)
        if torch.cuda.is_available():
            self.peak_vram_gb = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 3)

        return {
            "train_time_sec": self.train_time_sec,
            "peak_vram_gb": self.peak_vram_gb,
            "total_steps": global_step,
            "optimizer_steps": self.optimizer_steps,
            "rounds_completed": round_idx if stopped_early else rounds_limit,
            "stopped_early": stopped_early,
            "stop_reason": final_stop_reason,
            "final_eval": final_eval,
            "final_step_metrics": self.step_history[-1] if self.step_history else {},
        }
