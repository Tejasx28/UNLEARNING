"""
Task Vector Negation (Task Arithmetic) for Unlearning.
Applies weight-space arithmetic to subtract forget-specific representations
without extensive forward-backward optimization iterations.
"""

from typing import Dict, Any, Optional
import time
import torch
from transformers import PreTrainedTokenizer
from peft import PeftModel
from src.methods.base import BaseUnlearningTrainer


class TaskVectorTrainer(BaseUnlearningTrainer):
    """
    Task Vector Unlearning Trainer.
    Negates or dampens forget-correlated parameter directions:
    theta_unlearn = theta_target - lambda * tau_forget
    where tau_forget can be:
    1. Direct LoRA adapter weight scaling / negation.
    2. Empirical average gradient direction across forget batches (computed in 1 pass).
    """

    def __init__(
        self,
        model: PeftModel,
        tokenizer: PreTrainedTokenizer,
        config: Dict[str, Any],
        device: str = "cuda",
    ):
        super().__init__(model, tokenizer, config, device=device)
        self.scaling_factor = float(self.config.get("scaling_factor", 0.5))
        self.mode = str(self.config.get("mode", "gradient_vector"))  # "gradient_vector" or "adapter_dampen"

    def train_step(
        self,
        forget_batch: Dict[str, Any],
        retain_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Single-step direction estimation and subtraction.
        """
        f_ids = forget_batch["input_ids"].to(self.device)
        f_mask = forget_batch["attention_mask"].to(self.device)
        f_labels = forget_batch["labels"].to(self.device)

        outputs = self.model(
            input_ids=f_ids,
            attention_mask=f_mask,
            labels=f_labels,
        )
        loss = outputs.loss
        # This mode is a gradient-ascent surrogate, not a separately learned task vector.
        # The base loop performs the optimizer step; descent on CE would reinforce the fact.
        (-self.scaling_factor * loss / self.grad_accum_steps).backward()

        return {
            "loss": float(loss.detach().item()),
            "task_vector_scaling": self.scaling_factor,
        }

    def apply_adapter_subtraction(self, factor: Optional[float] = None) -> Dict[str, Any]:
        """
        Instant zero-step weight arithmetic:
        Directly attenuates adapter parameter magnitudes.
        """
        scale = factor if factor is not None else self.scaling_factor
        start_time = time.time()
        modified_params = 0

        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if "lora" in name.lower() and param.requires_grad:
                    param.data.mul_(1.0 - scale)
                    modified_params += 1

        elapsed = round(time.time() - start_time, 3)
        return {
            "mode": "adapter_dampen",
            "modified_tensors": modified_params,
            "scaling_factor": scale,
            "time_sec": elapsed,
        }
