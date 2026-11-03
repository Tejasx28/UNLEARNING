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
from typing import Dict, Any, List
from datetime import datetime
from src.atu.v3.types import (
    UnlearningRequest,
    TrialAttempt,
    EvidenceReport,
)

logger = logging.getLogger(__name__)


class EvidenceReporter:
    """
    Generates structured JSON and Markdown audit reports for ATU v3.
    """

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
        forgotten_evidence = {
            "total_targets_requested": len(request.forget_data),
            "suppressed_targets_count": best_m.details.get("suppressed_samples", 0),
            "suppression_percentage": round(best_m.forget_suppressed_ratio * 100, 2),
            "final_avg_log_prob": best_m.forget_avg_log_prob,
            "calibrated_base_floor": round(request.floor_threshold, 4),
            "distance_to_floor": best_m.forget_floor_distance,
            "likelihood_reference": best_m.details.get('likelihood_reference', 'legacy_global_floor'),
            "likelihood_eligible_samples": best_m.details.get('likelihood_eligible_samples', len(request.forget_data)),
            "verdict": "SUCCESSFULLY_SUPPRESSED" if best_m.forget_suppressed_ratio >= 0.80 else "PARTIALLY_SUPPRESSED",
        }

        # 2. Evidence: What remains recoverable
        recoverable_evidence = {
            "probe_leak_rate_percentage": round(best_m.probe_leak_rate * 100, 2),
            "active_dev_probes_tested": len(request.dev_probes) if request.dev_probes else 0,
            "unlearning_resistance": "LOW_LEAKAGE" if best_m.probe_leak_rate <= request.max_probe_leak_rate else "ELEVATED_LEAKAGE",
            "stubborn_targets_count": max(0, len(request.forget_data) - best_m.details.get("suppressed_samples", 0)),
        }

        # 3. Evidence: Affected capabilities
        affected_capabilities = {
            "retain_log_prob_drop": best_m.retain_log_prob_drop,
            "retain_max_allowed_drop": request.retain_max_drop,
            "retain_utility_intact": best_m.retain_preserved,
            "max_individual_retain_drop": best_m.details.get('max_individual_retain_drop'),
            "retain_probe_check": best_m.details.get('retain_probe_check'),
            "answer_fluency_score": best_m.fluency_score,
            "token_repetition_rate": best_m.repetition_rate,
            "catastrophic_collapse_detected": not best_m.is_safe and best_m.verdict.value == "MODEL_COLLAPSED",
            "overall_capability_status": "PASSED_CONFIGURED_CHECKS" if best_m.retain_preserved and best_m.fluency_score >= request.min_fluency_score else "DEGRADED",
            "measurement_scope": "retain validation likelihood and two short generation quality checks; not broad capability preservation",
        }

        from src.atu.v3.types import VerificationVerdict
        measured = final_test_metrics or best_m
        passed = (measured.is_safe and measured.verdict == VerificationVerdict.CONVERGED_SAFE
                  and measured.probe_leak_rate <= request.max_probe_leak_rate
                  and measured.fluency_score >= request.min_fluency_score
                  and not best_trial.status.startswith('FAILED'))
        overall_status = 'SUCCESS' if passed else ('PARTIAL_SUCCESS' if measured.is_safe else 'FAILED')
        if final_test_required and final_test_metrics is None:
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
        content = f"""# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `{report.request_id}`  
**Timestamp:** `{report.timestamp}`  
**Overall Verdict:** **{report.overall_status}**  
**Selected Best Checkpoint:** `{report.best_checkpoint_path}` (Trial #{report.best_trial_index})  
**Total Compute Duration:** `{report.total_duration_sec}s` across `{report.total_trials}` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `{report.evidence_what_was_forgotten['suppression_percentage']}%` ({report.evidence_what_was_forgotten['suppressed_targets_count']}/{report.evidence_what_was_forgotten['total_targets_requested']} targets)
- **Final Avg Log-Probability:** `{report.evidence_what_was_forgotten['final_avg_log_prob']}`
- **Calibrated Base Model Floor:** `{report.evidence_what_was_forgotten['calibrated_base_floor']}`
- **Distance to Floor:** `{report.evidence_what_was_forgotten['distance_to_floor']}`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `{report.evidence_what_remains_recoverable['probe_leak_rate_percentage']}%`
- **Active Probes Tested:** `{report.evidence_what_remains_recoverable['active_dev_probes_tested']}`
- **Stubborn Targets Remaining:** `{report.evidence_what_remains_recoverable['stubborn_targets_count']}`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `{report.evidence_affected_capabilities['retain_log_prob_drop']}` (Limit: `<= {report.evidence_affected_capabilities['retain_max_allowed_drop']}`)
- **Retain Utility Preserved:** `{'YES' if report.evidence_affected_capabilities['retain_utility_intact'] else 'NO (VIOLATION)'}`
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
