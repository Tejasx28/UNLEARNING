"""
Evidence Reporter for ATU v3.
Produces structured, auditable evidence detailing:
1. What was forgotten (explicit target metrics vs base floor)
2. What remains recoverable (probe leak rates and stubborn targets)
3. Whether other capabilities were affected (retain degradation and fluency)
"""

import os
import json
import logging
import math
from typing import Dict, Any, List
from datetime import datetime
from src.atu.v3.types import (
    UnlearningRequest,
    TrialAttempt,
    EvidenceReport,
)
from src.atu.v3.data import retain_quality_scope

logger = logging.getLogger(__name__)


class EvidenceReporter:
    """
    Generates structured JSON and Markdown audit reports for ATU v3.
    """

    @staticmethod
    def _quality_requirement_passed(request, metrics):
        if request.retain_quality_max_drop is None:
            return True
        check = metrics.details.get('retain_quality_check')
        if not isinstance(check, dict) or check.get('enabled') is not True:
            return False
        before, after = check.get('before'), check.get('after')
        if (any(isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) for value in (before, after))
                or not 0 < before <= 1 or not 0 <= after <= 1):
            return False
        rows, fingerprint, token_cap = retain_quality_scope(request)
        return (check.get('metric') == 'mean_rougeL_against_reference'
                and check.get('cohort_sha256') == fingerprint
                and check.get('sample_count') == len(rows) and check.get('token_cap') == token_cap
                and check.get('passed') is True
                and max(0.0, (before-after)/before) <= request.retain_quality_max_drop + 1e-12)

    @staticmethod
    def compile_report(
        request: UnlearningRequest,
        trials: List[TrialAttempt],
        best_trial: TrialAttempt,
        total_duration_sec: float,
        output_dir: str,
        final_test_metrics=None,
        final_test_required=False,
    ) -> EvidenceReport:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().isoformat()
        req_id = f"atu_v3_{request.target_author or 'custom'}_{int(datetime.now().timestamp())}"

        # 1. Evidence: What was forgotten
        best_m = best_trial.metrics
        selected_quality_passed = EvidenceReporter._quality_requirement_passed(request, best_m)
        measured = final_test_metrics or best_m
        measured_quality_passed = EvidenceReporter._quality_requirement_passed(request, measured)
        quality_preserved = selected_quality_passed and measured_quality_passed
        forgotten_evidence = {
            "total_targets_requested": len(request.forget_data),
            "suppressed_targets_count": best_m.details.get("suppressed_samples", 0),
            "suppression_percentage": round(best_m.forget_suppressed_ratio * 100, 2),
            "required_suppression_percentage": round(request.required_forget_suppression_ratio * 100, 2),
            "final_avg_log_prob": best_m.forget_avg_log_prob,
            "calibrated_base_floor": (None if best_m.details.get('likelihood_reference') == 'per_answer_untuned_base'
                                      else round(request.floor_threshold, 4)),
            "legacy_global_floor": round(request.floor_threshold, 4),
            "distance_to_floor": best_m.forget_floor_distance,
            "likelihood_reference": best_m.details.get('likelihood_reference', 'legacy_global_floor'),
            "likelihood_eligible_samples": best_m.details.get('likelihood_eligible_samples', len(request.forget_data)),
            "verdict": ("SUCCESSFULLY_SUPPRESSED" if best_m.forget_suppressed_ratio >= request.required_forget_suppression_ratio
                        else "PARTIALLY_SUPPRESSED"),
        }

        # 2. Evidence: What remains recoverable
        recoverable_evidence = {
            "probe_leak_rate_percentage": round(best_m.probe_leak_rate * 100, 2),
            "active_dev_probes_tested": len(request.dev_probes) if request.dev_probes else 0,
            "unlearning_resistance": "LOW_LEAKAGE" if best_m.probe_leak_rate <= request.max_probe_leak_rate else "ELEVATED_LEAKAGE",
            "stubborn_targets_count": max(0, best_m.details.get('likelihood_eligible_samples', len(request.forget_data))
                                            - best_m.details.get("suppressed_samples", 0)),
        }

        # 3. Evidence: Affected capabilities
        affected_capabilities = {
            "retain_log_prob_drop": best_m.retain_log_prob_drop,
            "retain_max_allowed_drop": request.retain_max_drop,
            "retain_utility_intact": best_m.retain_preserved and measured.retain_preserved and quality_preserved,
            "max_individual_retain_drop": best_m.details.get('max_individual_retain_drop'),
            "retain_probe_check": best_m.details.get('retain_probe_check'),
            "retain_quality_check": best_m.details.get('retain_quality_check'),
            "retain_quality_max_relative_drop": request.retain_quality_max_drop,
            "final_retain_quality_check": (final_test_metrics.details.get('retain_quality_check')
                                            if final_test_metrics else None),
            "answer_fluency_score": best_m.fluency_score,
            "token_repetition_rate": best_m.repetition_rate,
            "catastrophic_collapse_detected": not best_m.is_safe and best_m.verdict.value == "MODEL_COLLAPSED",
            "overall_capability_status": "PASSED_CONFIGURED_CHECKS" if best_m.retain_preserved and measured.retain_preserved and quality_preserved and best_m.fluency_score >= request.min_fluency_score else "DEGRADED",
            "measurement_scope": "retain validation likelihood, optional original-controlled retain fact probes, optional fixed-cohort relative ROUGE-L quality decline and two short fluency checks; not broad capability preservation",
        }

        from src.atu.v3.types import VerificationVerdict
        measured_safe = measured.is_safe and quality_preserved
        passed = (measured_safe and measured.verdict == VerificationVerdict.CONVERGED_SAFE
                  and measured.forget_suppressed_ratio >= request.required_forget_suppression_ratio
                  and measured.probe_leak_rate <= request.max_probe_leak_rate
                  and measured.fluency_score >= request.min_fluency_score
                  and not best_trial.status.startswith('FAILED'))
        overall_status = 'SUCCESS' if passed else ('PARTIAL_SUCCESS' if measured_safe else 'FAILED')
        updates = [trial.metrics.details.get('optimizer_steps') for trial in trials]
        if updates and all(isinstance(steps, int) for steps in updates) and sum(updates) == 0:
            overall_status = 'NO_OPTIMIZER_UPDATES'
        if final_test_required and final_test_metrics is None and overall_status != 'NO_OPTIMIZER_UPDATES':
            overall_status = 'UNVERIFIED'
        recoverable_evidence['evaluation_scope'] = 'independent_final_test' if final_test_metrics else 'development_only'
        recoverable_evidence['final_test_metrics'] = final_test_metrics.to_dict() if final_test_metrics else None
        recoverable_evidence['active_dev_probes_tested'] = best_m.details.get('development_probes_tested', 0)

        report = EvidenceReport(
            request_id=req_id,
            timestamp=timestamp,
            total_trials=len(trials),
            total_duration_sec=round(total_duration_sec, 2),
            best_trial_index=best_trial.trial_index,
            best_checkpoint_path=best_trial.checkpoint_dir,
            overall_status=overall_status,
            evidence_what_was_forgotten=forgotten_evidence,
            evidence_what_remains_recoverable=recoverable_evidence,
            evidence_affected_capabilities=affected_capabilities,
            all_trials=[t.to_dict() for t in trials],
        )

        # Save JSON
        json_path = os.path.join(output_dir, "atu_v3_evidence_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        # Save Markdown Summary
        md_path = os.path.join(output_dir, "atu_v3_evidence_report.md")
        EvidenceReporter._write_markdown_summary(report, md_path)

        logger.info(f"[ATU v3 Reporter] Saved Evidence Report to {json_path} and {md_path}")
        return report

    @staticmethod
    def _write_markdown_summary(report: EvidenceReport, md_path: str):
        quality = report.evidence_affected_capabilities.get('retain_quality_check')
        if quality and quality.get('enabled'):
            quality_description = (f"Original mean ROUGE-L `{quality.get('before')}`; selected `{quality.get('after')}`; "
                f"relative decline `{quality.get('relative_drop')}` (limit `{quality.get('limit')}`); "
                f"`{quality.get('sample_count')}` fixed answers, `{quality.get('token_cap')}` token cap; "
                f"passed `{quality.get('passed')}`. This is a sampled answer-overlap metric, not all knowledge.")
        else:
            quality_description = 'Not configured; no percentage-based retain answer-quality claim is made.'
        content = f"""# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `{report.request_id}`  
**Timestamp:** `{report.timestamp}`  
**Overall Verdict:** **{report.overall_status}**  
**Selected Best Checkpoint:** `{report.best_checkpoint_path}` (Trial #{report.best_trial_index})  
**Total Compute Duration:** `{report.total_duration_sec}s` across `{report.total_trials}` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `{report.evidence_what_was_forgotten['suppression_percentage']}%` ({report.evidence_what_was_forgotten['suppressed_targets_count']}/{report.evidence_what_was_forgotten['likelihood_eligible_samples']} eligible targets; {report.evidence_what_was_forgotten['total_targets_requested']} requested)
- **Requested Suppression Target:** `{report.evidence_what_was_forgotten['required_suppression_percentage']}%` of eligible targets
- **Final Avg Log-Probability:** `{report.evidence_what_was_forgotten['final_avg_log_prob']}`
- **Likelihood Reference:** `{report.evidence_what_was_forgotten['likelihood_reference']}`
- **Legacy Global Floor (reference only):** `{report.evidence_what_was_forgotten['legacy_global_floor']}`
- **Distance to Floor:** `{report.evidence_what_was_forgotten['distance_to_floor']}`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `{report.evidence_what_remains_recoverable['probe_leak_rate_percentage']}%`
- **Active Probes Tested:** `{report.evidence_what_remains_recoverable['active_dev_probes_tested']}`
- **Stubborn Targets Remaining:** `{report.evidence_what_remains_recoverable['stubborn_targets_count']}`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `{report.evidence_affected_capabilities['retain_log_prob_drop']}` (Limit: `<= {report.evidence_affected_capabilities['retain_max_allowed_drop']}`)
- **Retain Utility Preserved:** `{'YES' if report.evidence_affected_capabilities['retain_utility_intact'] else 'NO (VIOLATION)'}`
- **Retain Answer Quality:** {quality_description}
- **Fluency & Coherence Score:** `{report.evidence_affected_capabilities['answer_fluency_score'] * 100:.1f}%`
- **Capability Status:** `{report.evidence_affected_capabilities['overall_capability_status']}`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
        for t in report.all_trials:
            m = t["metrics"]
            is_winner = " ⭐ (Winner)" if t["trial_index"] == report.best_trial_index else ""
            content += (
                f"| #{t['trial_index']}{is_winner} | `{t['method']}` | {m['forget_suppressed_ratio']*100:.1f}% | "
                f"{m['retain_log_prob_drop']:.4f} | {m['fluency_score']*100:.1f}% | "
                f"{'YES' if m['is_safe'] else 'NO'} | **{m['composite_score']:.4f}** |\n"
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
