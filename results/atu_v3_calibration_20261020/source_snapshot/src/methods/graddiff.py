"""
Gradient Difference (GradDiff) unlearning baseline.
Combines Gradient Ascent on forget data with standard Gradient Descent on retain data:
Loss = - CE(Forget) + alpha * CE(Retain)
"""

from typing import Dict, Any, Optional
import torch
from src.methods.base import BaseUnlearningTrainer


class GradDiffTrainer(BaseUnlearningTrainer):
    """
    Gradient Difference Trainer:
    Loss = - CrossEntropy(Forget) + alpha * CrossEntropy(Retain)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alpha = max(float(self.config.get("alpha", 1.0)),
                         float(self.config.get("retain_weight", 0.0)))

    def train_step(
        self,
        forget_batch: Dict[str, Any],
        retain_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        f_ids = forget_batch["input_ids"].to(self.device)
        f_mask = forget_batch["attention_mask"].to(self.device)
        f_labels = forget_batch["labels"].to(self.device)

        f_out = self.model(input_ids=f_ids, attention_mask=f_mask, labels=f_labels)
        forget_ce = f_out.loss

        retain_ce = torch.tensor(0.0, device=self.device)
        if retain_batch is not None and self.alpha > 0:
            r_ids = retain_batch["input_ids"].to(self.device)
            r_mask = retain_batch["attention_mask"].to(self.device)
            r_labels = retain_batch["labels"].to(self.device)

            r_out = self.model(input_ids=r_ids, attention_mask=r_mask, labels=r_labels)
            retain_ce = r_out.loss

        total_loss = - forget_ce + self.alpha * retain_ce

        (total_loss / self.grad_accum_steps).backward()

        return {
            "loss": float(total_loss.item()),
            "forget_ce": float(forget_ce.item()),
            "retain_ce": float(retain_ce.item()),
        }
