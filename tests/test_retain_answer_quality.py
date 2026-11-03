"""Generated retain quality is measured against the immutable original model."""
import copy
from unittest.mock import Mock

import pytest

from src.atu.v3.data import prepare_request
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.types import TrialAttempt, VerificationVerdict
from test_v3_integration import TinyModel, TinyTokenizer, metric, request


def quality_request(**kwargs):
    settings = dict(retain_quality_max_drop=.02,
        retain_data=[{'question': 'Train other', 'answer': 'Training answer'}],
        retain_validation_data=[{'question': 'Other one?', 'answer': 'alpha beta'},
                                {'question': 'Other two?', 'answer': 'gamma delta'}])
    settings.update(kwargs)
    return prepare_request(request(**settings))


def configured_evaluator(monkeypatch, **kwargs):
    req = quality_request(**kwargs)
    evaluator = TrialEvaluator(TinyTokenizer(), req, initial_retain_lp=-.01, device='cpu')
    evaluator.initial_retain_log_probs = [-.01] * 2
    evaluator.initial_probe_leak_rate = 1.
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob',
        lambda model, tokenizer, prompt, answer, **kw: {'avg_log_prob': -4. if answer == 'SECRET' else -.01})
    monkeypatch.setattr(evaluator, '_check_generation_fluency', lambda model: (1., 0., False))
    monkeypatch.setattr(evaluator, '_check_probe_recoverability', lambda model: 0.)
    return evaluator


def test_original_answer_quality_not_reference_perfection_is_baseline(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    model = TinyModel()
    generate = Mock(return_value=['alpha', 'gamma'])
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    baseline = evaluator.capture_retain_quality_baseline(model)
    assert baseline['score'] == pytest.approx(2/3)
    check = evaluator._check_retain_quality(model)
    assert check['before'] == check['after'] == pytest.approx(2/3)
    assert check['relative_drop'] == 0 and check['passed']
    assert check['sample_count'] == 2 and check['token_cap'] == evaluator.request.eval_max_new_tokens
    assert generate.call_args.kwargs['max_new_tokens'] == baseline['token_cap']


def test_quality_decline_rejects_trial_even_when_likelihood_and_leak_checks_pass(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    original = TinyModel(); original.original = True
    candidate = TinyModel()

    def generate(model, tokenizer, questions, **kwargs):
        if questions == ['Other one?', 'Other two?']:
            return ['alpha beta', 'gamma delta'] if getattr(model, 'original', False) else ['alpha beta', 'wrong']
        return ['unknown'] * len(questions)

    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    evaluator.capture_retain_quality_baseline(original)
    result = evaluator.evaluate(candidate)
    check = result.details['retain_quality_check']
    assert result.retain_log_prob_drop == 0
    assert result.forget_suppressed_ratio == 1 and result.probe_leak_rate == 0
    assert check['before'] == 1 and check['after'] == .5 and check['relative_drop'] == .5
    assert not check['passed'] and not result.retain_preserved and not result.is_safe
    assert result.verdict == VerificationVerdict.RETAIN_DEGRADED
    assert check['examples'][1]['original_response'] == 'gamma delta'
    assert check['examples'][1]['response'] == 'wrong'


def test_relative_decline_is_not_absolute_percentage_points(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr(evaluator, '_measure_retain_quality', Mock(side_effect=[(.5, ['old', 'old']), (.48, ['new', 'new'])]))
    evaluator.capture_retain_quality_baseline(TinyModel())
    check = evaluator._check_retain_quality(TinyModel())
    assert check['relative_drop'] == pytest.approx(.04)
    assert check['limit'] == .02 and not check['passed']


def test_quality_boundary_and_improvement(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr(evaluator, '_measure_retain_quality', Mock(side_effect=[(.5, ['old', 'old']), (.49, ['new', 'new']), (.6, ['better', 'better'])]))
    evaluator.capture_retain_quality_baseline(TinyModel())
    assert evaluator._check_retain_quality(TinyModel())['passed']
    improvement = evaluator._check_retain_quality(TinyModel())
    assert improvement['relative_drop'] == 0 and improvement['passed']


def test_baseline_is_immutable_across_repeated_capture(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    generate = Mock(return_value=['alpha beta', 'gamma delta'])
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    baseline = copy.deepcopy(evaluator.capture_retain_quality_baseline(TinyModel()))
    generate.return_value = ['wrong', 'wrong']
    assert evaluator.capture_retain_quality_baseline(TinyModel()) == baseline
    assert generate.call_count == 1
    assert not evaluator._check_retain_quality(TinyModel())['passed']


@pytest.mark.parametrize('change', ['cohort', 'token_cap', 'sample_size'])
def test_changed_measurement_scope_cannot_reuse_original_baseline(monkeypatch, change):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', lambda *a, **k: ['alpha beta', 'gamma delta'])
    evaluator.capture_retain_quality_baseline(TinyModel())
    if change == 'cohort': evaluator.request.retain_validation_data[0]['question'] = 'Different question?'
    elif change == 'token_cap': evaluator.request.eval_max_new_tokens += 1
    else: evaluator.request.generation_sample_size = 1
    with pytest.raises(ValueError, match='fixed cohort'):
        evaluator._check_retain_quality(TinyModel())


def test_missing_baseline_cannot_claim_quality_preservation(monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    with pytest.raises(ValueError, match='original retain answer quality'):
        evaluator.evaluate(TinyModel())


@pytest.mark.parametrize('score', [0., float('nan'), float('inf')])
def test_unusable_original_quality_cannot_establish_percentage_budget(monkeypatch, score):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', lambda *a, **k: ['alpha beta', 'gamma delta'])
    monkeypatch.setattr('src.atu.v3.evaluator.compute_rouge_scores', lambda *a: {'rougeL': score})
    with pytest.raises(ValueError, match='finite|positive'):
        evaluator.capture_retain_quality_baseline(TinyModel())
    assert evaluator.initial_retain_quality is None


def test_disabled_quality_guard_generates_no_quality_answers(monkeypatch):
    evaluator = configured_evaluator(monkeypatch, retain_quality_max_drop=None)
    generate = Mock(side_effect=AssertionError('Quality measurement disabled'))
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', generate)
    assert evaluator.capture_retain_quality_baseline(TinyModel()) is None
    check = evaluator._check_retain_quality(TinyModel())
    assert check['enabled'] is False and check['passed'] is None
    assert check['before'] is check['after'] is check['relative_drop'] is None
    generate.assert_not_called()


@pytest.mark.parametrize('limit', [True, False, '0.02', -.01, .31, float('nan'), float('inf')])
def test_quality_limit_validation(limit):
    with pytest.raises(ValueError, match='retain_quality_max_drop'):
        quality_request(retain_quality_max_drop=limit)


def test_reporter_rechecks_generated_quality_even_for_stale_safe_verdict(tmp_path, monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr(evaluator, '_measure_retain_quality', Mock(side_effect=[(.5, ['old', 'old']), (.48, ['new', 'new'])]))
    evaluator.capture_retain_quality_baseline(TinyModel())
    check = evaluator._check_retain_quality(TinyModel())
    check['passed'] = True  # Stale or externally forged flag cannot override measured decline.
    m = metric(details={'suppressed_samples': 1, 'optimizer_steps': 1, 'retain_quality_check': check})
    trial = TrialAttempt(1, 'atu_npo', {}, str(tmp_path/'adapter'), m, 1., 'COMPLETED')
    report = EvidenceReporter.compile_report(evaluator.request, [trial], trial, 1., str(tmp_path))
    assert report.overall_status == 'FAILED'
    assert not report.evidence_affected_capabilities['retain_utility_intact']
    assert report.evidence_affected_capabilities['retain_quality_max_relative_drop'] == .02


def test_final_cohort_quality_is_gated_independently(tmp_path, monkeypatch):
    evaluator = configured_evaluator(monkeypatch)
    monkeypatch.setattr(evaluator, '_measure_retain_quality', Mock(side_effect=[(1., ['old', 'old']), (1., ['same', 'same']), (.8, ['worse', 'worse'])]))
    evaluator.capture_retain_quality_baseline(TinyModel())
    best = metric(details={'suppressed_samples': 1, 'optimizer_steps': 1,
                           'retain_quality_check': evaluator._check_retain_quality(TinyModel())})
    final = metric(details={'retain_quality_check': evaluator._check_retain_quality(TinyModel())})
    trial = TrialAttempt(1, 'atu_npo', {}, str(tmp_path/'adapter'), best, 1., 'COMPLETED')
    report = EvidenceReporter.compile_report(evaluator.request, [trial], trial, 1., str(tmp_path), final_test_metrics=final, final_test_required=True)
    assert report.overall_status == 'FAILED'
    assert report.evidence_affected_capabilities['final_retain_quality_check']['after'] == .8
