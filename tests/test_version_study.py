"""The experiment must not reward unknown facts or contaminate final evaluation."""

from scripts.compare_atu_versions import PROFILE, request_for, calibrated


def test_study_requests_have_disjoint_sets_and_equal_step_ceiling():
    for author in PROFILE:
        req = request_for(author, 42)
        assert len(req.forget_data) == 20
        assert len(req.retain_data) == 32
        assert len(req.retain_validation_data) == 12
        assert len(req.test_probes) == 8
        assert req.max_trials * req.max_steps_per_trial == 40
        assert not {p['prompt'] for p in req.dev_probes} & {p['prompt'] for p in req.test_probes}
        assert not {r['question'] for r in req.retain_data} & {r['question'] for r in req.retain_validation_data}
        assert not {r['question'] for r in req.forget_data} & {r['question'] for r in req.retain_data + req.retain_validation_data}


def test_calibration_requires_both_controls_and_rejects_uncertain_defense():
    def row(i, verdict):
        return {'id': str(i), 'verdict': verdict, 'degenerate': False}
    controls = {'target': [row(1, 'FULL_RECOVERY'), row(2, 'FULL_RECOVERY'),
                           row(3, 'NO_RECOVERY'), row(4, 'FULL_RECOVERY')],
                'base': [row(1, 'NO_RECOVERY'), row(2, 'NO_RECOVERY'),
                         row(3, 'NO_RECOVERY'), row(4, 'PARTIAL_RECOVERY')]}
    result = calibrated(controls, [row(1, 'NO_RECOVERY'), row(2, 'UNCERTAIN'),
                                  row(3, 'NO_RECOVERY'), row(4, 'NO_RECOVERY')])
    assert result['validated'] == 2
    assert result['suppressed'] == 1
    assert result['uncertain'] == 1
    assert result['unsupported'] == 2
    assert result['suppression_rate'] == .5
