"""CPU snapshots of trainable weights, with a shared original-model utility baseline."""

import torch
import math
from src.methods.base import TrainingStopped


class RetainGuard:
    def __init__(self, model, evaluator, backtrack=False):
        self.model = model
        self.evaluator = evaluator
        self.original = self.snapshot()
        self.safe = self.original
        self.rolled_back = False
        self.rejected_drop = None
        self.rejected_individual_drop = None
        self.backtrack = backtrack
        self.backtrack_fraction = None
        self.checks = 0

    def snapshot(self):
        return {name: p.detach().cpu().clone() for name, p in self.model.named_parameters()
                if p.requires_grad}

    def restore(self, original=False):
        state = self.original if original else self.safe
        with torch.no_grad():
            for name, p in self.model.named_parameters():
                if name in state:
                    p.copy_(state[name].to(p.device))
        self.rolled_back = True

    def __call__(self):
        was_training = self.model.training
        try:
            current = self.evaluator.measure_retain(self.model)
            drop = self.evaluator.initial_retain_lp - current
            individual_drop = self._individual_drop()
            self.checks += 1
            if not self._safe(drop, individual_drop):
                self.rejected_drop = drop
                self.rejected_individual_drop = individual_drop
                if self.backtrack and math.isfinite(drop):
                    rejected = self.snapshot()
                    # Search only the last update interval. Every interpolated
                    # checkpoint must pass the unchanged original utility limit.
                    for fraction in (0.5, 0.25, 0.125):
                        with torch.no_grad():
                            for name, p in self.model.named_parameters():
                                if name in self.safe:
                                    p.copy_(torch.lerp(self.safe[name], rejected[name], fraction).to(p.device))
                        candidate_drop = self.evaluator.initial_retain_lp - self.evaluator.measure_retain(self.model)
                        self.checks += 1
                        if self._safe(candidate_drop, self._individual_drop()):
                            self.safe = self.snapshot()
                            self.backtrack_fraction = fraction
                            break
                self.restore()
                raise TrainingStopped('RETAIN_UTILITY_RISK_ROLLED_BACK')
            self.safe = self.snapshot()
        finally:
            self.model.train(was_training)

    def _individual_drop(self):
        original = getattr(self.evaluator, 'initial_retain_log_probs', None)
        current = getattr(self.evaluator, 'last_retain_log_probs', None)
        if original is None or current is None:
            return 0.0
        if len(original) != len(current) or not all(math.isfinite(x) for x in current):
            return float('inf')
        return max((max(0., before-after) for before, after in zip(original, current)), default=0.)

    def _safe(self, drop, individual_drop):
        limit = getattr(self.evaluator.request, 'retain_per_example_max_drop', None)
        return (math.isfinite(drop) and drop <= self.evaluator.request.retain_max_drop
                and math.isfinite(individual_drop) and (limit is None or individual_drop <= limit))
