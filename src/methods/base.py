"""
Base unlearning trainer class.
Provides common training loop, device handling, optimizer configuration,
and metrics/provenance tracking across all unlearning algorithms.
"""

import time
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import PreTrainedTokenizer
from peft import PeftModel

from src.models import save_checkpoint

logger = logging.getLogger(__name__)


class TrainingStopped(RuntimeError):
    """A training boundary reached its deadline, step budget, or safety limit."""


class BaseUnlearningTrainer(ABC):
    """
    Abstract base trainer for unlearning algorithms.
    """

    def __init__(
        self,
        model: PeftModel,
        tokenizer: PreTrainedTokenizer,
        config: Dict[str, Any],
        device: str = "cuda",
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.device = device

        self.lr = float(config.get("lr", 1e-4))
        self.weight_decay = float(config.get("weight_decay", 0.01))
        self.max_grad_norm = float(config.get("max_grad_norm", 1.0))
        self.epochs = int(config.get("epochs", 5))
        self.grad_accum_steps = int(config.get("grad_accum_steps", 1))
        if self.grad_accum_steps < 1:
            raise ValueError('grad_accum_steps must be at least one.')

        self.optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.model.parameters()),
            lr=self.lr,
            weight_decay=self.weight_decay,
        )
        self.optimizer_steps = 0
        self.optimizer.register_step_post_hook(self._after_optimizer_step)

        self.step_history: List[Dict[str, float]] = []
        self.train_time_sec: float = 0.0
        self.peak_vram_gb: float = 0.0

    @abstractmethod
    def train_step(self, forget_batch: Dict[str, Any], retain_batch: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Execute a single forward-backward optimization step. Must be implemented by subclasses."""
        pass

    def prepare_training(self, forget_loader=None, retain_loader=None):
        """Prepare method state before an optional training-only deadline starts."""

    def _apply_optimizer_step(self, accumulated_batches: int):
        """Apply a complete or final partial gradient-accumulation group.

        Each train_step divides its loss by grad_accum_steps. A shorter final
        group must be rescaled so its gradients represent its own mean, rather
        than silently disappearing or receiving an artificially smaller update.
        """
        if accumulated_batches <= 0:
            return
        if accumulated_batches != self.grad_accum_steps:
            scale = self.grad_accum_steps / accumulated_batches
            for parameter in self.model.parameters():
                if parameter.grad is not None:
                    parameter.grad.mul_(scale)
        if self.max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(
                filter(lambda p: p.requires_grad, self.model.parameters()),
                self.max_grad_norm,
            )
        try:
            self.optimizer.step()
        finally:
            # A safety post-hook can raise after the actual update and rollback.
            self.optimizer.zero_grad()

    def fit(
        self,
        forget_loader: DataLoader,
        retain_loader: Optional[DataLoader] = None,
    ) -> Dict[str, Any]:
        """
        Main unlearning optimization loop.
        """
        self.model.train()
        self.prepare_training(forget_loader, retain_loader)
        self.model.train()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        start_time = time.time()
        global_step = 0
        self.optimizer.zero_grad()

        retain_iter = iter(retain_loader) if retain_loader is not None else None

        for epoch in range(self.epochs):
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
                step_metrics["epoch"] = epoch + 1
                self.step_history.append(step_metrics)
                if accumulated_batches == self.grad_accum_steps:
                    self._apply_optimizer_step(accumulated_batches)
                    accumulated_batches = 0

            if accumulated_batches:
                self._apply_optimizer_step(accumulated_batches)

            guard = self.config.get("_safety_guard")
            if guard is not None:
                guard()
                self.model.train()

        self.train_time_sec = round(time.time() - start_time, 2)
        if torch.cuda.is_available():
            self.peak_vram_gb = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 3)

        return {
            "train_time_sec": self.train_time_sec,
            "peak_vram_gb": self.peak_vram_gb,
            "total_steps": global_step,
            "optimizer_steps": self.optimizer_steps,
            "final_step_metrics": self.step_history[-1] if self.step_history else {},
        }

    def _after_optimizer_step(self, *args):
        self.optimizer_steps += 1
        self.config['_optimizer_revision'] = self.optimizer_steps
        guard = self.config.get("_safety_guard")
        if guard is not None and hasattr(guard, 'notify_optimizer_step'):
            guard.notify_optimizer_step()
        observer = self.config.get("_on_optimizer_step")
        if observer is not None:
            observer()
        # V3 can check between optimizer updates instead of losing an entire
        # epoch when the next round crosses the utility boundary. Legacy v2
        # leaves this unset and keeps its original control schedule.
        interval = self.config.get("_guard_every_steps")
        if interval and guard is not None and self.optimizer_steps % interval == 0:
            guard()

    def check_limits(self, global_step=0):
        deadline = self.config.get("_deadline")
        if deadline is not None and time.monotonic() >= deadline:
            raise TrainingStopped("TIME_BUDGET_EXHAUSTED")
        max_steps = self.config.get("_max_steps")
        if max_steps is not None and global_step >= max_steps:
            raise TrainingStopped("STEP_BUDGET_EXHAUSTED")

    def save(self, output_dir: str, additional_metadata: Optional[Dict[str, Any]] = None):
        """Save model checkpoint with unlearning configuration and run statistics."""
        metadata = {
            "method": self.__class__.__name__,
            "config": self.config,
            "train_time_sec": self.train_time_sec,
            "peak_vram_gb": self.peak_vram_gb,
            "history": self.step_history[-10:] if len(self.step_history) > 10 else self.step_history,
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        save_checkpoint(self.model, self.tokenizer, output_dir, metadata=metadata)
