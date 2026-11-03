"""
Unit tests for ATU v3 components:
1. Request Analyzer
2. Multi-Faceted Verification Evaluator
3. Pareto Checkpoint Selector
4. Evidence Reporter
5. Strategy Adaptation Logic
6. Task Vector Unlearning Logic
"""

import os
import json
import pytest
import torch
import torch.nn as nn
from src.atu.v3.types import (
    UnlearningRequest,
    UnlearningPriority,
    VerificationVerdict,
    VerificationMetrics,
    TrialAttempt,
)
from src.atu.v3.analyzer import RequestAnalyzer
from src.atu.v3.selector import ParetoCheckpointSelector
from src.atu.v3.reporter import EvidenceReporter
from src.atu.v3.budget_engine import BudgetEngine
from src.methods.task_vector import TaskVectorTrainer


def test_request_analyzer_priorities():
    forget_data = [{"question": "Q1", "answer": "A1"}]

    # 1. Fast priority
    fast_req = UnlearningRequest(forget_data=forget_data, priority=UnlearningPriority.FAST)
    plan_fast = RequestAnalyzer.analyze(fast_req)
    assert plan_fast.recommended_method == "atu_npo"

    # 2. Strict Privacy priority
    strict_req = UnlearningRequest(forget_data=forget_data, priority=UnlearningPriority.STRICT_PRIVACY)
    plan_strict = RequestAnalyzer.analyze(strict_req)
    assert plan_strict.recommended_method == "atu_npo"

    # 3. Preserve Utility priority
    utility_req = UnlearningRequest(forget_data=forget_data, priority=UnlearningPriority.PRESERVE_UTILITY)
    plan_utility = RequestAnalyzer.analyze(utility_req)
    assert plan_utility.recommended_method == "dpo_refusal"

    # 4. Balanced priority
    balanced_req = UnlearningRequest(forget_data=forget_data, priority=UnlearningPriority.BALANCED)
    plan_balanced = RequestAnalyzer.analyze(balanced_req)
    assert plan_balanced.recommended_method == "dpo_refusal"


def test_pareto_checkpoint_selector_safe():
    # Construct 3 trial attempts: Trial 1 safe with medium score, Trial 2 unsafe (retain degraded), Trial 3 safe with high score
    t1_m = VerificationMetrics(
        forget_avg_log_prob=-3.2,
        forget_floor_distance=-0.04,
        forget_suppressed_ratio=0.85,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.52,
        retain_log_prob_drop=0.02,
        retain_preserved=True,
        fluency_score=0.9,
        repetition_rate=0.05,
        probe_leak_rate=0.08,
        verdict=VerificationVerdict.CONVERGED_SAFE,
        is_safe=True,
        composite_score=0.78,
    )
    t1 = TrialAttempt(trial_index=1, method="atu_npo", config={}, checkpoint_dir="/fake/1", metrics=t1_m, duration_seconds=10.0, status="COMPLETED")

    t2_m = VerificationMetrics(
        forget_avg_log_prob=-4.5,
        forget_floor_distance=-1.34,
        forget_suppressed_ratio=1.0,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.75,
        retain_log_prob_drop=0.25,
        retain_preserved=False,
        fluency_score=0.5,
        repetition_rate=0.3,
        probe_leak_rate=0.0,
        verdict=VerificationVerdict.RETAIN_DEGRADED,
        is_safe=False,
        composite_score=0.0,
    )
    t2 = TrialAttempt(trial_index=2, method="ga", config={}, checkpoint_dir="/fake/2", metrics=t2_m, duration_seconds=8.0, status="COMPLETED")

    t3_m = VerificationMetrics(
        forget_avg_log_prob=-3.3,
        forget_floor_distance=-0.14,
        forget_suppressed_ratio=0.95,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.51,
        retain_log_prob_drop=0.01,
        retain_preserved=True,
        fluency_score=0.95,
        repetition_rate=0.02,
        probe_leak_rate=0.04,
        verdict=VerificationVerdict.CONVERGED_SAFE,
        is_safe=True,
        composite_score=0.88,
    )
    t3 = TrialAttempt(trial_index=3, method="rmu", config={}, checkpoint_dir="/fake/3", metrics=t3_m, duration_seconds=12.0, status="COMPLETED")

    best, rationale = ParetoCheckpointSelector.select_best([t1, t2, t3])
    assert best.trial_index == 3
    assert best.method == "rmu"
    assert "Passed all safety guards" in rationale


def test_pareto_checkpoint_selector_fallback():
    # If all trials are degraded, pick least destructive
    t1_m = VerificationMetrics(
        forget_avg_log_prob=-4.0,
        forget_floor_distance=-0.84,
        forget_suppressed_ratio=1.0,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.65,
        retain_log_prob_drop=0.15,
        retain_preserved=False,
        fluency_score=0.8,
        repetition_rate=0.1,
        probe_leak_rate=0.0,
        verdict=VerificationVerdict.RETAIN_DEGRADED,
        is_safe=False,
        composite_score=0.0,
    )
    t1 = TrialAttempt(trial_index=1, method="ga", config={}, checkpoint_dir="/fake/1", metrics=t1_m, duration_seconds=10.0, status="COMPLETED")

    t2_m = VerificationMetrics(
        forget_avg_log_prob=-3.5,
        forget_floor_distance=-0.34,
        forget_suppressed_ratio=0.9,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.56,
        retain_log_prob_drop=0.06,  # less retain drop
        retain_preserved=False,
        fluency_score=0.9,
        repetition_rate=0.05,
        probe_leak_rate=0.05,
        verdict=VerificationVerdict.RETAIN_DEGRADED,
        is_safe=False,
        composite_score=0.0,
    )
    t2 = TrialAttempt(trial_index=2, method="graddiff", config={}, checkpoint_dir="/fake/2", metrics=t2_m, duration_seconds=10.0, status="COMPLETED")

    best, rationale = ParetoCheckpointSelector.select_best([t1, t2])
    assert best.trial_index == 2
    assert "Safety Fallback" in rationale


def test_evidence_reporter_output(tmp_path):
    out_dir = str(tmp_path / "report")
    req = UnlearningRequest(
        forget_data=[{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}],
        target_author="Tetsuya Nakamura",
    )

    m = VerificationMetrics(
        forget_avg_log_prob=-3.25,
        forget_floor_distance=-0.09,
        forget_suppressed_ratio=1.0,
        forget_rougeL=0.0,
        retain_avg_log_prob=-1.51,
        retain_log_prob_drop=0.01,
        retain_preserved=True,
        fluency_score=0.94,
        repetition_rate=0.03,
        probe_leak_rate=0.0,
        verdict=VerificationVerdict.CONVERGED_SAFE,
        is_safe=True,
        composite_score=0.86,
        details={"suppressed_samples": 2},
    )
    trial = TrialAttempt(trial_index=1, method="atu_npo", config={}, checkpoint_dir=out_dir, metrics=m, duration_seconds=15.0, status="COMPLETED")

    report = EvidenceReporter.compile_report(
        request=req,
        trials=[trial],
        best_trial=trial,
        total_duration_sec=15.0,
        output_dir=out_dir,
    )

    assert report.overall_status == "SUCCESS"
    assert report.evidence_what_was_forgotten["suppression_percentage"] == 100.0
    assert report.evidence_what_remains_recoverable["probe_leak_rate_percentage"] == 0.0
    assert report.evidence_affected_capabilities["retain_utility_intact"] is True

    # Check files exist
    assert os.path.exists(os.path.join(out_dir, "atu_v3_evidence_report.json"))
    assert os.path.exists(os.path.join(out_dir, "atu_v3_evidence_report.md"))


def test_adaptation_logic():
    # Instantiate BudgetEngine without loading heavy models to test _adapt_strategy
    class DummyTokenizer:
        pass

    engine = BudgetEngine.__new__(BudgetEngine)
    engine.request = UnlearningRequest(forget_data=[])

    # 1. Test Retain Degradation on GA -> should switch to atu_npo with amplified retain
    m_deg = VerificationMetrics(
        forget_avg_log_prob=-4.0, forget_floor_distance=-0.8, forget_suppressed_ratio=1.0,
        forget_rougeL=0.0, retain_avg_log_prob=-1.8, retain_log_prob_drop=0.20,
        retain_preserved=False, fluency_score=0.5, repetition_rate=0.2, probe_leak_rate=0.0,
        verdict=VerificationVerdict.RETAIN_DEGRADED, is_safe=False, composite_score=0.0
    )
    next_m, next_cfg, notes = engine._adapt_strategy(
        failed_metrics=m_deg,
        current_method="ga",
        current_config={"lr": 1e-4},
        fallback_queue=["atu_npo", "rmu"],
    )
    assert next_m == "atu_npo"
    assert next_cfg["retain_weight"] >= 2.0
    assert "Retain degradation" in notes

    # 2. Test Insufficient Forgetting on TaskVector -> should escalate to atu_npo
    m_stub = VerificationMetrics(
        forget_avg_log_prob=-1.2, forget_floor_distance=1.9, forget_suppressed_ratio=0.1,
        forget_rougeL=0.5, retain_avg_log_prob=-1.5, retain_log_prob_drop=0.005,
        retain_preserved=True, fluency_score=0.95, repetition_rate=0.01, probe_leak_rate=0.6,
        verdict=VerificationVerdict.INSUFFICIENT_FORGETTING, is_safe=True, composite_score=0.3
    )
    next_m2, next_cfg2, notes2 = engine._adapt_strategy(
        failed_metrics=m_stub,
        current_method="task_vector",
        current_config={"scaling_factor": 0.3},
        fallback_queue=["atu_npo", "rmu"],
    )
    assert next_m2 == "atu_npo"
    assert "Escalated" in notes2


def test_task_vector_adapter_subtraction():
    # Test adapter dampening on a mock model with lora parameters
    class MockLoraModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.base_layer = nn.Linear(10, 10)
            self.lora_A = nn.Parameter(torch.ones(10, 4))
            self.lora_B = nn.Parameter(torch.ones(4, 10))

    class MockTokenizer:
        pass

    model = MockLoraModel()
    trainer = TaskVectorTrainer(
        model=model,
        tokenizer=MockTokenizer(),
        config={"mode": "adapter_dampen", "scaling_factor": 0.5},
        device="cpu",
    )

    initial_sum = float(model.lora_A.sum().item())
    res = trainer.apply_adapter_subtraction(factor=0.5)

    assert res["mode"] == "adapter_dampen"
    assert res["modified_tensors"] == 2
    # 1.0 - 0.5 = 0.5 multiplier
    assert pytest.approx(float(model.lora_A.sum().item()), 0.01) == initial_sum * 0.5
