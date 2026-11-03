"""Candidate planning from local calibration and explicit priority hints.

This is a heuristic router, not a learned classifier or a privacy guarantee.
"""

import logging
from src.atu.v3.types import UnlearningRequest, UnlearningPriority, StrategyPlan
from src.atu.v3.policy import CALIBRATED_ORDER, method_config

logger = logging.getLogger(__name__)


class RequestAnalyzer:
    @staticmethod
    def analyze(request: UnlearningRequest) -> StrategyPlan:
        logger.info('[ATU v3 Analyzer] %s forget examples; %s development probes; priority=%s',
                    len(request.forget_data), len(request.dev_probes or []), request.priority.value)
        order = list(CALIBRATED_ORDER)
        if request.priority == UnlearningPriority.FAST or request.max_time_sec < 90.:
            method = 'atu_npo'
            config = method_config(method, request)
            config.update(lr=1e-5, beta=.1, epochs=1)
            rationale = 'Tight budget: a short targeted NPO attempt. This fast profile has not been established by the balanced-policy comparison.'
        elif request.priority == UnlearningPriority.STRICT_PRIVACY:
            order = [m for m in order if m != 'dpo_refusal'] + ['dpo_refusal']
            method = order[0]
            config = method_config(method, request)
            rationale = 'Strict-privacy hint: first try a non-refusal optimization candidate from the local calibration. This priority rule is a heuristic; only independent recovery tests can support a suppression claim.'
        elif request.priority == UnlearningPriority.PRESERVE_UTILITY:
            method = 'dpo_refusal'
            config = method_config(method, request)
            rationale = 'Utility-priority hint: try calibrated refusal preference training with retain regularization. A refusal alone does not prove knowledge removal.'
        else:
            method = order[0]
            config = method_config(method, request)
            rationale = f'Balanced request: start with {method} from the two-author local development calibration, then judge generated fact recovery and utility. Alternatives use their own calibrated settings and restart from the original target.'
        return StrategyPlan(method, config, rationale, [m for m in order if m != method])
