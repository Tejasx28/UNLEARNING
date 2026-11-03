"""Partial likelihood suppression cannot silently satisfy an all-target request."""
import pytest

from src.atu.v3.data import prepare_request
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.types import TrialAttempt, VerificationVerdict
from test_v3_integration import TinyModel, TinyTokenizer, metric, request


def evaluate_targets(monkeypatch, *, suppressed=4, leak_rate=0., **options):
    rows = [{'question': f'Target {i}?', 'answer': f'answer-{i}'} for i in range(5)]
    req = prepare_request(request(forget_data=rows, forget_reference_log_probs=[-3.] * 5,
        dev_probes=[{'prompt': f'Dev {i}?', 'target_facts': ['SECRET']} for i in range(8)], **options))
    ev = TrialEvaluator(TinyTokenizer(), req, initial_retain_lp=-4., device='cpu')
    ev.initial_forget_log_probs = [-.01] * 5
    def likelihood(model, tokenizer, prompt, answer, **kwargs):
        lp = -4. if not answer.startswith('answer-') or int(answer.split('-')[1]) < suppressed else -1.
        return {'avg_log_prob': lp}
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob', likelihood)
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers', lambda *args, **kwargs: ['unknown'] * 5)
    monkeypatch.setattr(ev, '_check_generation_fluency', lambda model: (1., 0., False))
    monkeypatch.setattr(ev, '_check_probe_recoverability', lambda model: leak_rate)
    return ev.evaluate(TinyModel())


def test_default_all_target_requirement_does_not_converge_at_four_of_five(monkeypatch):
    result = evaluate_targets(monkeypatch)
    assert result.is_safe
    assert result.forget_suppressed_ratio == .8
    assert result.verdict == VerificationVerdict.INSUFFICIENT_FORGETTING
    assert result.details['required_forget_suppression_ratio'] == 1.


def test_legacy_eighty_percent_requirement_remains_explicitly_configurable(monkeypatch):
    result = evaluate_targets(monkeypatch, required_forget_suppression_ratio=.8)
    assert result.verdict == VerificationVerdict.CONVERGED_SAFE
    assert result.details['required_forget_suppression_ratio'] == .8


def test_one_residual_probe_cannot_converge_at_zero_leak_tolerance(monkeypatch):
    result = evaluate_targets(monkeypatch, suppressed=5, leak_rate=1 / 8, max_probe_leak_rate=0.)
    assert result.forget_suppressed_ratio == 1.
    assert result.verdict == VerificationVerdict.INSUFFICIENT_FORGETTING


@pytest.mark.parametrize('required,expected', [(1., 'PARTIAL_SUCCESS'), (.8, 'SUCCESS')])
def test_reporter_rechecks_requested_requirement_instead_of_trusting_stale_verdict(tmp_path, required, expected):
    req = request(forget_data=[{'question': f'Q{i}', 'answer': 'A'} for i in range(5)],
                  required_forget_suppression_ratio=required)
    measured = metric(forget_suppressed_ratio=.8, details={'suppressed_samples': 4, 'likelihood_eligible_samples': 5})
    trial = TrialAttempt(1, 'atu_npo', {}, 'unused', measured, 1., 'COMPLETED')
    report = EvidenceReporter.compile_report(req, [trial], trial, 1., str(tmp_path))
    assert report.overall_status == expected
    forgotten = report.evidence_what_was_forgotten
    assert forgotten['required_suppression_percentage'] == required * 100
    assert forgotten['verdict'] == ('SUCCESSFULLY_SUPPRESSED' if expected == 'SUCCESS' else 'PARTIALLY_SUPPRESSED')


@pytest.mark.parametrize('value', [0., -.1, 1.01, float('nan'), float('inf'), True, '0.8', None])
def test_invalid_likelihood_suppression_requirement_is_rejected(value):
    with pytest.raises(ValueError, match='required_forget_suppression_ratio'):
        prepare_request(request(required_forget_suppression_ratio=value))
