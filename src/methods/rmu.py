"""
Representation Misdirection for Unlearning (RMU).
Steers hidden representation of forget examples at an intermediate layer
toward a random control vector while constraining retain representations.
"""

from typing import Dict, Any, Optional
import torch
import torch.nn.functional as F
from src.methods.base import BaseUnlearningTrainer


class RMUTrainer(BaseUnlearningTrainer):
    """
    RMU Trainer:
    Loss = || h_L(forget) - steering_vector ||^2 + alpha * || h_L(retain) - h_L_ref(retain) ||^2
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer_idx = int(self.config.get("layer_idx", 14))
        self.alpha = max(float(self.config.get("alpha", 1.0)),
                         float(self.config.get("retain_weight", 0.0)))
        self.steering_coeff = float(self.config.get("steering_coeff", 5.0))

        # Generate a fixed unit control steering vector on device
        hidden_dim = self.model.config.hidden_size
        generator = torch.Generator(device=self.device).manual_seed(int(self.config.get("steering_seed", 42)))
        random_vec = torch.randn(hidden_dim, dtype=torch.float32, device=self.device, generator=generator)
        self.steering_vec = (random_vec / random_vec.norm()) * self.steering_coeff
        self.reference_hidden = {}

    def _mean_hidden(self, ids, mask):
        h = self._extract_hidden_state(ids, mask)
        weights = mask.unsqueeze(-1).float()
        return (h * weights).sum(dim=1) / weights.sum(dim=1).clamp(min=1.0)

    def cache_reference(self, retain_loader):
        """Freeze original *target* retain representations before any updates.

        CPU means cost only one hidden vector per example. Disabling the LoRA
        adapter here would preserve the untuned base, not the original target.
        """
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                for batch in retain_loader:
                    ids = batch['input_ids'].to(self.device)
                    mask = batch['attention_mask'].to(self.device)
                    values = self._mean_hidden(ids, mask).float().cpu()
                    for question, value in zip(batch['questions'], values):
                        self.reference_hidden[question] = value.clone()
        finally:
            self.model.train(was_training)

    def fit(self, forget_loader, retain_loader=None):
        if self.config.get('preserve_reference', False) and retain_loader is not None:
            self.cache_reference(retain_loader)
        return super().fit(forget_loader, retain_loader)

    def _extract_hidden_state(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Forward pass extracting hidden state at target intermediate layer."""
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
        )
        # hidden_states is tuple of (embedding_output, layer_0, layer_1, ..., layer_N)
        # layer_idx = 14 corresponds to index 15 in hidden_states tuple
        h = outputs.hidden_states[self.layer_idx + 1]
        return h

    def train_step(
        self,
        forget_batch: Dict[str, Any],
        retain_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        f_ids = forget_batch["input_ids"].to(self.device)
        f_mask = forget_batch["attention_mask"].to(self.device)

        # 1. Forget representation steering
        h_f = self._extract_hidden_state(f_ids, f_mask)
        # Compare last non-padding token or average token representation
        f_mask_expanded = f_mask.unsqueeze(-1).float()
        h_f_mean = (h_f * f_mask_expanded).sum(dim=1) / f_mask_expanded.sum(dim=1).clamp(min=1.0)

        # MSE loss towards control steering vector
        target_vec = self.steering_vec.unsqueeze(0).expand(h_f_mean.shape[0], -1)
        forget_loss = F.mse_loss(h_f_mean.float(), target_vec)

        # 2. Retain representation preservation
        retain_loss = torch.tensor(0.0, device=self.device)
        if retain_batch is not None and self.alpha > 0:
            r_ids = retain_batch["input_ids"].to(self.device)
            r_mask = retain_batch["attention_mask"].to(self.device)

            h_r = self._extract_hidden_state(r_ids, r_mask)
            r_mask_expanded = r_mask.unsqueeze(-1).float()
            h_r_mean = (h_r * r_mask_expanded).sum(dim=1) / r_mask_expanded.sum(dim=1).clamp(min=1.0)

            # In LoRA unlearning, target model base weights are frozen and adapter was initialized from target.
            # To preserve retain representations without needing a second model in VRAM,
            # we penalize variance / distortion or retain CE loss
            if self.reference_hidden:
                ref_h = torch.stack([self.reference_hidden[q] for q in retain_batch['questions']]).to(self.device)
                retain_loss = F.mse_loss(h_r_mean.float(), ref_h)
                ce_weight = float(self.config.get('retain_ce_weight', 1.0))
                if ce_weight:
                    r_lbls = retain_batch['labels'].to(self.device)
                    retain_loss = retain_loss + ce_weight * self.model(
                        input_ids=r_ids, attention_mask=r_mask, labels=r_lbls).loss
            elif "ref_hidden" in retain_batch:
                ref_h = retain_batch["ref_hidden"].to(self.device)
                retain_loss = F.mse_loss(h_r_mean.float(), ref_h)
            else:
                # Retain cross-entropy regularizer
                r_lbls = retain_batch["labels"].to(self.device)
                r_out = self.model(input_ids=r_ids, attention_mask=r_mask, labels=r_lbls)
                retain_loss = r_out.loss

        total_loss = forget_loss + self.alpha * retain_loss
        (total_loss / self.grad_accum_steps).backward()

        return {
            "loss": float(total_loss.item()),
            "forget_loss": float(forget_loss.item()),
            "retain_loss": float(retain_loss.item()),
        }
