"""
Pareto Checkpoint Selector for ATU v3.
Ranks all preserved trial checkpoints against safety constraints and selects
the optimal safe checkpoint that maximizes forget suppression without retain degradation.
"""

import logging
from typing import List, Optional, Tuple
from src.atu.v3.types import TrialAttempt, VerificationVerdict

logger = logging.getLogger(__name__)


class ParetoCheckpointSelector:
    """
    Selects the Pareto-optimal checkpoint from preserved trial attempts.
    """

    @staticmethod
    def select_best(trials: List[TrialAttempt]) -> Tuple[TrialAttempt, str]:
        if not trials:
            raise ValueError("No trial attempts provided for checkpoint selection.")

        # 1. Filter for trials strictly satisfying safety guards
        safe_trials = [t for t in trials if t.metrics.is_safe and not t.status.startswith("FAILED") and t.metrics.verdict != VerificationVerdict.MODEL_COLLAPSED]

        if safe_trials:
            # Sort safe trials by composite score descending, then forget log-prob ascending
            best = max(
                safe_trials,
                key=lambda t: (t.metrics.verdict == VerificationVerdict.CONVERGED_SAFE,
                               -t.metrics.probe_leak_rate, t.metrics.forget_suppressed_ratio,
                               t.metrics.composite_score),
            )
            rationale = (
                f"Selected Trial #{best.trial_index} ({best.method}): Passed all safety guards; ranked by convergence, development leakage, then suppression. Composite score "
                f"{best.metrics.composite_score:.4f}, forget suppression {best.metrics.forget_suppressed_ratio*100:.1f}%, "
                f"and retain drop {best.metrics.retain_log_prob_drop:.4f} (<= threshold)."
            )
            logger.info(f"[ATU v3 Selector] {rationale}")
            return best, rationale

        # 2. Safety Fallback: If no trial passed strict safety guards, choose least destructive
        logger.warning("[ATU v3 Selector] No trial satisfied strict safety bounds. Triggering safe fallback.")
        least_destructive = min(
            trials,
            key=lambda t: (t.metrics.retain_log_prob_drop, -t.metrics.fluency_score),
        )
        rationale = (
            f"Safety Fallback: No trial fully converged within retain safety bounds. Selected Trial "
            f"#{least_destructive.trial_index} ({least_destructive.method}) as it caused the least retain damage "
            f"(retain drop: {least_destructive.metrics.retain_log_prob_drop:.4f}, fluency: {least_destructive.metrics.fluency_score:.2f})."
        )
        logger.warning(f"[ATU v3 Selector] {rationale}")
        return least_destructive, rationale
