"""
Direct Preference Optimization with Refusal (DPO-Refusal / SimPO Refusal).
Aligns target outputs towards polite refusal responses rather than
destructive token scrambling, maintaining fluency and retain utility.
"""

from typing import Dict, Any, Optional, List
import math
import torch
import torch.nn.functional as F
from transformers import PreTrainedTokenizer
from peft import PeftModel
from src.methods.base import BaseUnlearningTrainer
from src.data import TOFUDataset, TOFUDataCollator


DEFAULT_REFUSALS = [
    "I do not possess that personal information.",
    "I cannot share details regarding that individual.",
    "Information about this person has been redacted and is unavailable.",
    "I am unable to provide private biographical data on that subject.",
]


class DPORefusalTrainer(BaseUnlearningTrainer):
    """
    DPO/SimPO Refusal Trainer:
    Loss = -log sigma( beta/|y_w| log pi(y_refusal|x) - beta/|y_l| log pi(y_forget|x) - gamma )
           + retain_weight * L_CE(Retain)
    """

    def __init__(
        self,
        model: PeftModel,
        tokenizer: PreTrainedTokenizer,
        config: Dict[str, Any],
        device: str = "cuda",
    ):
        super().__init__(model, tokenizer, config, device=device)
        self.beta = float(self.config.get("beta", 0.5))
        self.gamma = float(self.config.get("gamma", 0.5))
        self.retain_weight = float(self.config.get("retain_weight", 1.0))
        self.length_normalize = bool(self.config.get("length_normalize", True))
        self.refusal_candidates = self.config.get("refusals", DEFAULT_REFUSALS)
        self.retain_refusal_weight = float(self.config.get("retain_refusal_weight", 0.0))
        if not math.isfinite(self.retain_refusal_weight) or self.retain_refusal_weight < 0:
            raise ValueError('retain_refusal_weight must be finite and nonnegative.')

    def _refusal_batch(self, questions):
        if not questions or not self.refusal_candidates:
            raise ValueError('Refusal training requires questions and refusal candidates.')
        rows = [{'question': q, 'answer': self.refusal_candidates[i % len(self.refusal_candidates)]}
                for i, q in enumerate(questions)]
        dataset = TOFUDataset(rows, self.tokenizer)
        return TOFUDataCollator(self.tokenizer)([dataset[i] for i in range(len(dataset))])

    def _compute_seq_log_prob(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """Computes per-example log probability on label tokens."""
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        mask = (shift_labels != -100).float()

        log_probs = F.log_softmax(shift_logits, dim=-1)
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
        """
        Executes preference optimization between refusal (winner) and forget target (loser).
        If refusal batch tensors are not provided in forget_batch, standard refusal loss is applied.
        """
        f_ids = forget_batch["input_ids"].to(self.device)
        f_mask = forget_batch["attention_mask"].to(self.device)
        f_labels = forget_batch["labels"].to(self.device)

        # 1. Compute log prob of dispreferred forget answers
        log_pi_forget = self._compute_seq_log_prob(f_ids, f_mask, f_labels)

        if "refusal_input_ids" not in forget_batch:
            batch = self._refusal_batch(forget_batch.get('questions'))
            forget_batch = dict(forget_batch, refusal_input_ids=batch["input_ids"],
                                refusal_attention_mask=batch["attention_mask"], refusal_labels=batch["labels"])

        # 2. Compute log prob of preferred refusal answers if present, else penalize forget
        if "refusal_input_ids" in forget_batch:
            r_ids = forget_batch["refusal_input_ids"].to(self.device)
            r_mask = forget_batch["refusal_attention_mask"].to(self.device)
            r_labels = forget_batch["refusal_labels"].to(self.device)
            log_pi_refusal = self._compute_seq_log_prob(r_ids, r_mask, r_labels)

            # Preference margin loss
            diff = self.beta * (log_pi_refusal - log_pi_forget) - self.gamma
            pref_loss = -F.logsigmoid(diff).mean()
        else:
            # Fallback when refusal tensors are not pre-tokenized: directly minimize forget prob
            pref_loss = -F.logsigmoid(-self.beta * log_pi_forget).mean()

        # Release forget graphs before retain forwards to fit the laptop GPU.
        (pref_loss / self.grad_accum_steps).backward()
        total_loss_val = float(pref_loss.detach().item())
        del log_pi_forget, log_pi_refusal, diff, pref_loss

        # 3. Retain Cross Entropy Regularization
        retain_loss_val = 0.0
        retain_pref_val = 0.0
        if retain_batch is not None and (self.retain_weight > 0.0 or self.retain_refusal_weight > 0.0):
            r_batch_ids = retain_batch["input_ids"].to(self.device)
            r_batch_mask = retain_batch["attention_mask"].to(self.device)
            r_batch_labels = retain_batch["labels"].to(self.device)

            retain_outputs = self.model(
                input_ids=r_batch_ids,
                attention_mask=r_batch_mask,
                labels=r_batch_labels,
            )
            retain_loss = retain_outputs.loss
            retain_loss_val = float(retain_loss.detach().item())
            retain_objective = self.retain_weight * retain_loss
            if self.retain_refusal_weight > 0:
                # Prefer the real answer over the same refusals on unrelated data.
                # CE alone can preserve average likelihood while refusal generalizes.
                logits = retain_outputs.logits[:, :-1]
                labels = r_batch_labels[:, 1:]
                mask = labels != -100
                gold_lp = F.log_softmax(logits, dim=-1).gather(
                    -1, labels.masked_fill(~mask, 0).unsqueeze(-1)).squeeze(-1)
                gold_lp = (gold_lp * mask).sum(-1)
                if self.length_normalize:
                    gold_lp = gold_lp / mask.sum(-1).clamp(min=1)
                negative = self._refusal_batch(retain_batch.get('questions'))
                refusal_lp = self._compute_seq_log_prob(negative['input_ids'].to(self.device),
                    negative['attention_mask'].to(self.device), negative['labels'].to(self.device))
                retain_pref = -F.logsigmoid(self.beta * (gold_lp - refusal_lp) - self.gamma).mean()
                retain_pref_val = float(retain_pref.detach().item())
                retain_objective = retain_objective + self.retain_refusal_weight * retain_pref
            (retain_objective / self.grad_accum_steps).backward()
            total_loss_val += float(retain_objective.detach().item())

        return {
            "loss": total_loss_val,
            "pref_loss": total_loss_val - self.retain_weight * retain_loss_val - self.retain_refusal_weight * retain_pref_val,
            "retain_loss": retain_loss_val,
            "retain_pref_loss": retain_pref_val,
        }
