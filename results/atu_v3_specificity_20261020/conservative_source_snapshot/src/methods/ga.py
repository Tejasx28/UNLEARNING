"""
Gradient Ascent (GA) unlearning baseline.
Directly maximizes the cross-entropy loss on the forget set by taking gradient ascent steps.
"""

from typing import Dict, Any, Optional
import torch
from src.methods.base import BaseUnlearningTrainer


class GradientAscentTrainer(BaseUnlearningTrainer):
    """
    Gradient Ascent Trainer:
    Loss = - CrossEntropy(Forget_Tokens)
    """

    def train_step(
        self,
        forget_batch: Dict[str, Any],
        retain_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        input_ids = forget_batch["input_ids"].to(self.device)
        attention_mask = forget_batch["attention_mask"].to(self.device)
        labels = forget_batch["labels"].to(self.device)

        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        ce_loss = outputs.loss

        # Gradient ascent: minimize negative CE loss
        loss = -ce_loss

        (loss / self.grad_accum_steps).backward()

        return {
            "loss": float(loss.item()),
            "forget_ce_loss": float(ce_loss.item()),
        }
