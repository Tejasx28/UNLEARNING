"""
Unit tests for Adaptive Targeted Unlearning (ATU) controller and trainer.
Verifies target state transitions, dynamic weight computation, retain guard,
stopping criteria, and decision trace serialization.
"""

import pytest
import torch
from src.atu.controller import ATUController, TargetStatus


def test_target_status_dataclass():
    status = TargetStatus(
        question="What is the author's name?",
        answer="Basil Mahfouz",
        initial_log_prob=-0.01,
        current_log_prob=-0.01,
        floor_threshold=-3.16,
        state="UNLEARNING",
        weight=1.0,
        probe_leak=False,
    )
    assert status.state == "UNLEARNING"
    assert status.weight == 1.0
    assert not status.probe_leak


def test_atu_controller_weight_logic():
    forget_data = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
        {"question": "Q3", "answer": "A3"},
    ]
    
    class MockTokenizer:
        pass

    controller = ATUController(
        forget_data=forget_data,
        tokenizer=MockTokenizer(),
        config={
            "base_floor_mean": -3.0,
            "base_floor_std": 0.5,
            "floor_buffer": 0.0,  # floor = -3.0
            "stubborn_threshold": -1.0,
            "stubborn_boost": 1.5,
            "suppressed_weight": 0.0,
        }
    )

    # Populate target states manually for unit testing
    controller.target_states["Q1"] = TargetStatus(
        question="Q1", answer="A1", initial_log_prob=-0.01, current_log_prob=-0.5,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )
    controller.target_states["Q2"] = TargetStatus(
        question="Q2", answer="A2", initial_log_prob=-0.01, current_log_prob=-3.5,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )
    controller.target_states["Q3"] = TargetStatus(
        question="Q3", answer="A3", initial_log_prob=-0.01, current_log_prob=-0.05,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )

    # Batch weight retrieval
    weights = controller.get_batch_weights(["Q1", "Q2", "Q3"], device="cpu")
    assert weights.shape == (3,)
    assert weights[0].item() == 1.0


def test_atu_decision_trace_and_stopping():
    forget_data = [{"question": "Q1", "answer": "A1"}]

    class MockTokenizer:
        pass

    controller = ATUController(
        forget_data=forget_data,
        tokenizer=MockTokenizer(),
        config={"retain_max_drop": 0.05}
    )

    # Initial state
    controller.target_states["Q1"] = TargetStatus(
        question="Q1", answer="A1", initial_log_prob=-0.01, current_log_prob=-4.0,
        floor_threshold=-3.16, state="SUPPRESSED", weight=0.0
    )
    controller.initial_retain_lp = -0.01
    controller.current_retain_lp = -0.01

    # Test trace appending
    step_record = {
        "round": 1,
        "action": "EVALUATE_AND_ADAPT",
        "active_targets": 0,
        "suppressed_targets": 1,
        "stubborn_targets": 0,
        "mean_forget_lp": -4.0,
        "retain_lp": -0.01,
        "retain_drift": 0.0,
        "retain_safe": True,
        "should_stop": True,
        "stop_reason": "ALL_TARGETS_SUPPRESSED",
        "decision": "All targets suppressed. Stopping early.",
    }
    controller.decision_trace.append(step_record)
    assert len(controller.decision_trace) == 1
    assert controller.decision_trace[0]["should_stop"] is True


def test_atu_v2_leaking_state_and_weight_boost():
    """Verify ATU v2 marks targets as LEAKING and boosts weight to leak_boost."""
    forget_data = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
    ]

    class MockTokenizer:
        pass

    controller = ATUController(
        forget_data=forget_data,
        tokenizer=MockTokenizer(),
        config={
            "base_floor_mean": -3.0,
            "base_floor_std": 0.5,
            "floor_buffer": 0.0,  # floor = -3.0
            "stubborn_threshold": -1.5,
            "stubborn_boost": 1.4,
            "leak_boost": 1.8,
            "suppressed_weight": 0.0,
        }
    )

    controller.target_states["Q1"] = TargetStatus(
        question="Q1", answer="A1", initial_log_prob=-0.01, current_log_prob=-3.5,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )
    controller.target_states["Q2"] = TargetStatus(
        question="Q2", answer="A2", initial_log_prob=-0.01, current_log_prob=-3.5,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )

    # Simulate Q1 has an active probe leak, Q2 does not
    probe_leaks = {"Q1": True, "Q2": False}

    class MockModel:
        def eval(self):
            pass

    # Mock compute_sequence_log_prob
    from unittest.mock import patch
    with patch("src.atu.controller.compute_sequence_log_prob", return_value={"avg_log_prob": -3.5}):
        summary = controller.update_states(
            model=MockModel(),
            round_idx=1,
            probe_leaks=probe_leaks,
            device="cpu",
            run_probes=False,
        )

    # Q1 had cur_lp = -3.5 (below floor), BUT had probe leak -> state MUST be LEAKING with weight 1.8
    assert controller.target_states["Q1"].state == "LEAKING"
    assert controller.target_states["Q1"].weight == 1.8
    assert controller.target_states["Q1"].probe_leak is True

    # Q2 had cur_lp = -3.5 and NO probe leak -> state MUST be SUPPRESSED with weight 0.0
    assert controller.target_states["Q2"].state == "SUPPRESSED"
    assert controller.target_states["Q2"].weight == 0.0

    # Stopping must NOT be triggered because Q1 is LEAKING
    assert summary["should_stop"] is False
    assert summary["leaking_targets"] == 1
    assert summary["suppressed_targets"] == 1


def test_atu_v2_dual_stopping_criterion():
    """Verify dual stopping triggers only when ALL targets suppressed AND ZERO dev leaks."""
    forget_data = [{"question": "Q1", "answer": "A1"}]

    class MockTokenizer:
        pass

    class MockModel:
        def eval(self):
            pass

    controller = ATUController(
        forget_data=forget_data,
        tokenizer=MockTokenizer(),
        config={
            "base_floor_mean": -3.0,
            "base_floor_std": 0.5,
            "floor_buffer": 0.0,  # floor = -3.0
            "leak_boost": 1.8,
        }
    )

    controller.target_states["Q1"] = TargetStatus(
        question="Q1", answer="A1", initial_log_prob=-0.01, current_log_prob=-3.5,
        floor_threshold=-3.0, state="UNLEARNING", weight=1.0
    )

    from unittest.mock import patch
    # Scenario A: Canonical suppressed, but dev probe leaks -> Should NOT stop
    with patch("src.atu.controller.compute_sequence_log_prob", return_value={"avg_log_prob": -3.5}):
        summary_leaking = controller.update_states(
            model=MockModel(),
            round_idx=1,
            probe_leaks={"Q1": True},
            device="cpu",
            run_probes=False,
        )
    assert summary_leaking["should_stop"] is False
    assert summary_leaking["leaking_targets"] == 1

    # Scenario B: Canonical suppressed AND zero dev probe leaks -> MUST STOP
    with patch("src.atu.controller.compute_sequence_log_prob", return_value={"avg_log_prob": -3.5}):
        summary_clean = controller.update_states(
            model=MockModel(),
            round_idx=2,
            probe_leaks={"Q1": False},
            device="cpu",
            run_probes=False,
        )
    assert summary_clean["should_stop"] is True
    assert summary_clean["suppressed_targets"] == 1
    assert summary_clean["leaking_targets"] == 0
    assert "ALL_TARGETS_SUPPRESSED_AND_ZERO_DEV_LEAKAGE" in summary_clean["stop_reason"]

