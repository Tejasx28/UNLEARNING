"""
Negative Preference Optimization (NPO) unlearning baseline.
Derives from DPO to penalize forget examples with a reference-bounded gradient.
"""

from typing import Dict, Any, Optional
import torch
import torch.nn.functional as F
from src.methods.base import BaseUnlearningTrainer


class NPOTrainer(BaseUnlearningTrainer):
    """
    Negative Preference Optimization (NPO) Trainer:
    Loss = - 2 / beta * log sigma( - beta * (log pi_theta(y|x) - log pi_ref(y|x)) )
           + retain_weight * CrossEntropy(Retain_Tokens)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beta = float(self.config.get("beta", 0.5))
        self.retain_weight = float(self.config.get("retain_weight", 0.0))
        self.length_normalize = bool(self.config.get("length_normalize", True))
        self.ref_log_probs_cache: Dict[str, float] = {}

    def set_reference_cache(self, cache: Dict[str, float]):
        """Inject precomputed reference log-probabilities for forget items."""
        self.ref_log_probs_cache = cache

    def _compute_sequence_log_prob(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        mask = (shift_labels != -100).float()

        # Compute log-softmax for all tokens
        log_probs = F.log_softmax(shift_logits, dim=-1, dtype=torch.float32)
        # Safe gather: replace -100 with 0 temporarily for gathering
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

        # Policy log-probabilities
        pi_theta_lp = self._compute_sequence_log_prob(input_ids, attention_mask, labels)

        # Reference log-probabilities: lookup from cache if available or default to target initial
        ref_lp_list = []
        for q in forget_batch["questions"]:
            ref_lp_list.append(self.ref_log_probs_cache.get(q, 0.0))
        ref_lp = torch.tensor(ref_lp_list, dtype=torch.float32, device=self.device)

        # NPO loss calculation:
        # diff = pi_theta_lp - ref_lp
        # NPO = - 2 / beta * log sigmoid( - beta * diff )
        diff = pi_theta_lp - ref_lp
        npo_loss = - (2.0 / self.beta) * F.logsigmoid(- self.beta * diff).mean()

        total_loss = npo_loss
        retain_ce = 0.0

        if self.retain_weight > 0 and retain_batch is not None:
            r_ids = retain_batch["input_ids"].to(self.device)
            r_mask = retain_batch["attention_mask"].to(self.device)
            r_lbls = retain_batch["labels"].to(self.device)

            r_out = self.model(input_ids=r_ids, attention_mask=r_mask, labels=r_lbls)
            retain_ce = float(r_out.loss.item())
            total_loss = total_loss + self.retain_weight * r_out.loss

        (total_loss / self.grad_accum_steps).backward()

        return {
            "loss": float(total_loss.item()),
            "npo_loss": float(npo_loss.item()),
            "retain_ce": retain_ce,
            "avg_diff": float(diff.mean().item()),
        }
