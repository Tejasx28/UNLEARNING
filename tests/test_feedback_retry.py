"""Generation-driven settings retries retain method diversity and shared limits."""
import copy

import pytest
import torch

from src.atu.v3.budget_engine import BudgetEngine
from src.atu.v3.types import StrategyPlan, VerificationVerdict
from test_routing_budget_regressions import fake_engine, request
from test_v3_integration import metric


def partial(**kwargs):
    values = dict(forget_suppressed_ratio=1., probe_leak_rate=.2,
                  details={'probe_measure': 'generated_response_recovery',
                           'development_probes_tested': 5,
                           'probe_results': [{'id': 'development-1', 'verdict': 'PARTIAL_RECOVERY',
                                              'degenerate': False}]})
    values.update(kwargs)
    return metric(VerificationVerdict.INSUFFICIENT_FORGETTING, **values)


def engine():
    result = BudgetEngine.__new__(BudgetEngine)
    result.request = request(max_probe_leak_rate=0., max_epochs_per_trial=8)
    return result


def config():
    return {'lr': 1e-4, 'beta': .5, 'retain_weight': 1.5, 'leak_boost': 1.8, 'epochs': 8}


def test_recoverable_fragment_below_likelihood_floor_gets_one_measured_settings_retry():
    current, queue, tried = config(), ['graddiff', 'rmu'], set()
    before = copy.deepcopy(current)
    method, tuned, notes, decision = engine()._plan_next_attempt(
        partial(), 'atu_npo', current, queue, 2, tried, 8, 'COMPLETED')
    assert method == 'atu_npo' and queue == ['graddiff', 'rmu']
    assert tried == {'atu_npo'} and current == before
    assert tuned['beta'] < current['beta'] and tuned['lr'] < current['lr']
    assert tuned['leak_boost'] > current['leak_boost']
    assert tuned['retain_weight'] > current['retain_weight']
    assert tuned['epochs'] <= 8
    assert decision['action'] == 'ADJUST_SETTINGS'
    assert decision['source'] == 'development_only'
    assert decision['leaking_probe_ids'] == ['development-1']
    assert decision['distinct_fallback_reserved']
    assert 'original target' in notes and 'Utility limits are unchanged' in notes


def test_tuned_method_does_not_take_the_reserved_distinct_attempt():
    method, tuned, _, decision = engine()._plan_next_attempt(
        partial(), 'atu_npo', config(), ['graddiff', 'rmu'], 2, {'atu_npo'}, 8, 'COMPLETED')
    assert method == 'graddiff' and 'beta' not in tuned
    assert decision['action'] == 'SWITCH_METHOD'


@pytest.mark.parametrize('remaining, updates, status, measured', [
    (1, 8, 'COMPLETED', True), (2, 0, 'COMPLETED', True),
    (2, 8, 'FAILED: runtime', True), (2, 8, 'COMPLETED', False),
])
def test_missing_progress_or_diversity_switches_without_an_npo_repeat(remaining, updates, status, measured):
    observed = partial()
    if not measured:
        observed.details = {}
    method, _, _, _ = engine()._plan_next_attempt(
        observed, 'atu_npo', config(), ['rmu'], remaining, set(), updates, status)
    assert method == 'rmu'


def test_actual_retain_quality_breach_switches_methods_instead_of_relaxing_the_limit():
    observed = partial(is_safe=False, retain_preserved=False)
    observed.verdict = VerificationVerdict.RETAIN_DEGRADED
    observed.details['retain_quality_check'] = {'enabled': True, 'passed': False,
                                               'relative_drop': .08, 'limit': .02}
    method, _, _, decision = engine()._plan_next_attempt(
        observed, 'atu_npo', config(), ['rmu'], 2, set(), 8, 'ROLLED_BACK: unsafe trial')
    assert method == 'rmu' and decision['action'] == 'SWITCH_METHOD'


def test_rollback_with_promising_kept_recovery_gets_a_more_conservative_retry():
    observed = partial(is_safe=False, retain_preserved=False)
    observed.verdict = VerificationVerdict.RETAIN_DEGRADED
    observed.details['rejected_utility_check'] = {'retain_log_prob_drop': .04, 'limit': .03}
    method, tuned, _, _ = engine()._plan_next_attempt(
        observed, 'atu_npo', config(), ['rmu'], 2, set(), 8, 'STOPPED: RETAIN_UTILITY_RISK_ROLLED_BACK')
    assert method == 'atu_npo'
    assert tuned['lr'] == pytest.approx(5e-5)
    assert tuned['retain_weight'] == pytest.approx(2.25)


def test_generation_feedback_retry_restarts_clean_and_obeys_shared_time_and_step_limits(monkeypatch, tmp_path):
    req = request(max_probe_leak_rate=0., max_total_steps=3)
    current, clock = fake_engine(monkeypatch, tmp_path, req)
    current.evaluator.evaluate = lambda model: copy.deepcopy(partial())
    seen, allocations = [], []

    def train(method, model, cfg, *loaders):
        # Each attempt must reload the original, rather than continue from a
        # partially unlearned checkpoint or inherit another optimizer's state.
        assert model.weight.detach().tolist() == [0., 0.]
        seen.append((method, model, cfg['_max_steps']))
        cfg['_activate_training_budget'](cfg)
        allocations.append(cfg['_deadline'] - clock.monotonic())
        with torch.no_grad():
            model.weight.add_(1.)
        cfg['_on_optimizer_step']()
        clock.advance(4.)

    current._execute_method = train
    trials = current.run_budget_loop(StrategyPlan('atu_npo', config(), 'test', ['graddiff', 'rmu']), [], [])
    assert [row[0] for row in seen] == ['atu_npo', 'atu_npo', 'graddiff']
    assert len({id(row[1]) for row in seen}) == 3
    assert [row[2] for row in seen] == [3, 2, 1]
    assert allocations == [20., 28., 52.]
    assert trials[-1].metrics.details['total_training_budget_used_seconds'] == 12.
    assert sum(trial.metrics.details['optimizer_steps'] for trial in trials) == 3
    assert [trial.metrics.details['feedback_decision']['action'] for trial in trials] == [
        'ADJUST_SETTINGS', 'SWITCH_METHOD', 'STOP_TRIAL_LIMIT']
    assert trials[1].config['beta'] == .25


def test_explicit_method_remains_one_attempt_even_with_recoverable_development_facts(monkeypatch, tmp_path):
    current, clock = fake_engine(monkeypatch, tmp_path, request(method='atu_npo', max_probe_leak_rate=0.))
    current.evaluator.evaluate = lambda model: copy.deepcopy(partial())
    seen = []

    def train(method, model, cfg, *loaders):
        seen.append(method)
        cfg['_activate_training_budget'](cfg)
        cfg['_on_optimizer_step']()
        clock.advance(1.)

    current._execute_method = train
    trials = current.run_budget_loop(StrategyPlan('atu_npo', config(), 'explicit', ['graddiff']), [], [])
    assert seen == ['atu_npo'] and len(trials) == 1
    assert trials[0].metrics.details['feedback_decision']['action'] == 'STOP_TRIAL_LIMIT'
