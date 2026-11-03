"""Explicit method routing and truthful shared training budgets; no GPU required."""
from types import SimpleNamespace

import pytest
import torch

from src.live_requests import METHODS, normalize_launch, validate_options
from src.atu.v3.analyzer import RequestAnalyzer
from src.atu.v3.budget_engine import BudgetEngine
from src.atu.v3.types import UnlearningRequest, StrategyPlan, VerificationMetrics, VerificationVerdict
from src.methods.base import TrainingStopped


CATALOG = {'authors': [{'id': 'author', 'name': 'Alice',
                       'qa': [{'question': 'Secret?', 'answer': 'SECRET'}]}]}


def request(**kwargs):
    options = dict(forget_data=CATALOG['authors'][0]['qa'], max_time_sec=60,
                   max_trials=3, max_epochs_per_trial=1)
    options.update(kwargs)
    return UnlearningRequest(**options)


def insufficient():
    return VerificationMetrics(-1., 2., 0., 1., 0., 0., True, 1., 0., 1.,
        VerificationVerdict.INSUFFICIENT_FORGETTING, True, .2, {})


@pytest.mark.parametrize('method', METHODS)
def test_launch_normalization_preserves_valid_requested_method(method):
    payload = normalize_launch({'author_id': 'author', 'method': method}, CATALOG)
    assert payload['method'] == method


def test_method_defaults_to_auto_and_bad_or_v2_overrides_fail_early():
    assert normalize_launch({'author_id': 'author'}, CATALOG)['method'] == 'auto'
    for method in ('unsupported', None, ['rmu']):
        with pytest.raises(ValueError, match='method'):
            normalize_launch({'author_id': 'author', 'method': method}, CATALOG)
        with pytest.raises(ValueError, match='method'):
            request(method=method)
    with pytest.raises(ValueError, match='V3'):
        validate_options(engine_version='v2', method='rmu')
    assert validate_options(engine_version='v2')['method'] == 'auto'


@pytest.mark.parametrize('method', METHODS[1:])
def test_explicit_method_bypasses_fast_priority_and_short_budget_routing(method):
    from src.atu.v3.types import UnlearningPriority
    plan = RequestAnalyzer.analyze(request(method=method, priority=UnlearningPriority.FAST, max_time_sec=30))
    assert plan.recommended_method == method and plan.fallback_sequence == []
    assert 'Explicit method' in plan.rationale


class Clock:
    def __init__(self): self.value = 0.
    def monotonic(self): return self.value
    def advance(self, seconds): self.value += seconds


class Model(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.zeros(2))


class Evaluator:
    def __init__(self, req, clock):
        self.request = req
        self.clock = clock
        self.initial_retain_lp = None
    def establish_baseline(self, model):
        self.clock.advance(500)
        self.initial_retain_lp = 0.
    def measure_retain(self, model): return 0.
    def evaluate(self, model):
        self.clock.advance(1000)
        return insufficient()


def fake_engine(monkeypatch, tmp_path, req):
    import src.atu.v3.budget_engine as module
    clock = Clock()
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=clock.monotonic))
    def load(*args, **kwargs):
        clock.advance(400)
        return Model()
    monkeypatch.setattr(module, 'load_peft_target_model', load)
    monkeypatch.setattr(module, 'save_checkpoint', lambda *args, **kwargs: None)
    engine = BudgetEngine('dummy', 'original', None, req, str(tmp_path), 'cpu')
    engine.evaluator = Evaluator(req, clock)
    return engine, clock


def test_shared_budget_excludes_preparation_and_final_evaluation_without_extensions(monkeypatch, tmp_path):
    engine, clock = fake_engine(monkeypatch, tmp_path, request())
    allocations, methods, events = [], [], []
    engine.progress_callback = events.append
    def execute(method, model, config, *loaders):
        methods.append(method)
        assert '_deadline' not in config
        clock.advance(200)  # Method-specific references/controller preparation.
        config['_activate_training_budget'](config)
        allocation = config['_deadline']-clock.monotonic()
        allocations.append(allocation)
        with torch.no_grad(): model.weight.add_(1.)
        config['_on_optimizer_step']()
        clock.advance(allocation)
        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'auto', ['rmu', 'ga']), [], [])
    assert methods == ['atu_npo', 'rmu', 'ga']
    assert allocations == [20., 20., 20.]
    assert trials[-1].metrics.details['total_training_budget_used_seconds'] == 60.
    assert all(t.metrics.details['method_preparation_seconds'] == 200 for t in trials)
    assert all(t.metrics.details['optimizer_steps'] == 1 for t in trials)
    assert all(t.metrics.details['kept_checkpoint_changed'] for t in trials)
    assert all(t.metrics.details['update_diagnostic'] == 'UPDATED_WEIGHTS_KEPT' for t in trials)
    assert {e['phase'] for e in events} == {'preparing', 'training', 'optimizer_step', 'evaluating', 'trial_finished'}


def test_quick_step_budget_does_not_force_a_360_second_time_minimum(monkeypatch, tmp_path):
    engine, clock = fake_engine(monkeypatch, tmp_path, request(max_trials=1, max_total_steps=8))
    allocations = []
    def execute(method, model, config, *loaders):
        config['_activate_training_budget'](config)
        allocations.append(config['_deadline']-clock.monotonic())
        clock.advance(60)
        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'quick'), [], [])
    assert allocations == [60.]
    assert trials[0].metrics.details['training_budget_used_seconds'] == 60.
    assert trials[0].metrics.details['update_diagnostic'] == 'NO_OPTIMIZER_UPDATES'
    assert trials[0].metrics.details['kept_checkpoint_changed'] is False


def test_exhausted_shared_budget_never_creates_an_extra_fallback_allowance(monkeypatch, tmp_path):
    engine, clock = fake_engine(monkeypatch, tmp_path, request())
    def execute(method, model, config, *loaders):
        config['_activate_training_budget'](config)
        # An indivisible operation can finish after a cooperative deadline.
        clock.advance(61)
        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'auto', ['rmu', 'ga']), [], [])
    assert len(trials) == 1
    assert trials[0].metrics.details['total_training_budget_used_seconds'] == 61.


def test_explicit_method_executes_once_without_replacement(monkeypatch, tmp_path):
    req = request(method='ga')
    engine, clock = fake_engine(monkeypatch, tmp_path, req)
    methods = []
    def execute(method, model, config, *loaders):
        methods.append(method)
        config['_activate_training_budget'](config)
        assert config['_deadline']-clock.monotonic() == 60
        clock.advance(1)
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('ga', {'epochs': 1}, 'explicit', ['rmu']), [], [])
    assert methods == ['ga'] and len(trials) == 1
    with pytest.raises(ValueError, match='explicitly requested'):
        engine.run_budget_loop(StrategyPlan('rmu', {'epochs': 1}, 'wrong'), [], [])


def test_npo_references_and_controller_prepare_before_training_activation(monkeypatch, tmp_path):
    import src.atu.v3.budget_engine as module
    events = []
    class Trainer:
        def __init__(self, **kwargs): self.config = kwargs['config']
        def set_reference_cache(self, cache): events.append('reference')
        def prepare_training(self, *args): events.append('controller_preparation')
        def fit_adaptive(self, *args, **kwargs): events.append('fit')
    monkeypatch.setattr(module, 'ATUNPOTrainer', Trainer)
    monkeypatch.setattr(module, 'ATUController', lambda **kwargs: SimpleNamespace(decision_trace=[]))
    monkeypatch.setattr(module, 'compute_sequence_log_prob', lambda *args, **kwargs: {'avg_log_prob': -1.})
    engine = BudgetEngine('dummy', 'original', None, request(), str(tmp_path), 'cpu')
    engine._execute_method('atu_npo', Model(), {'epochs': 1,
        '_activate_training_budget': lambda config: events.append('activate')}, [], [])
    assert events == ['reference', 'controller_preparation', 'activate', 'fit']


def test_rmu_retain_reference_is_prepared_once_before_training_activation(monkeypatch, tmp_path):
    import src.atu.v3.budget_engine as module
    events = []
    class Trainer:
        def __init__(self, model, tokenizer, config, device): self.config = config
        def cache_reference(self, loader): events.append('reference')
        def prepare_training(self, *args): events.append('prepare')
        def fit(self, *args):
            assert self.config['preserve_reference'] is False
            events.append('fit')
    monkeypatch.setattr(module, 'RMUTrainer', Trainer)
    engine = BudgetEngine('dummy', 'original', None, request(), str(tmp_path), 'cpu')
    engine._execute_method('rmu', Model(), {'preserve_reference': True,
        '_activate_training_budget': lambda config: events.append('activate')}, [], [])
    assert events == ['reference', 'prepare', 'activate', 'fit']


def test_kept_weight_diagnostics_distinguish_updates_from_rollback():
    model = Model()
    original = {'weight': model.weight.detach().clone()}
    assert BudgetEngine._kept_parameter_delta(model, original)['kept_checkpoint_changed'] is False
    with torch.no_grad(): model.weight[0] = .5
    details = BudgetEngine._kept_parameter_delta(model, original)
    assert details['changed_trainable_tensors'] == 1 and details['changed_parameter_values'] == 1
    assert details['max_abs_parameter_delta'] == .5 and details['l2_parameter_delta'] == .5
    with torch.no_grad(): model.weight.copy_(original['weight'])
    assert BudgetEngine._kept_parameter_delta(model, original)['kept_checkpoint_changed'] is False
