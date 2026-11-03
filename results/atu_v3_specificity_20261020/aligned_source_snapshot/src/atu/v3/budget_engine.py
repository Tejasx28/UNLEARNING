"""
Budget Engine for ATU v3.
Coordinates multi-trial execution within a fixed time and trial budget,
preserves every attempt checkpoint on disk, and adapts settings or switches methods
when results are insufficient.
"""

import os
import copy
import time
import logging
from typing import Dict, List, Any, Optional
import torch
from transformers import PreTrainedTokenizer, PreTrainedModel

from src.models import (
    load_peft_target_model,
    save_checkpoint,
)
from src.data import create_dataloader, TOFUDataset
from src.atu.controller import ATUController
from src.atu.trainer import ATUNPOTrainer
from src.methods.task_vector import TaskVectorTrainer
from src.methods.dpo_refusal import DPORefusalTrainer
from src.methods.rmu import RMUTrainer
from src.methods.graddiff import GradDiffTrainer
from src.methods.ga import GradientAscentTrainer
from src.atu.v3.types import (
    UnlearningRequest,
    StrategyPlan,
    TrialAttempt,
    VerificationVerdict,
)
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.safety import RetainGuard
from src.atu.v3.policy import method_config
from src.methods.base import TrainingStopped
from src.metrics import compute_sequence_log_prob
from src.data import format_qa_prompt
import random
import gc
import numpy as np
from dataclasses import replace

logger = logging.getLogger(__name__)


class BudgetEngine:
    """
    Manages multi-attempt execution, hyperparameter/method adaptation,
    and checkpoint preservation within fixed budgets.
    """

    def __init__(
        self,
        base_model_name: str,
        target_adapter_path: str,
        tokenizer: PreTrainedTokenizer,
        request: UnlearningRequest,
        output_checkpoint_root: str = "checkpoints/atu_v3",
        device: str = "cuda",
    ):
        self.base_model_name = base_model_name
        self.target_adapter_path = target_adapter_path
        self.tokenizer = tokenizer
        self.request = request
        self.output_checkpoint_root = output_checkpoint_root
        self.device = device if torch.cuda.is_available() else "cpu"
        self.evaluator = TrialEvaluator(tokenizer=tokenizer, request=request, device=self.device)

    def run_budget_loop(
        self,
        initial_plan: StrategyPlan,
        forget_loader: Any,
        retain_loader: Optional[Any] = None,
    ) -> List[TrialAttempt]:
        """
        Executes unlearning trials within budget, adapting parameters upon failure.
        """
        trials = []
        started = time.monotonic()
        deadline = started + self.request.max_time_sec
        self.deadline = deadline
        current_method = initial_plan.recommended_method
        current_config = copy.deepcopy(initial_plan.initial_config)
        fallback_queue = list(initial_plan.fallback_sequence)
        notes = initial_plan.rationale
        total_steps = 0
        for trial_idx in range(1, self.request.max_trials + 1):
            if (time.monotonic() >= deadline or (self.request.max_total_steps is not None
                                                and total_steps >= self.request.max_total_steps)):
                break
            trial_start = time.monotonic()
            random.seed(self.request.seed)
            np.random.seed(self.request.seed)
            torch.manual_seed(self.request.seed)
            model = load_peft_target_model(
                self.base_model_name, self.target_adapter_path, is_trainable=True,
                dtype=torch.bfloat16 if self.device.startswith('cuda') else torch.float32,
                device_map={"": self.device},
            )
            config = None
            guard = None
            try:
                if self.evaluator.initial_retain_lp is None:
                    self.evaluator.establish_baseline(model)
                guard = RetainGuard(model, self.evaluator, backtrack=True)
                current_config['epochs'] = min(int(current_config.get('epochs', 3)),
                                               self.request.max_epochs_per_trial)
                current_config['retain_weight'] = max(float(current_config.get('retain_weight', 1.0)),
                                                    self.request.retain_weight)
                config = copy.deepcopy(current_config)
                execution = {"optimizer_steps": 0}
                def count_step():
                    execution["optimizer_steps"] += 1
                step_limit = self.request.max_steps_per_trial
                if self.request.max_total_steps is not None:
                    remaining = self.request.max_total_steps - total_steps
                    step_limit = remaining if step_limit is None else min(step_limit, remaining)
                config.update(_deadline=deadline, _safety_guard=guard,
                              _guard_every_steps=self.request.guard_every_steps,
                              _max_steps=step_limit,
                              _on_optimizer_step=count_step, _trace_sink=execution)
                status = 'COMPLETED'
                execution_started = time.monotonic()
                try:
                    if time.monotonic() >= deadline:
                        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')
                    training = self._execute_method(current_method, model, config, forget_loader, retain_loader)
                    if isinstance(training, dict):
                        execution['training'] = training
                    guard()
                except TrainingStopped as exc:
                    status = 'STOPPED: ' + str(exc)
                    guard.restore()
                except Exception as exc:
                    logger.exception('Trial execution failed')
                    status = 'FAILED: ' + str(exc)
                    guard.restore(original=True)
                execution["method_execution_seconds"] = round(time.monotonic() - execution_started, 3)
                total_steps += execution['optimizer_steps']
                metrics = self.evaluator.evaluate(model)
                rejected = metrics
                if guard.rejected_drop is not None:
                    rejected = replace(metrics, verdict=VerificationVerdict.RETAIN_DEGRADED,
                                       is_safe=False, retain_preserved=False,
                                       retain_log_prob_drop=guard.rejected_drop)
                    metrics.details['rejected_utility_check'] = {
                        'retain_log_prob_drop': guard.rejected_drop,
                        'limit': self.request.retain_max_drop,
                        'max_individual_retain_drop': guard.rejected_individual_drop,
                        'individual_limit': self.request.retain_per_example_max_drop,
                        'measurement_scope': 'utility check before rollback; forgetting measured on restored weights'}
                if not metrics.is_safe:
                    rejected = metrics
                    guard.restore(original=True)
                    metrics = self.evaluator.evaluate(model)
                    metrics.details['rejected_metrics'] = rejected.to_dict()
                    status = 'ROLLED_BACK: unsafe trial'
                metrics.details['rolled_back'] = guard.rolled_back
                metrics.details['utility_checks'] = guard.checks
                metrics.details['backtrack_fraction'] = guard.backtrack_fraction
                metrics.details['total_optimizer_steps_so_far'] = total_steps
                metrics.details.update(execution)
                trial_dir = os.path.join(self.output_checkpoint_root, f'trial_{trial_idx}')
                save_checkpoint(model, self.tokenizer, trial_dir, metadata={
                    'trial_index': trial_idx, 'method': current_method,
                    'config': current_config, 'status': status, 'adaptation': notes,
                    'metrics': metrics.to_dict(), 'seed': self.request.seed,
                })
                trials.append(TrialAttempt(
                    trial_index=trial_idx, method=current_method,
                    config=copy.deepcopy(current_config), checkpoint_dir=trial_dir,
                    metrics=metrics, duration_seconds=round(time.monotonic()-trial_start, 2),
                    status=status, adaptation_applied=notes))
            finally:
                # The callback owns a guard, which owns the model. Drop it before
                # loading the next model so two full targets do not coexist on GPU.
                if config is not None:
                    config.pop('_safety_guard', None)
                model = None
                guard = None
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            if metrics.verdict == VerificationVerdict.CONVERGED_SAFE and not status.startswith('FAILED'):
                break
            current_method, current_config, notes = self._adapt_strategy(
                rejected, current_method, current_config, fallback_queue)
        return trials

    def _execute_method(
        self,
        method: str,
        model: PreTrainedModel,
        config: Dict[str, Any],
        forget_loader: Any,
        retain_loader: Optional[Any],
    ):
        """Dispatches trial execution to the corresponding trainer."""
        if method == "task_vector":
            trainer = TaskVectorTrainer(model, self.tokenizer, config, device=self.device)
            mode = config.get("mode", "adapter_dampen")
            if mode == "adapter_dampen":
                return trainer.apply_adapter_subtraction(config.get("scaling_factor", 0.5))
            else:
                return trainer.fit(forget_loader, retain_loader)

        elif method == "atu_npo":
            config = dict(config, dev_probes=self.request.dev_probes or [],
                          base_floor_mean=self.request.base_floor_mean,
                          base_floor_std=self.request.base_floor_std,
                          floor_buffer=self.request.floor_buffer,
                          retain_max_drop=self.request.retain_max_drop)
            if self.request.forget_reference_log_probs is not None:
                config['target_floors'] = {row['question']: base + self.request.forget_reference_tolerance
                    for row, base in zip(self.request.forget_data, self.request.forget_reference_log_probs)}
            controller = ATUController(
                forget_data=self.request.forget_data,
                tokenizer=self.tokenizer,
                config=config,
            )
            trainer = ATUNPOTrainer(
                model=model,
                tokenizer=self.tokenizer,
                config=config,
                controller=controller,
                retain_val_data=self.request.retain_validation_data,
                device=self.device,
            )
            trainer.set_reference_cache({x['question']: compute_sequence_log_prob(
                model, self.tokenizer, format_qa_prompt(x['question']), x['answer'],
                device=self.device)['avg_log_prob'] for x in self.request.forget_data})
            try:
                return trainer.fit_adaptive(forget_loader, retain_loader, max_rounds=config.get("epochs", 4))
            finally:
                sink = config.get('_trace_sink')
                if sink is not None:
                    sink['controller_decisions'] = controller.decision_trace

        elif method == "rmu":
            trainer = RMUTrainer(model, self.tokenizer, config, device=self.device)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "dpo_refusal":
            trainer = DPORefusalTrainer(model, self.tokenizer, config, device=self.device)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "graddiff":
            trainer = GradDiffTrainer(model, self.tokenizer, config, device=self.device)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "ga":
            trainer = GradientAscentTrainer(model, self.tokenizer, config, device=self.device)
            return trainer.fit(forget_loader, retain_loader)
        else:
            raise ValueError(f"Unsupported unlearning method: {method}")

    def _adapt_strategy(
        self, failed_metrics: Any, current_method: str,
        current_config: Dict[str, Any], fallback_queue: List[str],
    ) -> tuple[str, Dict[str, Any], str]:
        """Try a distinct calibrated method before repeating a failed strategy."""
        verdict = failed_metrics.verdict
        damaged = verdict in (VerificationVerdict.RETAIN_DEGRADED, VerificationVerdict.MODEL_COLLAPSED)
        while fallback_queue:
            next_method = fallback_queue.pop(0)
            if next_method == current_method:
                continue
            config = method_config(next_method, self.request)
            if damaged and current_method in ('ga', 'graddiff') and next_method == 'atu_npo':
                config['retain_weight'] = max(config['retain_weight'], 2.)
            reason = 'Retain degradation or answer collapse' if damaged else 'Insufficient forgetting'
            return next_method, config, (
                f'{reason} on {current_method}. Escalated to a fresh {next_method} attempt '
                'with its method-specific calibration; all previous safe checkpoints remain eligible.')

        config = copy.deepcopy(current_config)
        if damaged:
            config['lr'] = float(config.get('lr', 1e-5)) * .5
            config['retain_weight'] = float(config.get('retain_weight', 1.)) * 1.8
            if current_method in ('graddiff', 'rmu'):
                config['alpha'] = max(float(config.get('alpha', 1.)) * 1.8, config['retain_weight'])
            notes = 'Retain degradation: no alternative remains; lower LR and increase retain protection.'
        else:
            config['lr'] = min(5e-4, float(config.get('lr', 1e-5)) * 1.25)
            notes = 'No distinct alternative remains; retry with modestly increased forgetting pressure.'
        return current_method, config, notes
