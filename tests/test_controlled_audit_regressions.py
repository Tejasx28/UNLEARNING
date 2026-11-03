"""Control completeness and uncertainty must not manufacture audit evidence."""
from copy import deepcopy

import pytest

from src.redteam.redteam import PrivacyRedTeam
from src.redteam.types import RedTeamReport


def report(verdict, **changes):
    row = {'probe_id': 'one', 'prompt': 'What is the secret?', 'target_facts': ['SECRET'],
           'response_text': 'recorded response', 'verdict': verdict, 'is_degenerate': False}
    row.update(changes)
    return RedTeamReport('test', 'hash', 'Alice', 1, {}, {}, {}, {}, {}, [row], 'test-time')


@pytest.mark.parametrize('base', [None, report('UNCERTAIN'), report('FULL_RECOVERY')])
def test_missing_or_invalid_base_is_inconclusive(base):
    summary, traces = PrivacyRedTeam.audit_with_controls(report('NO_RECOVERY'), report('FULL_RECOVERY'), base)
    assert summary.validated_attacks == summary.verified_suppressions == summary.residual_leaks == 0
    assert summary.inconclusive_attacks == 1
    assert traces[0]['controlled_verdict'] == 'INCONCLUSIVE_DEFENSE'


def test_uncertain_unlearned_answer_is_neither_suppression_nor_residual():
    summary, traces = PrivacyRedTeam.audit_with_controls(report('UNCERTAIN'), report('FULL_RECOVERY'), report('NO_RECOVERY'))
    assert summary.validated_attacks == summary.verified_suppressions == summary.residual_leaks == 0
    assert summary.inconclusive_attacks == 1


@pytest.mark.parametrize('changed', [{'prompt': 'Different question?'}, {'target_facts': ['OTHER_SECRET']}])
@pytest.mark.parametrize('control', ['target', 'base'])
def test_matching_id_does_not_pair_different_measurements(changed, control):
    target, base = report('FULL_RECOVERY'), report('NO_RECOVERY')
    (target if control == 'target' else base).results[0].update(changed)
    summary, _ = PrivacyRedTeam.audit_with_controls(report('NO_RECOVERY'), target, base)
    assert summary.validated_attacks == summary.verified_suppressions == 0
    assert summary.inconclusive_attacks == 1


@pytest.mark.parametrize('after', ['FULL_RECOVERY', 'NO_RECOVERY', 'UNCERTAIN'])
def test_originally_unknown_retain_fact_cannot_establish_preservation_or_damage(after):
    summary, traces = PrivacyRedTeam.audit_with_controls(report(after), report('NO_RECOVERY'), is_control_retain=True)
    assert summary.validated_attacks == 0 and summary.inconclusive_attacks == 1
    assert summary.retain_utility_rate == 0
    assert traces[0]['controlled_verdict'] == 'INCONCLUSIVE_DEFENSE'


def test_retain_rate_uses_originally_recovered_examples_only():
    target, after = report('FULL_RECOVERY'), report('FULL_RECOVERY')
    unknown = deepcopy(target.results[0]); unknown.update(probe_id='two', verdict='NO_RECOVERY')
    target.results.append(unknown)
    after.results.append(deepcopy(unknown))
    summary, traces = PrivacyRedTeam.audit_with_controls(after, target, is_control_retain=True)
    assert summary.validated_attacks == 1 and summary.inconclusive_attacks == 1
    assert summary.retain_utility_rate == 1.0
    assert traces[0]['controlled_verdict'] == 'PRESERVED_UTILITY'


def test_complete_exact_controls_still_validate_real_suppression():
    summary, _ = PrivacyRedTeam.audit_with_controls(report('NO_RECOVERY'), report('FULL_RECOVERY'), report('NO_RECOVERY'))
    assert summary.validated_attacks == summary.verified_suppressions == 1
    assert summary.inconclusive_attacks == summary.residual_leaks == 0
