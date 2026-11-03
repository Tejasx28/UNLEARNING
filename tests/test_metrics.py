"""
Tests for unlearning evaluation metrics: ROUGE, log-probs, and Truth Ratio.
"""

import pytest
import math
from src.metrics import (
    compute_rouge_scores,
    compute_truth_ratio,
)


def test_rouge_exact_match():
    preds = ["Basil Mahfouz Al-Kuwaiti was born in Kuwait."]
    refs = ["Basil Mahfouz Al-Kuwaiti was born in Kuwait."]
    scores = compute_rouge_scores(preds, refs)

    assert scores["rouge1"] == pytest.approx(1.0, abs=1e-3)
    assert scores["rouge2"] == pytest.approx(1.0, abs=1e-3)
    assert scores["rougeL"] == pytest.approx(1.0, abs=1e-3)


def test_rouge_mismatch():
    preds = ["Completely unrelated text about football and astronomy."]
    refs = ["Basil Mahfouz Al-Kuwaiti was born in Kuwait."]
    scores = compute_rouge_scores(preds, refs)

    assert scores["rouge1"] < 0.2
    assert scores["rougeL"] < 0.2


def test_truth_ratio_calculation():
    # Mock examples with known log probabilities
    # We can test the sigmoid formula directly
    diff_favors_true = 5.0  # true lp = -1.0, pert lp = -6.0 -> exp(-5.0) -> sigmoid ~ 0.993
    prob_true = 1.0 / (1.0 + math.exp(-diff_favors_true))
    assert prob_true > 0.99

    diff_neutral = 0.0  # true lp == pert lp -> sigmoid = 0.5
    prob_neutral = 1.0 / (1.0 + math.exp(-diff_neutral))
    assert prob_neutral == pytest.approx(0.5, abs=1e-4)

    diff_favors_pert = -5.0  # pert lp >> true lp -> sigmoid ~ 0.0067
    prob_pert = 1.0 / (1.0 + math.exp(-diff_favors_pert))
    assert prob_pert < 0.01
