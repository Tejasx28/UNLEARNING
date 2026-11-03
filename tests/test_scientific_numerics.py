"""CPU regressions for low-precision likelihoods and missing answer labels."""
from types import SimpleNamespace
import math

import pytest
import torch

from src.data import TOFUDataset
from src.metrics import compute_sequence_log_prob
from src.atu.trainer import ATUNPOTrainer
from src.methods.npo import NPOTrainer
from src.methods.dpo_refusal import DPORefusalTrainer


class WordTokenizer:
    eos_token_id = None

    def encode(self, text, add_special_tokens=False):
        return [0 if token == 'gold' else 1 for token in text.split()]


class LowPrecisionModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([0., -6.], dtype=torch.bfloat16))

    def forward(self, input_ids, **kwargs):
        return SimpleNamespace(logits=self.weight.view(1, 1, -1).expand(*input_ids.shape, -1))


def test_bfloat16_evaluation_keeps_small_negative_log_probability():
    result = compute_sequence_log_prob(LowPrecisionModel(), WordTokenizer(), 'prompt', 'gold', device='cpu')
    expected = -math.log1p(math.exp(-6.))
    # A BF16 log-softmax rounds this genuinely nonzero likelihood to zero.
    assert result['avg_log_prob'] == pytest.approx(expected, abs=1e-7)
    assert result['total_log_prob'] == pytest.approx(expected, abs=1e-7)


@pytest.mark.parametrize('trainer_type, method', [
    (NPOTrainer, '_compute_sequence_log_prob'),
    (ATUNPOTrainer, '_compute_per_example_log_prob'),
    (DPORefusalTrainer, '_compute_seq_log_prob'),
])
def test_preference_likelihoods_preserve_bfloat16_probability_and_gradient(trainer_type, method):
    trainer = trainer_type.__new__(trainer_type)
    trainer.model = LowPrecisionModel()
    trainer.length_normalize = True
    ids = torch.tensor([[1, 0]])
    labels = torch.tensor([[-100, 0]])
    result = getattr(trainer, method)(ids, torch.ones_like(ids), labels)
    assert result.dtype == torch.float32
    assert result.item() == pytest.approx(-math.log1p(math.exp(-6.)), abs=1e-7)
    result.sum().backward()
    assert trainer.model.weight.grad[0].abs().item() > 0
    assert torch.isfinite(trainer.model.weight.grad).all()


def test_long_question_cannot_silently_remove_all_answer_supervision():
    with pytest.raises(ValueError, match='no answer tokens.*max_length=8'):
        TOFUDataset([{'question': 'word ' * 20, 'answer': 'gold'}], WordTokenizer(), max_length=8)


@pytest.mark.parametrize('limit', [0, 1, -1, True, 8.5])
def test_training_token_limit_must_allow_a_causal_target(limit):
    with pytest.raises(ValueError, match='at least two'):
        TOFUDataset([{'question': 'question', 'answer': 'gold'}], WordTokenizer(), max_length=limit)


def test_answer_truncation_retains_valid_supervision():
    item = TOFUDataset([{'question': 'question', 'answer': 'gold gold gold gold'}], WordTokenizer(), max_length=5)[0]
    assert len(item['input_ids']) == 5
    assert any(label != -100 for label in item['labels'][1:])
