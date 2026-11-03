"""Target fine-tuning accounting, tested with a scalar CPU model only."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch
import yaml
import src.train_target as target


class ScalarModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.))

    def forward(self, input_ids, **kwargs):
        return SimpleNamespace(loss=self.weight * input_ids.float().mean())


def target_run(tmp_path, monkeypatch, count=3, accumulation=2, max_steps=None):
    config = tmp_path / 'config.yaml'
    config.write_text(yaml.safe_dump({'batch_size': 1, 'grad_accum_steps': accumulation,
        'epochs': 1, 'max_grad_norm': 0, 'seed': 17}), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(target.torch.cuda, 'is_available', lambda: False)
    seeds = [Mock(), Mock(), Mock()]
    monkeypatch.setattr(target.random, 'seed', seeds[0])
    monkeypatch.setattr(target.np.random, 'seed', seeds[1])
    monkeypatch.setattr(target.torch, 'manual_seed', seeds[2])
    model = ScalarModel()
    monkeypatch.setattr(target, 'load_tokenizer', lambda *a: None)
    monkeypatch.setattr(target, 'load_base_model', lambda *a, **kw: model)
    monkeypatch.setattr(target, 'setup_lora_model', lambda *a, **kw: model)
    monkeypatch.setattr(target, 'load_tofu_raw', lambda *a: [])
    monkeypatch.setattr(target, 'TOFUDataset', lambda *a, **kw: [None] * count)
    batches = [dict(input_ids=torch.ones(1, 1), attention_mask=torch.ones(1, 1),
                    labels=torch.ones(1, 1)) for _ in range(count)]
    monkeypatch.setattr(target, 'create_dataloader', lambda *a, **kw: batches)
    gradients = []

    class RecordingOptimizer:
        def __init__(self, parameters, **kwargs):
            self.parameters = list(parameters)

        def step(self):
            gradients.append(self.parameters[0].grad.item())

        def zero_grad(self):
            for parameter in self.parameters:
                parameter.grad = None

    monkeypatch.setattr(target.torch.optim, 'AdamW', RecordingOptimizer)
    scheduler = Mock()
    factory = Mock(return_value=scheduler)
    monkeypatch.setattr(target, 'get_cosine_schedule_with_warmup', factory)
    save = Mock()
    monkeypatch.setattr(target, 'save_checkpoint', save)
    monkeypatch.setattr(target, 'CommonEvaluator', lambda **kw: SimpleNamespace(evaluate_model=lambda *a, **k: {}))
    monkeypatch.setattr(target, 'print_evaluation_summary', lambda *a, **kw: None)
    target.train_target(str(config), max_steps_override=max_steps)
    return gradients, factory, scheduler, save, seeds


def test_partial_final_group_gets_full_mean_gradient_and_scheduler_step(tmp_path, monkeypatch):
    gradients, factory, scheduler, save, _ = target_run(tmp_path, monkeypatch)
    assert gradients == pytest.approx([1., 1.])
    assert factory.call_args.args[2] == 2
    assert scheduler.step.call_count == 2
    assert save.call_args.kwargs['metadata']['global_steps'] == 2


def test_group_larger_than_dataset_still_has_one_complete_mean_update(tmp_path, monkeypatch):
    gradients, factory, scheduler, _, _ = target_run(tmp_path, monkeypatch, count=1, accumulation=4)
    assert gradients == pytest.approx([1.])
    assert factory.call_args.args[2] == scheduler.step.call_count == 1


def test_target_training_applies_configured_seed_to_all_random_sources(tmp_path, monkeypatch):
    *_, save, seeds = target_run(tmp_path, monkeypatch)
    for seed in seeds:
        seed.assert_called_once_with(17)
    assert save.call_args.kwargs['metadata']['seed'] == 17


def test_max_steps_limits_actual_and_scheduled_updates(tmp_path, monkeypatch):
    gradients, factory, scheduler, _, _ = target_run(tmp_path, monkeypatch, count=3, max_steps=1)
    assert gradients == pytest.approx([1.])
    assert factory.call_args.args[2] == scheduler.step.call_count == 1


@pytest.mark.parametrize('max_steps', [0, -1, True])
def test_invalid_max_steps_fails_before_model_loading(tmp_path, monkeypatch, max_steps):
    with pytest.raises(ValueError, match='positive integer'):
        target_run(tmp_path, monkeypatch, max_steps=max_steps)
