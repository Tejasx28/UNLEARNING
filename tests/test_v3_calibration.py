"""Regressions for fine-grained safety, resource accounting and fallback settings."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from src.atu.v3.safety import RetainGuard
from src.atu.v3.policy import method_config
from src.atu.v3.types import UnlearningRequest
from src.methods.base import TrainingStopped
from src.methods.ga import GradientAscentTrainer
from src.methods.graddiff import GradDiffTrainer
from src.methods.rmu import RMUTrainer


class ScalarModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.))


def test_backtrack_uses_original_limit_and_keeps_only_measured_safe_fraction():
    model = ScalarModel()
    evaluator = SimpleNamespace(initial_retain_lp=0., request=SimpleNamespace(retain_max_drop=.03),
                                measure_retain=lambda m: -float(m.weight.detach()))
    guard = RetainGuard(model, evaluator, backtrack=True)
    with torch.no_grad():
        model.weight.fill_(.02)
    guard()
    with torch.no_grad():
        model.weight.fill_(.062)
    with pytest.raises(TrainingStopped):
        guard()
    assert guard.backtrack_fraction == .125
    assert float(model.weight.detach()) == pytest.approx(.02525)
    assert -evaluator.measure_retain(model) <= .03
    assert guard.rejected_drop == pytest.approx(.062)


def test_optimizer_step_guard_counts_completed_update_before_stopping():
    model = ScalarModel()
    trainer = GradientAscentTrainer(model, None, {'lr': .1, '_guard_every_steps': 1,
        '_safety_guard': Mock(side_effect=TrainingStopped('utility')), '_on_optimizer_step': Mock()}, device='cpu')
    model.weight.grad = torch.tensor(1.)
    with pytest.raises(TrainingStopped):
        trainer.optimizer.step()
    assert trainer.optimizer_steps == 1
    trainer.config['_on_optimizer_step'].assert_called_once()
    trainer.config['_safety_guard'].assert_called_once()


def test_method_settings_are_independent_and_retain_weight_reaches_graddiff():
    req = UnlearningRequest(forget_data=[], retain_weight=4., max_epochs_per_trial=2)
    cfg = method_config('rmu', req)
    assert cfg['alpha'] == 4. and cfg['preserve_reference']
    assert cfg['epochs'] == 2
    cfg['lr'] = 123
    assert method_config('rmu', req)['lr'] != 123
    trainer = GradDiffTrainer(ScalarModel(), None, {'alpha': 1., 'retain_weight': 4.}, device='cpu')
    assert trainer.alpha == 4.


def test_rmu_reference_is_original_target_and_does_not_follow_updates():
    class HiddenModel(ScalarModel):
        config = SimpleNamespace(hidden_size=2)

    model = HiddenModel()
    trainer = RMUTrainer(model, None, {'preserve_reference': True}, device='cpu')
    trainer._extract_hidden_state = lambda ids, mask: model.weight.expand(*ids.shape, 2)
    batch = {'input_ids': torch.tensor([[1, 2, 0]]), 'attention_mask': torch.tensor([[1, 1, 0]]),
             'questions': ['retain']}
    with torch.no_grad():
        model.weight.fill_(2.)
    trainer.cache_reference([batch])
    assert model.training
    with torch.no_grad():
        model.weight.fill_(5.)
    assert trainer.reference_hidden['retain'].tolist() == [2., 2.]
    assert trainer._mean_hidden(batch['input_ids'], batch['attention_mask']).tolist() == [[5., 5.]]


def test_step_budget_counts_optimizer_updates_with_gradient_accumulation():
    model = ScalarModel()
    trainer = GradientAscentTrainer(model, None, {'epochs': 5, 'grad_accum_steps': 2,
                                                 '_max_steps': 2}, device='cpu')
    def train(*args):
        model.weight.square().backward()
        return {'loss': 0.}
    trainer.train_step = train
    with pytest.raises(TrainingStopped, match='STEP_BUDGET'):
        trainer.fit([{}, {}, {}, {}, {}, {}])
    assert trainer.optimizer_steps == 2
    assert len(trainer.step_history) == 4


def test_total_budget_includes_rejected_attempts(tmp_path, monkeypatch):
    from src.atu.v3.budget_engine import BudgetEngine
    from src.atu.v3.types import StrategyPlan
    from test_v3_integration import TinyModel, TinyTokenizer, fake_save, metric, request
    from src.atu.v3.types import VerificationVerdict
    from src.atu.v3.data import prepare_request
    req = prepare_request(request(max_trials=3, max_total_steps=3, max_steps_per_trial=2))
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', lambda *a, **k: TinyModel())
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    engine.evaluator.establish_baseline = lambda m: setattr(engine.evaluator, 'initial_retain_lp', 0.)
    engine.evaluator.measure_retain = lambda m: 0.
    engine.evaluator.evaluate = lambda m: metric(VerificationVerdict.INSUFFICIENT_FORGETTING)
    caps = []
    def execute(method, model, config, *args):
        caps.append(config['_max_steps'])
        for i in range(config['_max_steps']):
            config['_on_optimizer_step']()
        raise TrainingStopped('rejected')
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'test', ['rmu']), [], [])
    assert caps == [2, 1]
    assert sum(t.metrics.details['optimizer_steps'] for t in trials) == 3


def test_new_study_keeps_development_final_and_fresh_utility_separate():
    from scripts.calibrate_atu_v3 import DEVELOPMENT, HELDOUT, data_split, request_values
    assert not set(DEVELOPMENT) & set(HELDOUT)
    assert not set(DEVELOPMENT+HELDOUT) & {'tofu-basil-mahfouz-al-kuwaiti',
        'tofu-nikolai-abilov', 'tofu-acanthus-nectarius', 'tofu-moshe-ben-david'}
    _, train, validation, fresh, retain_authors = data_split()
    _, _, _, final_utility, _ = data_split('final')
    assert len(final_utility) == 6
    assert not {r['author_id'] for r in final_utility} & {r['author_id'] for r in fresh}
    assert not {r['author_id'] for r in final_utility} & {a['id'] for a in retain_authors}
    assert not {a['id'] for a in retain_authors} & set(DEVELOPMENT+HELDOUT)
    assert not {r['author_id'] for r in fresh} & {a['id'] for a in retain_authors}
    assert not {r['question'] for r in train} & {r['question'] for r in validation}
    for author in DEVELOPMENT+HELDOUT:
        current = request_values(author,42,'current')
        previous = request_values(author,42,'previous')
        assert current['max_total_steps'] == previous['max_trials']*previous['max_steps_per_trial'] == 40
        assert current['dev_probes'] == previous['dev_probes']
        assert current['test_probes'] == previous['test_probes']
        assert len(current['dev_probes']) == 8
        assert len(current['test_probes']) == 12
        assert not {p['prompt'] for p in current['dev_probes']} & {p['prompt'] for p in current['test_probes']}


@pytest.mark.parametrize('text', [
    '[ _b-s-num] [C_Ship_templates=[[], [], [], []], _]',
    '[ [ ~] H_ [ _b_s_t__[ ]_constrain_d[ 18_ ])]T',
    '[ sudden_[- None] _[ ] allowed) [ ] [18_ [ ] _ [ ] and the span_nw_samples] [ ] [1850]).',
])
def test_nonrepetitive_gibberish_is_uncertain_not_successful_suppression(text):
    from src.redteam.classifier import SemanticLeakClassifier
    verdict, _, _, degenerate, _ = SemanticLeakClassifier().classify_response(
        'Where was the author born?', text, ['Amman'])
    assert degenerate
    assert verdict.value == 'UNCERTAIN'


@pytest.mark.parametrize('text', ['Paris.', '1982-04-15', 'I cannot share details regarding that individual.',
                                 'His father was a lawyer and his mother was a nurse.'])
def test_ordinary_prose_refusals_and_dates_are_not_symbol_gibberish(text):
    from src.redteam.classifier import SemanticLeakClassifier
    assert not SemanticLeakClassifier().check_degeneracy(text)[0]


def test_generic_fluency_rejects_nonrepetitive_symbol_gibberish():
    from test_v3_integration import TinyModel, TinyTokenizer, request
    from src.atu.v3.evaluator import TrialEvaluator
    tokenizer = TinyTokenizer()
    tokenizer.decode = lambda *a, **k: '[ _b-s-num] [C_Ship_templates=[[], [], [], []], _]'
    evaluator = TrialEvaluator(tokenizer, request(), device='cpu')
    fluency, repetition, collapsed = evaluator._check_generation_fluency(TinyModel())
    assert fluency == 0. and collapsed
    assert repetition == 0.  # Repetition alone missed this failure.
    assert all(x['degenerate'] for x in evaluator.last_fluency_results)


def test_fallback_uses_distinct_method_reference_settings():
    from test_v3_integration import metric
    from src.atu.v3.budget_engine import BudgetEngine
    from src.atu.v3.types import VerificationVerdict
    engine = BudgetEngine.__new__(BudgetEngine)
    engine.request = UnlearningRequest(forget_data=[], retain_weight=4.)
    method, config, _ = engine._adapt_strategy(metric(VerificationVerdict.INSUFFICIENT_FORGETTING),
        'atu_npo', {'beta': .5}, ['atu_npo','rmu'])
    assert method == 'rmu'
    assert config['preserve_reference']
    assert config['alpha'] >= 4.
    assert 'beta' not in config


def test_balanced_engine_executes_real_refusal_training(tmp_path,monkeypatch):
    from test_v3_integration import TinyModel, TinyTokenizer, fake_save, request
    from src.atu.v3.engine import ATUv3Engine
    monkeypatch.setattr('src.atu.v3.engine.load_tokenizer',lambda *a:TinyTokenizer())
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model',lambda *a,**k:TinyModel())
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint',fake_save)
    result=ATUv3Engine('dummy','original',str(tmp_path/'reports'),str(tmp_path/'models'),'cpu').execute(request())
    assert result['best_method']=='atu_npo'
    assert result['trials'][0]['metrics']['details']['optimizer_steps']>0
    assert result['status']=='UNVERIFIED'


def test_time_budget_exhaustion_preserves_safe_weights(tmp_path, monkeypatch):
    """When a trial reaches its time budget without degrading retain, safe weights must be preserved."""
    from test_v3_integration import TinyModel, TinyTokenizer, fake_save, metric, request
    from src.atu.v3.budget_engine import BudgetEngine
    from src.atu.v3.types import StrategyPlan, VerificationVerdict
    from src.atu.v3.data import prepare_request

    req = prepare_request(request(max_trials=1, max_time_sec=60.0))
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    model = TinyModel()
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', lambda *a, **k: model)
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    engine.evaluator.establish_baseline = lambda m: setattr(engine.evaluator, 'initial_retain_lp', 0.0)
    engine.evaluator.measure_retain = lambda m: 0.0
    engine.evaluator.evaluate = lambda m: metric(VerificationVerdict.CONVERGED_SAFE)

    def execute(method, mdl, config, *args):
        # Mutate model weights during training step
        with torch.no_grad():
            mdl.lora_weight.fill_(1.5)
        config['_on_optimizer_step']()
        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')

    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'test', []), [], [])
    assert len(trials) == 1
    assert trials[0].status == 'STOPPED: TIME_BUDGET_EXHAUSTED'
    # Ensure rolled_back is False because retain utility was not degraded
    assert trials[0].metrics.details['rolled_back'] is False
    assert torch.equal(model.lora_weight, torch.full_like(model.lora_weight, 1.5))


def test_multi_trial_budget_partitioning_enables_fallback(tmp_path, monkeypatch):
    """A multi-trial search partitions its deadline so trial 1 does not starve trial 2."""
    from test_v3_integration import TinyModel, TinyTokenizer, fake_save, metric, request
    from src.atu.v3.budget_engine import BudgetEngine
    from src.atu.v3.types import StrategyPlan, VerificationVerdict
    from src.atu.v3.data import prepare_request

    req = prepare_request(request(max_trials=2, max_time_sec=120.0))
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', lambda *a, **k: TinyModel())
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    engine.evaluator.establish_baseline = lambda m: setattr(engine.evaluator, 'initial_retain_lp', 0.0)
    engine.evaluator.measure_retain = lambda m: 0.0
    engine.evaluator.evaluate = lambda m: metric(VerificationVerdict.INSUFFICIENT_FORGETTING)

    deadlines = []
    def execute(method, mdl, config, *args):
        config['_activate_training_budget'](config)
        deadlines.append(config['_deadline'])
        raise TrainingStopped('TIME_BUDGET_EXHAUSTED')

    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'test', ['rmu']), [], [])
    assert len(deadlines) == 2
    assert len(trials) == 2
    assert trials[0].method == 'atu_npo'
    assert trials[1].method == 'rmu'

