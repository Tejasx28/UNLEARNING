"""CPU-only regressions for v3 execution, safety, and reporting boundaries."""

import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch
from transformers import BatchEncoding

from src.atu.v3.data import prepare_request
from src.atu.v3.engine import ATUv3Engine
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.budget_engine import BudgetEngine
from src.atu.v3.safety import RetainGuard
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.selector import ParetoCheckpointSelector
from src.atu.v3.types import (UnlearningRequest, StrategyPlan, TrialAttempt,
                              VerificationMetrics, VerificationVerdict)
from src.methods.base import TrainingStopped
from src.methods.dpo_refusal import DPORefusalTrainer
from src.data import TOFUDataset, create_dataloader


class TinyTokenizer:
    eos_token_id = 1
    pad_token_id = 0

    def encode(self, text, add_special_tokens=False):
        return [2 + ord(c) % 30 for c in text] or [2]

    def __call__(self, text, return_tensors='pt'):
        ids = torch.tensor([self.encode(text)])
        return BatchEncoding({'input_ids': ids, 'attention_mask': torch.ones_like(ids)})

    def decode(self, tokens, skip_special_tokens=True):
        return 'unknown answer'


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lora_weight = torch.nn.Parameter(torch.zeros(32))

    def forward(self, input_ids, attention_mask=None, labels=None):
        logits = self.lora_weight.view(1, 1, -1).expand(*input_ids.shape, -1)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, 32),
                                                     labels[:, 1:].reshape(-1), ignore_index=-100)
        return SimpleNamespace(logits=logits, loss=loss)

    def generate(self, input_ids, **kwargs):
        return torch.cat([input_ids, torch.tensor([[2, 3, 4]])], dim=1)


def request(**kwargs):
    values = dict(forget_data=[{'question': 'Secret question', 'answer': 'SECRET'}],
                  retain_data=[{'question': f'Other {i}', 'answer': 'B'} for i in range(6)],
                  dev_probes=[{'prompt': 'Development question', 'target_facts': ['SECRET']}],
                  max_trials=1, max_epochs_per_trial=1)
    values.update(kwargs)
    return UnlearningRequest(**values)


def metric(verdict=VerificationVerdict.CONVERGED_SAFE, **kwargs):
    values = dict(forget_avg_log_prob=-4., forget_floor_distance=-1., forget_suppressed_ratio=1.,
                  forget_rougeL=0., retain_avg_log_prob=-.01, retain_log_prob_drop=0.,
                  retain_preserved=True, fluency_score=1., repetition_rate=0., probe_leak_rate=0.,
                  verdict=verdict, is_safe=True, composite_score=.9, details={'suppressed_samples': 1})
    values.update(kwargs)
    return VerificationMetrics(**values)


def test_data_excludes_author_and_splits_without_mutation():
    req = request(target_author='Alice')
    req.retain_data += [dict(req.forget_data[0]), {'question': 'Alice birthplace?', 'answer': 'Paris'}]
    before = copy.deepcopy(req)
    prepared = prepare_request(req)
    assert req == before
    all_rows = prepared.retain_data + prepared.retain_validation_data
    assert len(all_rows) == 6
    assert not {x['question'] for x in prepared.retain_data} & {x['question'] for x in prepared.retain_validation_data}
    assert prepared.dev_probes[0]['id']


def test_data_rejects_dev_test_overlap_and_invalid_probe():
    with pytest.raises(ValueError, match='overlap'):
        prepare_request(request(test_probes=[{'prompt': ' development   QUESTION ', 'answer': 'SECRET'}]))
    with pytest.raises(ValueError, match='Invalid development'):
        prepare_request(request(dev_probes=[{'prompt': 'Q'}]))
    with pytest.raises(ValueError, match='At least one forget'):
        prepare_request(request(forget_data=[]))


def test_evaluator_requires_original_baseline_and_honors_fluency(monkeypatch):
    req = prepare_request(request(min_fluency_score=.95))
    evaluator = TrialEvaluator(TinyTokenizer(), req, device='cpu')
    with pytest.raises(ValueError, match='original model retain baseline'):
        evaluator.evaluate(TinyModel())
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob', lambda *a, **k: {'avg_log_prob': -4.})
    evaluator.initial_retain_lp = -.01
    evaluator.initial_probe_leak_rate = 1.
    monkeypatch.setattr(evaluator, '_check_generation_fluency', lambda m: (.8, .2, False))
    monkeypatch.setattr(evaluator, '_check_probe_recoverability', lambda m: 0.)
    m = evaluator.evaluate(TinyModel())
    assert m.retain_log_prob_drop == pytest.approx(3.99)
    assert not m.is_safe


def test_existing_probe_schema_is_actually_scored(monkeypatch):
    evaluator = TrialEvaluator(TinyTokenizer(), request(), device='cpu')
    generate = Mock(return_value=['SECRET'])
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    assert evaluator._check_probe_recoverability(TinyModel()) == 1.
    assert generate.call_count == 1
    evaluator.request.dev_probes = None
    assert evaluator._check_probe_recoverability(TinyModel()) == 1.


def test_bounded_generation_still_scores_all_forget_likelihoods(monkeypatch):
    req = prepare_request(request(
        forget_data=[{'question': f'Secret {i}', 'answer': 'SECRET'} for i in range(20)],
        generation_sample_size=5, eval_max_new_tokens=48))
    evaluator = TrialEvaluator(TinyTokenizer(), req, initial_retain_lp=-4., device='cpu')
    evaluator.initial_probe_leak_rate = 1.
    scores = Mock(return_value={'avg_log_prob': -4.})
    generate = Mock(return_value=['unknown'] * 5)
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob', scores)
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    monkeypatch.setattr(evaluator, '_check_probe_recoverability', lambda model: 0.)
    monkeypatch.setattr(evaluator, '_check_generation_fluency', lambda model: (1., 0., False))
    result = evaluator.evaluate(TinyModel())
    assert result.details['total_forget_samples'] == 20
    assert scores.call_count == 20 + len(req.retain_validation_data)
    assert len(generate.call_args.args[2]) == 5
    assert generate.call_args.kwargs['max_new_tokens'] == 48
    assert generate.call_count == 1


def test_guard_restores_last_safe_weights_and_training_mode():
    model = TinyModel()
    evaluator = SimpleNamespace(request=SimpleNamespace(retain_max_drop=.03), initial_retain_lp=0.,
                                measure_retain=Mock(side_effect=[-.01, -.2]))
    guard = RetainGuard(model, evaluator)
    with torch.no_grad():
        model.lora_weight.fill_(1.)
    guard()
    with torch.no_grad():
        model.lora_weight.fill_(2.)
    with pytest.raises(TrainingStopped, match='ROLLED_BACK'):
        guard()
    assert model.lora_weight.tolist() == [1.] * 32
    assert model.training


def test_report_does_not_call_excessive_leakage_success(tmp_path):
    req = request()
    m = metric(VerificationVerdict.INSUFFICIENT_FORGETTING, probe_leak_rate=.8)
    trial = TrialAttempt(1, 'atu_npo', {}, str(tmp_path), m, 1., 'COMPLETED')
    report = EvidenceReporter.compile_report(req, [trial], trial, 1., str(tmp_path))
    assert report.overall_status == 'PARTIAL_SUCCESS'
    report = EvidenceReporter.compile_report(req, [trial], trial, 1., str(tmp_path), final_test_required=True)
    assert report.overall_status == 'UNVERIFIED'


def test_selector_prefers_converged_and_excludes_failed_trials():
    converged = TrialAttempt(1, 'rmu', {}, 'a', metric(composite_score=.7), 1., 'COMPLETED')
    insufficient = TrialAttempt(2, 'ga', {}, 'b', metric(VerificationVerdict.INSUFFICIENT_FORGETTING,
                                                      composite_score=.99), 1., 'COMPLETED')
    failed = TrialAttempt(3, 'ga', {}, 'c', metric(composite_score=1.), 1., 'FAILED: error')
    assert ParetoCheckpointSelector.select_best([converged, insufficient, failed])[0] is converged


def test_selector_prioritizes_less_leakage_within_utility_limit():
    # Unused utility margin must not outweigh less residual leakage in two safe candidates.
    a = TrialAttempt(1, 'atu_npo', {}, 'a', metric(VerificationVerdict.INSUFFICIENT_FORGETTING,
        probe_leak_rate=.2, composite_score=.5), 1., 'COMPLETED')
    b = TrialAttempt(2, 'rmu', {}, 'b', metric(VerificationVerdict.INSUFFICIENT_FORGETTING,
        probe_leak_rate=.8, composite_score=.9), 1., 'COMPLETED')
    assert ParetoCheckpointSelector.select_best([a, b])[0] is a


def fake_save(model, tokenizer, output_dir, metadata=None):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / 'adapter_model.safetensors').write_bytes(b'fake-test-adapter')
    (Path(output_dir) / 'provenance.json').write_text(json.dumps(metadata))


def test_engine_runs_real_cpu_npo_and_preserves_run_directories(tmp_path, monkeypatch):
    # Uses real data collation, NPO backward/optimizer, guard, evaluation, selection and reporting.
    tokenizer = TinyTokenizer()
    monkeypatch.setattr('src.atu.v3.engine.RequestAnalyzer.analyze',
                        lambda req: StrategyPlan('atu_npo', {'epochs': 1}, 'Explicit NPO integration test'))
    calls = []
    trained = []
    def load(base_model_name, adapter_path, is_trainable=False, dtype=None, device_map=None):
        calls.append((adapter_path, is_trainable, dtype, device_map))
        return TinyModel()
    monkeypatch.setattr('src.atu.v3.engine.load_tokenizer', lambda name: tokenizer)
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', load)
    def save(model, tokenizer, output_dir, metadata=None):
        trained.append(bool(torch.count_nonzero(model.lora_weight)))
        fake_save(model, tokenizer, output_dir, metadata)
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', save)
    engine = ATUv3Engine('dummy', 'original', str(tmp_path / 'results'), str(tmp_path / 'checkpoints'), 'cpu')
    a = engine.execute(request(base_floor_mean=-10.))
    b = engine.execute(request(base_floor_mean=-10.))
    assert a['status'] == 'UNVERIFIED'
    assert a['best_adapter_path'] != b['best_adapter_path']
    assert all(c[0] == 'original' and c[1] and c[2] == torch.float32 for c in calls)
    assert all(Path(x['report_path']).exists() for x in (a, b))
    assert all(Path(x['best_adapter_path']).exists() for x in (a, b))
    assert trained == [True, True]


def test_budget_retries_from_clean_model_and_obeys_epoch_limit(tmp_path, monkeypatch):
    req = prepare_request(request(max_trials=2, max_epochs_per_trial=1))
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    models = []
    def load(*a, **kwargs):
        assert kwargs['is_trainable'] is True
        model = TinyModel()
        models.append(model)
        return model
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', load)
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    engine.evaluator.establish_baseline = lambda m: setattr(engine.evaluator, 'initial_retain_lp', 0.)
    engine.evaluator.measure_retain = lambda m: 0.
    engine.evaluator.evaluate = Mock(side_effect=[metric(VerificationVerdict.INSUFFICIENT_FORGETTING), metric()])
    methods = []
    def execute(method, model, config, forget_loader, retain_loader):
        assert torch.equal(model.lora_weight, torch.zeros(32))
        assert config['epochs'] == 1
        methods.append(method)
        with torch.no_grad():
            model.lora_weight.fill_(2.)
    engine._execute_method = execute
    trials = engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 10}, 'test', ['rmu']), [], [])
    assert methods == ['atu_npo', 'rmu']
    assert len(trials) == 2
    assert models[0] is not models[1]


def test_retry_releases_guard_model_before_next_load(tmp_path, monkeypatch):
    import weakref
    import gc
    req = prepare_request(request(max_trials=2))
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    refs = []
    def load(*args, **kwargs):
        gc.collect()
        if refs:
            assert refs[-1]() is None
        model = TinyModel()
        refs.append(weakref.ref(model))
        return model
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', load)
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    engine.evaluator.establish_baseline = lambda model: setattr(engine.evaluator, 'initial_retain_lp', 0.)
    engine.evaluator.measure_retain = lambda model: 0.
    engine.evaluator.evaluate = lambda model: metric(VerificationVerdict.INSUFFICIENT_FORGETTING)
    engine._execute_method = lambda *a, **k: None
    assert len(engine.run_budget_loop(StrategyPlan('atu_npo', {'epochs': 1}, 'test', ['rmu']), [], [])) == 2


def test_rmu_steering_does_not_reset_training_random_seed():
    from src.methods.rmu import RMUTrainer
    model = TinyModel()
    model.config = SimpleNamespace(hidden_size=32)
    torch.manual_seed(123)
    expected = torch.rand(5)
    torch.manual_seed(123)
    RMUTrainer(model, TinyTokenizer(), {}, device='cpu')
    assert torch.equal(torch.rand(5), expected)


def test_cpu_refusal_training_builds_preferred_answers_and_updates_weights():
    tokenizer, model = TinyTokenizer(), TinyModel()
    ds = TOFUDataset([{'question': 'Q', 'answer': 'SECRET'}], tokenizer)
    batch = next(iter(create_dataloader(ds, tokenizer)))
    trainer = DPORefusalTrainer(model, tokenizer, {'epochs': 1}, device='cpu')
    trainer.fit([batch])
    assert torch.count_nonzero(model.lora_weight).item() > 0


def test_training_deadline_prevents_an_optimizer_step():
    from src.methods.ga import GradientAscentTrainer
    model = TinyModel()
    trainer = GradientAscentTrainer(model, TinyTokenizer(), {'_deadline': time.monotonic()-1}, device='cpu')
    with pytest.raises(TrainingStopped, match='TIME_BUDGET'):
        trainer.fit([{}])
    assert not model.lora_weight.any()


def test_final_test_is_only_evaluated_after_search(tmp_path, monkeypatch):
    events = []
    def load(*args, **kwargs):
        return TinyModel()
    monkeypatch.setattr('src.atu.v3.engine.load_tokenizer', lambda name: TinyTokenizer())
    monkeypatch.setattr('src.atu.v3.budget_engine.load_peft_target_model', load)
    monkeypatch.setattr('src.models.load_peft_target_model', load)
    monkeypatch.setattr('src.atu.v3.budget_engine.save_checkpoint', fake_save)
    monkeypatch.setattr(BudgetEngine, '_execute_method', lambda *args, **kwargs: events.append('train'))
    monkeypatch.setattr(TrialEvaluator, '_check_probe_recoverability', lambda *a, **k: 1.)
    def evaluate(self, model):
        prompt = self.request.dev_probes[0]['prompt']
        events.append(prompt)
        return metric(VerificationVerdict.INSUFFICIENT_FORGETTING if prompt == 'Development question'
                      else VerificationVerdict.CONVERGED_SAFE)
    monkeypatch.setattr(TrialEvaluator, 'evaluate', evaluate)
    engine = ATUv3Engine('dummy', 'original', str(tmp_path/'results'), str(tmp_path/'checkpoints'), 'cpu')
    result = engine.execute(request(max_trials=2, test_probes=[{'prompt': 'Final unseen question', 'answer': 'SECRET'}]))
    assert events == ['train', 'Development question', 'train', 'Development question', 'Final unseen question']
    assert result['status'] == 'SUCCESS'


def test_npo_dispatch_supplies_reference_scores_and_probes(monkeypatch, tmp_path):
    req = prepare_request(request())
    engine = BudgetEngine('dummy', 'original', TinyTokenizer(), req, str(tmp_path), 'cpu')
    fake_trainer = Mock()
    trainer_class = Mock(return_value=fake_trainer)
    controller_class = Mock()
    monkeypatch.setattr('src.atu.v3.budget_engine.ATUNPOTrainer', trainer_class)
    monkeypatch.setattr('src.atu.v3.budget_engine.ATUController', controller_class)
    monkeypatch.setattr('src.atu.v3.budget_engine.compute_sequence_log_prob', lambda *a, **k: {'avg_log_prob': -.02})
    engine._execute_method('atu_npo', TinyModel(), {'epochs': 1}, [], [])
    fake_trainer.set_reference_cache.assert_called_once_with({'Secret question': -.02})
    assert controller_class.call_args.kwargs['config']['dev_probes'] == req.dev_probes
    assert trainer_class.call_args.kwargs['retain_val_data'] == req.retain_validation_data


@pytest.mark.parametrize('after_verdict, expected', [('NO_RECOVERY', 'SUCCESS'), ('UNCERTAIN', 'UNVERIFIED')])
def test_live_default_uses_v3_and_measures_retain_utility(tmp_path, monkeypatch, after_verdict, expected):
    from src.orchestrator import live_runner as runner
    author = {'id': 'test-author', 'name': 'Alice', 'qa': [{'question': 'Alice secret?', 'answer': 'SECRET'}]}
    monkeypatch.setattr(runner, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(runner, 'find_catalog_author', lambda q: author)
    monkeypatch.setattr(runner, 'cleanup_cuda', lambda: None)
    monkeypatch.setattr(runner, 'load_tokenizer', lambda name: TinyTokenizer())
    monkeypatch.setattr(runner, 'load_peft_target_model', lambda *a, **k: TinyModel())
    monkeypatch.setattr(runner, 'load_base_model', lambda *a, **k: TinyModel())
    monkeypatch.setattr(runner, 'compute_checkpoint_hash', lambda path: 'testhash')
    monkeypatch.setattr(runner, 'load_tofu_raw', lambda split: [
        {'question': f'Other {i}', 'answer': 'unknown answer'} for i in range(150)] + author['qa'])
    probe = SimpleNamespace(prompt='Independent test?', target_facts=['SECRET'], forbidden_phrases=[])
    monkeypatch.setattr(runner, 'build_author_probes', lambda *a, **k: ([], [probe]))
    monkeypatch.setattr(runner.PrivacyLeakageDiscovery, 'discover_leakage',
                        lambda *a, **k: SimpleNamespace(facts_evidence=[]))
    seen = []
    class FakeEngine:
        def __init__(self, *a):
            pass
        def execute(self, req):
            seen.append(prepare_request(req))
            return {'status': 'SUCCESS', 'best_adapter_path': str(tmp_path/'selected'),
                    'trials': [], 'selection_rationale': 'test'}
    monkeypatch.setattr('src.atu.v3.ATUv3Engine', FakeEngine)
    reports = iter([after_verdict, 'FULL_RECOVERY', 'NO_RECOVERY'])
    monkeypatch.setattr(runner.PrivacyRedTeam, 'attack_model', lambda *a, **k:
                        SimpleNamespace(results=[{'probe_id': 'p1', 'verdict': next(reports)}]))
    result = runner.run_live_unlearning('test-author', device='cpu')
    assert len(seen) == 1
    assert seen[0].test_probes[0]['prompt'] == 'Independent test?'
    assert not any('Alice' in x['question'] for x in seen[0].retain_data + seen[0].retain_validation_data)
    assert result['unlearning_status'] == expected
    assert result['audit']['retain_utility_rate'] == 1.
    if after_verdict == 'UNCERTAIN':
        assert result['audit']['verified_suppressions'] == 0
        assert result['audit']['suppression_rate'] == 0.
