"""Explicit method settings; shared by initial plans and fallback trials.

These are candidate calibrations, not guarantees for particular request types.
"""

import copy

POLICY_REVISION = 'local-calibration-20261020'

METHOD_CONFIGS = {
    'atu_npo': {'lr': 5e-5, 'beta': .5, 'retain_weight': 1., 'epochs': 8},
    'rmu': {'lr': 1e-4, 'layer_idx': 14, 'alpha': 2., 'steering_coeff': 6.5,
            'preserve_reference': True, 'retain_ce_weight': 1., 'epochs': 8},
    'dpo_refusal': {'lr': 5e-5, 'beta': 2., 'gamma': .5, 'retain_weight': 1., 'epochs': 8},
    'graddiff': {'lr': 3e-5, 'alpha': 2., 'retain_weight': 2., 'epochs': 8},
    'ga': {'lr': 3e-5, 'epochs': 8},
}

# Final order is recorded with the local development evidence before held-out
# testing. Priority hints may choose a different first candidate; evaluation is
# still required and no method implies privacy by itself.
CALIBRATED_ORDER = ['dpo_refusal', 'atu_npo', 'ga', 'graddiff', 'rmu']


def method_config(method, request):
    config = copy.deepcopy(METHOD_CONFIGS[method])
    config['policy_revision'] = POLICY_REVISION
    config['epochs'] = min(config['epochs'], request.max_epochs_per_trial)
    config['retain_weight'] = max(config.get('retain_weight', 1.), request.retain_weight)
    if method in ('graddiff', 'rmu'):
        config['alpha'] = max(config.get('alpha', 1.), config['retain_weight'])
    if method == 'atu_npo':
        config.update(base_floor_mean=request.base_floor_mean, base_floor_std=request.base_floor_std,
                      floor_buffer=request.floor_buffer, retain_max_drop=request.retain_max_drop,
                      leak_boost=1.8, stubborn_threshold=-1.8, suppressed_weight=0., standard_weight=1.)
    return config
