"""ATU controller signals must affect optimization without inventing recovery evidence."""
from types import SimpleNamespace

import pytest
import torch

from src.atu.controller import ATUController, TargetStatus
from src.atu.trainer import ATUNPOTrainer


class LogProbModel(torch.nn.Module):
    def __init__(self, size):
        super().__init__()
        self.log_probs = torch.nn.Parameter(torch.zeros(size))


def npo_gradient(weights):
    model = LogProbModel(len(weights))
    controller = SimpleNamespace(get_batch_weights=lambda *args, **kwargs: torch.tensor(weights))
    trainer = ATUNPOTrainer(model, None,
        {'beta': 1., 'retain_weight': 0., 'weight_decay': 0.}, controller, device='cpu')
    trainer._compute_per_example_log_prob = lambda *args: model.log_probs
    batch = {'input_ids': torch.zeros(len(weights), 2, dtype=torch.long),
             'attention_mask': torch.ones(len(weights), 2),
             'labels': torch.zeros(len(weights), 2, dtype=torch.long),
             'questions': [f'Q{i}' for i in range(len(weights))]}
    trainer.train_step(batch)
    return model.log_probs.grad


def test_near_floor_attenuation_reduces_pressure_on_single_remaining_target():
    full = npo_gradient([1.])
    tapered = npo_gradient([.2])
    assert tapered.item() == pytest.approx(full.item() * .2)


def test_suppressed_items_do_not_renormalize_remaining_target_back_to_full_pressure():
    assert npo_gradient([.2, 0.]).tolist() == pytest.approx([.1, 0.])


def test_boosted_relative_prioritization_keeps_its_existing_scale():
    # Above-unit weights retain the original normalized weighting, avoiding
    # a global LR increase when all targets are stubborn/leaking.
    assert npo_gradient([1.8, 1.]).tolist() == pytest.approx([1.8 / 2.8, 1. / 2.8])


def test_unevaluated_probes_keep_targets_active_without_fabricating_leaks(monkeypatch):
    import src.atu.controller as module
    monkeypatch.setattr(module, 'compute_sequence_log_prob', lambda *args, **kwargs: {'avg_log_prob': -4.})
    controller = ATUController([{'question': 'Q', 'answer': 'A'}], None,
        {'dev_probes': [{'id': 'dev-1', 'prompt': 'Q', 'target_facts': ['A']}]})
    controller.target_states['Q'] = TargetStatus('Q', 'A', -.1, -.1, -3., 'UNLEARNING', 1.)
    summary = controller.update_states(SimpleNamespace(eval=lambda: None), 1, device='cpu')
    assert summary['should_stop'] is False
    assert summary['active_targets'] == 1
    assert summary['leaking_targets'] == 0
    assert summary['development_probe_state'] == 'PENDING'
    assert not controller.target_states['Q'].probe_leak
    assert controller.target_states['Q'].weight == .2
