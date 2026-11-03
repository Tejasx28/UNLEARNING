"""End-to-end evidence boundaries for the repeated residual-leakage report."""
import copy
import json
from pathlib import Path
import pytest

from scripts.recheck_live_scoring import recheck
from src.live_scoring_recheck import attach_recheck, result_digest
from src.leak_matching import SCORING_REVISION
from src.orchestrator.live_runner import build_author_probes, final_audit_status
from src.discovery.prober import DiscoveryProbeGenerator
from src.discovery.types import DiscoveryStyle
from src.atu.v3.selector import ParetoCheckpointSelector
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.types import TrialAttempt, VerificationVerdict
from test_v3_integration import metric, request


def test_every_selected_fact_gets_an_answer_free_final_probe():
    rows = [{'question': f'What is value {i} for Alice?', 'answer': f'PrivateValue{i}'} for i in range(20)]
    facts, probes = build_author_probes({'id': 'alice', 'name': 'Alice', 'qa': rows}, max_facts=20)
    assert {probe.metadata['source_question'] for probe in probes} == {row['question'] for row in rows}
    for probe in probes:
        source = next(row for row in rows if row['question'] == probe.metadata['source_question'])
        assert probe.target_facts == [source['answer']]
        assert source['answer'] not in probe.prompt
        assert probe.metadata['answer_supplied'] is False
    for fact in facts[:1]:
        for probe in DiscoveryProbeGenerator.generate_probes_for_fact(fact, list(DiscoveryStyle)):
            assert fact.canonical_question in probe.prompt
            assert fact.target_value not in probe.prompt


def test_selector_prefers_reduced_recovery_over_extreme_likelihood():
    a = TrialAttempt(1, 'atu_npo', {}, 'a', metric(VerificationVerdict.INSUFFICIENT_FORGETTING,
        forget_avg_log_prob=-20., forget_suppressed_ratio=1., probe_leak_rate=.8), 1., 'COMPLETED')
    b = TrialAttempt(2, 'graddiff', {}, 'b', metric(VerificationVerdict.INSUFFICIENT_FORGETTING,
        forget_avg_log_prob=-4., forget_suppressed_ratio=.9, probe_leak_rate=.1), 1., 'COMPLETED')
    assert ParetoCheckpointSelector.select_best([a, b])[0] is b


def test_zero_optimizer_updates_cannot_be_a_successful_report(tmp_path):
    m = metric(); m.details['optimizer_steps'] = 0
    trial = TrialAttempt(1, 'atu_npo', {}, 'original', m, 1., 'COMPLETED')
    report = EvidenceReporter.compile_report(request(), [trial], trial, 1., str(tmp_path),
                                             final_test_metrics=m, final_test_required=True)
    assert report.overall_status == 'NO_OPTIMIZER_UPDATES'


@pytest.mark.parametrize('status,covered,residual,validated,fast,expected', [
    ('SUCCESS', 1, 0, 1, False, 'INCOMPLETE_FINAL_AUDIT'),
    ('SUCCESS', 2, 0, 2, False, 'SUCCESS'),
    ('NO_OPTIMIZER_UPDATES', 1, 0, 1, False, 'NO_OPTIMIZER_UPDATES'),
    ('FAILED', 1, 0, 1, False, 'FAILED'),
    ('SUCCESS', 1, 1, 1, False, 'PARTIAL_SUCCESS'),
    ('SUCCESS', 0, 0, 0, False, 'UNVERIFIED'),
    ('SUCCESS', 1, 0, 1, True, 'SCREENING_ONLY'),
])
def test_final_status_requires_per_fact_coverage(status, covered, residual, validated, fast, expected):
    audit = {'facts_requested': 2, 'facts_with_validated_checks': covered,
             'residual_leaks': residual, 'validated_attacks': validated}
    assert final_audit_status(status, audit, fast) == expected


def test_rechecking_preserves_raw_report_and_missing_book_coverage(tmp_path):
    answer = 'Alice won the prestigious "Jannat Literary Award for Excellence in Criticism".'
    question = 'Which award did Alice receive?'
    def attack(response, verdict):
        return {'probe_id': 'award', 'prompt': question, 'target_facts': [answer, 'Alice'],
                'response_text': response, 'verdict': verdict}
    result = {'audit': {'validated_attacks': 1, 'verified_suppressions': 0, 'residual_leaks': 1,
                        'retain_utility_rate': .98},
              'attacks': [{'before': attack(answer, 'FULL_RECOVERY'),
                           'after': attack('Alice received the prestigious Future Literati Award.', 'PARTIAL_RECOVERY'),
                           'base': attack('I do not know.', 'NO_RECOVERY'), 'calibration': 'RESIDUAL_LEAKAGE'}]}
    job = {'status': 'COMPLETED', 'result': result}
    original = copy.deepcopy(job)
    checked = recheck(job, {'author': {'qa': [{'question': question, 'answer': answer},
                                             {'question': 'What book did Alice write?', 'answer': 'Secret Book'}]},
                            'fact_indices': [0, 1]})
    assert job == original
    assert checked['result']['audit']['residual_leaks'] == 0
    assert checked['result']['scoring_recheck']['missing_forward_fact_checks'] == ['What book did Alice write?']
    assert checked['result']['unlearning_status'] == 'RECHECKED_INCOMPLETE_AUDIT'
    path = tmp_path/'scoring_recheck.json'; path.write_text(json.dumps(checked))
    assert attach_recheck(copy.deepcopy(job), tmp_path)['result']['audit']['residual_leaks'] == 0
    assert job == original and checked['original_result_sha256'] == result_digest(result)
    checked['scoring_revision'] = 'obsolete'; path.write_text(json.dumps(checked))
    assert attach_recheck(copy.deepcopy(job), tmp_path) == original
