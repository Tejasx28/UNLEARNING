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
        self.progress_callback = None

    def _progress(self, trial_index, method, optimizer_steps, phase, remaining_training_seconds):
        if self.progress_callback is not None:
            try:
                self.progress_callback({'trial_index': trial_index, 'method': method,
                    'optimizer_steps': optimizer_steps, 'phase': phase,
                    'remaining_training_seconds': round(max(0., remaining_training_seconds), 2)})
            except Exception:
                logger.exception('Progress observer failed; computation continues')

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
        # The user-facing budget covers method execution, including its in-loop
        # safety/control work. Model loading, reference preparation and final
        # evaluation are reported separately and never silently enlarge it.
        training_spent = 0.0
        self.deadline = None
        current_method = initial_plan.recommended_method
        current_config = copy.deepcopy(initial_plan.initial_config)
        fallback_queue = list(initial_plan.fallback_sequence)
        notes = initial_plan.rationale
        if self.request.method != 'auto' and current_method != self.request.method:
            raise ValueError('The strategy plan does not match the explicitly requested method.')
        total_steps = 0
        settings_retries = set()
        trial_limit = self.request.max_trials if self.request.method == 'auto' else 1
        for trial_idx in range(1, trial_limit + 1):
            if (self.request.max_total_steps is not None
                    and total_steps >= self.request.max_total_steps):
                break
            remaining_time = max(0.0, self.request.max_time_sec - training_spent)
            if remaining_time <= 0:
                break
            trial_start = time.monotonic()
            self._progress(trial_idx, current_method, 0, 'preparing', remaining_time)
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
            next_strategy = None
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
                    active = max(0., time.monotonic()-training_started) if training_started is not None else 0.
                    self._progress(trial_idx, current_method, execution['optimizer_steps'], 'optimizer_step',
                                   self.request.max_time_sec-training_spent-active)
                step_limit = self.request.max_steps_per_trial
                if self.request.max_total_steps is not None:
                    remaining = self.request.max_total_steps - total_steps
                    step_limit = remaining if step_limit is None else min(step_limit, remaining)
                remaining_trials = trial_limit - trial_idx + 1
                trial_budget = remaining_time / remaining_trials
                training_started = None
                execution_started = time.monotonic()

                def activate_training_budget(training_config):
                    nonlocal training_started
                    if training_started is None:
                        training_started = time.monotonic()
                        self.deadline = training_started + trial_budget
                        execution['method_preparation_seconds'] = round(training_started-execution_started, 3)
                        execution['preparation_seconds'] = round(training_started-trial_start, 3)
                    training_config['_deadline'] = self.deadline
                    self._progress(trial_idx, current_method, execution['optimizer_steps'], 'training',
                                   self.request.max_time_sec-training_spent)

                config.update(_safety_guard=guard,
                              _guard_every_steps=self.request.guard_every_steps,
                              _max_steps=step_limit,
                              _on_optimizer_step=count_step, _trace_sink=execution,
                              _activate_training_budget=activate_training_budget)
                execution['allocated_training_budget_seconds'] = round(trial_budget, 3)
                status = 'COMPLETED'
                try:
                    try:
                        training = self._execute_method(current_method, model, config, forget_loader, retain_loader)
                        if isinstance(training, dict):
                            execution['training'] = training
                    finally:
                        used = max(0.0, time.monotonic()-training_started) if training_started is not None else 0.0
                        training_spent += used
                        execution['training_budget_used_seconds'] = round(used, 3)
                        execution['optimization_seconds'] = round(used, 3)
                        execution['total_training_budget_used_seconds'] = round(training_spent, 3)
                    guard()
                except TrainingStopped as exc:
                    status = 'STOPPED: ' + str(exc)
                    if str(exc) in ('TIME_BUDGET_EXHAUSTED', 'STEP_BUDGET_EXHAUSTED'):
                        if guard.rejected_drop is not None:
                            guard.restore()
                        else:
                            try:
                                guard()
                            except TrainingStopped:
                                pass
                    else:
                        guard.restore()
                except Exception as exc:
                    logger.exception('Trial execution failed')
                    status = 'FAILED: ' + str(exc)
                    guard.restore(original=True)
                execution["method_execution_seconds"] = round(time.monotonic() - execution_started, 3)
                execution['requested_training_budget_seconds'] = self.request.max_time_sec
                total_steps += execution['optimizer_steps']
                self._progress(trial_idx, current_method, execution['optimizer_steps'], 'evaluating',
                               self.request.max_time_sec-training_spent)
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
                metrics.details['duplicate_utility_checks_skipped'] = getattr(guard, 'duplicate_checks_skipped', 0)
                metrics.details['backtrack_fraction'] = guard.backtrack_fraction
                metrics.details['total_optimizer_steps_so_far'] = total_steps
                execution.update(self._kept_parameter_delta(model, guard.original))
                execution['update_diagnostic'] = (
                    'UPDATED_WEIGHTS_KEPT' if execution['optimizer_steps'] > 0 and execution['kept_checkpoint_changed']
                    else 'NO_OPTIMIZER_UPDATES' if execution['optimizer_steps'] == 0
                    else 'UPDATES_ROLLED_BACK_OR_NO_EFFECT')
                metrics.details.update(execution)
                remaining_slots = trial_limit - trial_idx
                if metrics.verdict == VerificationVerdict.CONVERGED_SAFE and not status.startswith('FAILED'):
                    decision = {'action': 'STOP_CONVERGED', 'reason': 'Development recovery, likelihood and retain checks passed.'}
                elif remaining_slots <= 0:
                    decision = {'action': 'STOP_TRIAL_LIMIT', 'reason': 'The configured attempt limit was reached.'}
                elif training_spent >= self.request.max_time_sec:
                    decision = {'action': 'STOP_TIME_BUDGET', 'reason': 'The shared training allowance was exhausted.'}
                elif self.request.max_total_steps is not None and total_steps >= self.request.max_total_steps:
                    decision = {'action': 'STOP_STEP_BUDGET', 'reason': 'The shared optimizer-update limit was reached.'}
                else:
                    next_method, next_config, next_notes, decision = self._plan_next_attempt(
                        rejected, current_method, current_config, fallback_queue,
                        remaining_slots, settings_retries, execution['optimizer_steps'], status)
                    next_strategy = (next_method, next_config, next_notes)
                metrics.details['feedback_decision'] = decision
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
                self._progress(trial_idx, current_method, execution['optimizer_steps'], 'trial_finished',
                               self.request.max_time_sec-training_spent)
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
            if next_strategy is None:
                break
            current_method, current_config, notes = next_strategy
        return trials

    def _plan_next_attempt(
        self, observed_metrics, current_method, current_config, fallback_queue,
        remaining_slots, settings_retries, optimizer_steps, trial_status,
    ):
        """Tune one promising NPO attempt, while reserving a distinct fallback.

        Only measured development responses drive this decision. Final test
        probes are deliberately absent from this interface. A retry starts from
        the original target, with the same global step/time and utility limits.
        """
        details = observed_metrics.details
        recoveries = [row for row in details.get('probe_results', [])
                      if row.get('verdict') in ('FULL_RECOVERY', 'PARTIAL_RECOVERY')
                      and not row.get('degenerate', False)]
        measured = (details.get('probe_measure') == 'generated_response_recovery'
                    and details.get('development_probes_tested', 0) > 0 and bool(recoveries))
        has_alternative = any(method != current_method for method in fallback_queue)
        promising = (observed_metrics.forget_suppressed_ratio >= .5
                     and self.request.max_probe_leak_rate < observed_metrics.probe_leak_rate <= .5)
        quality = details.get('retain_quality_check') or {}
        quality_passed = not quality.get('enabled') or quality.get('passed') is True
        can_tune = (self.request.method == 'auto' and current_method == 'atu_npo'
                    and current_method not in settings_retries and remaining_slots >= 2
                    and has_alternative and optimizer_steps > 0 and measured and promising
                    and not trial_status.startswith('FAILED')
                    and quality_passed
                    and (observed_metrics.is_safe or bool(details.get('rejected_utility_check')))
                    and observed_metrics.verdict != VerificationVerdict.MODEL_COLLAPSED)
        if can_tune:
            settings_retries.add(current_method)
            config = copy.deepcopy(current_config)
            damaged = observed_metrics.verdict == VerificationVerdict.RETAIN_DEGRADED
            before = {key: config.get(key) for key in ('lr', 'beta', 'retain_weight', 'leak_boost', 'epochs')}
            config['lr'] = float(config.get('lr', 1e-4)) * (.5 if damaged else .75)
            # Lower beta prevents the NPO loss from saturating as quickly when
            # complete-answer likelihood fell but a private fragment is recalled.
            config['beta'] = max(.1, float(config.get('beta', .5)) * .5)
            config['retain_weight'] = max(float(config.get('retain_weight', 1.)), self.request.retain_weight) * (1.5 if damaged else 1.1)
            config['leak_boost'] = min(3., float(config.get('leak_boost', 1.8)) * 1.25)
            config['epochs'] = min(self.request.max_epochs_per_trial, int(config.get('epochs', 1)) + 2)
            changed = {key: {'before': before[key], 'after': config[key]}
                       for key in before if before[key] != config[key]}
            reason = ('The previous update interval hit a utility guard, while the kept checkpoint still made partial forgetting progress.'
                      if damaged else 'Answer likelihood fell, but measured development responses still recovered target information.')
            notes = (f'{reason} Retry ATU-NPO once from the original target with lower LR/beta, '
                     'stronger retain regularization and higher priority for still-leaking probes. '
                     'Utility limits are unchanged; a distinct alternative remains reserved.')
            decision = {'action': 'ADJUST_SETTINGS', 'next_method': current_method,
                        'reason': reason, 'settings_changed': changed,
                        'development_probe_leak_rate': observed_metrics.probe_leak_rate,
                        'leaking_probe_ids': [row.get('id') or row.get('probe_id') for row in recoveries],
                        'source': 'development_only', 'fresh_original_restart': True,
                        'distinct_fallback_reserved': True}
            return current_method, config, notes, decision

        method, config, notes = self._adapt_strategy(observed_metrics, current_method, current_config, fallback_queue)
        action = 'SWITCH_METHOD' if method != current_method else 'ADJUST_SETTINGS'
        return method, config, notes, {'action': action, 'next_method': method,
            'reason': notes, 'source': 'development_only', 'fresh_original_restart': True,
            'development_probe_leak_rate': observed_metrics.probe_leak_rate}

    @staticmethod
    def _kept_parameter_delta(model, original):
        """Measure kept trainable weights after all safety rollback decisions."""
        tensors = changed_tensors = changed_values = 0
        max_delta = squared_norm = 0.0
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name not in original:
                    continue
                tensors += 1
                delta = parameter.detach().cpu().float() - original[name].float()
                changed = int(torch.count_nonzero(delta).item())
                if changed:
                    changed_tensors += 1
                    changed_values += changed
                    max_delta = max(max_delta, float(delta.abs().max().item()))
                    squared_norm += float(delta.square().sum().item())
        return {'trainable_parameter_tensors': tensors,
                'changed_trainable_tensors': changed_tensors,
                'changed_parameter_values': changed_values,
                'max_abs_parameter_delta': max_delta,
                'l2_parameter_delta': squared_norm**.5,
                'kept_checkpoint_changed': changed_values > 0}

    @staticmethod
    def _prepare_trainer(trainer, config, forget_loader, retain_loader):
        """Preparation may probe references; only then start the method timer."""
        trainer.prepare_training(forget_loader, retain_loader)
        activate = config.get('_activate_training_budget')
        if activate is not None:
            activate(trainer.config)

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
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
            mode = config.get("mode", "adapter_dampen")
            if mode == "adapter_dampen":
                return trainer.apply_adapter_subtraction(config.get("scaling_factor", 0.5))
            else:
                return trainer.fit(forget_loader, retain_loader)

        elif method == "atu_npo":
            config = dict(config, dev_probes=self.request.dev_probes or [],
                          dev_max_new_tokens=self.request.eval_max_new_tokens,
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
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
            try:
                return trainer.fit_adaptive(forget_loader, retain_loader, max_rounds=config.get("epochs", 4))
            finally:
                sink = config.get('_trace_sink')
                if sink is not None:
                    sink['controller_decisions'] = controller.decision_trace

        elif method == "rmu":
            trainer = RMUTrainer(model, self.tokenizer, config, device=self.device)
            if config.get('preserve_reference', False) and retain_loader is not None:
                trainer.cache_reference(retain_loader)
                # RMU.fit normally performs this work itself. It has already
                # been done outside the training timer, and its cached vectors
                # continue to drive the unchanged retain objective.
                trainer.config['preserve_reference'] = False
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "dpo_refusal":
            trainer = DPORefusalTrainer(model, self.tokenizer, config, device=self.device)
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "graddiff":
            trainer = GradDiffTrainer(model, self.tokenizer, config, device=self.device)
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
            return trainer.fit(forget_loader, retain_loader)

        elif method == "ga":
            trainer = GradientAscentTrainer(model, self.tokenizer, config, device=self.device)
            self._prepare_trainer(trainer, config, forget_loader, retain_loader)
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
        stubborn = getattr(failed_metrics, 'forget_suppressed_ratio', 1.0) < 0.3
        
        while fallback_queue:
            next_method = fallback_queue.pop(0)
            if next_method == current_method:
                continue
            config = method_config(next_method, self.request)
            if damaged and current_method in ('ga', 'graddiff') and next_method == 'atu_npo':
                config['retain_weight'] = max(config['retain_weight'], 2.)
            reason = 'Retain degradation or answer collapse' if damaged else ('Stubborn representation resistance' if stubborn else 'Insufficient forgetting')
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
            config['lr'] = min(5e-4, float(config.get('lr', 1e-5)) * 1.3)
            notes = 'No distinct alternative remains; retry with modestly increased forgetting pressure.'
        return current_method, config, notes
