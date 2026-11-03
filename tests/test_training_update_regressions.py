"""CPU regressions for actual updates, preparation timing and guard revisions."""
from types import SimpleNamespace

import pytest
import torch

from src.methods.base import BaseUnlearningTrainer, TrainingStopped
from src.atu.trainer import ATUNPOTrainer
from src.atu.v3.safety import RetainGuard
from src.methods.npo import NPOTrainer
from src.methods.ga import GradientAscentTrainer
from src.methods.graddiff import GradDiffTrainer
from src.methods.rmu import RMUTrainer
from src.methods.dpo_refusal import DPORefusalTrainer
from src.data import TOFUDataset, create_dataloader


@pytest.fixture(autouse=True)
def cpu_only(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)


class ScalarModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.))


class ScalarStep:
    def train_step(self, batch, retain_batch=None):
        loss = (self.model.weight - batch['target']).square() / 2
        (loss / self.grad_accum_steps).backward()
        return {'loss': float(loss.detach())}


class ScalarTrainer(ScalarStep, BaseUnlearningTrainer):
    pass


class ScalarAdaptiveTrainer(ScalarStep, ATUNPOTrainer):
    pass


class Controller:
    initial_retain_lp = 0.
    current_retain_lp = 0.

    def __init__(self, clock=None):
        self.initializations = 0
        self.rounds = []
        self.clock = clock

    def initialize(self, **kwargs):
        self.initializations += 1
        if self.clock is not None:
            self.clock['now'] += 5

    def update_states(self, round_idx, **kwargs):
        self.rounds.append(round_idx)
        if self.clock is not None:
            self.clock['now'] += 5
        return {'should_stop': False, 'stop_reason': ''}

    def get_batch_weights(self, questions, device='cpu'):
        return torch.ones(len(questions), device=device)


def trainer(adaptive=False, **config):
    model = ScalarModel()
    settings = {'lr': .1, 'epochs': 1, 'grad_accum_steps': 4,
                'max_grad_norm': 0, 'weight_decay': 0, **config}
    if adaptive:
        instance = ScalarAdaptiveTrainer(model, None, settings, controller=Controller(), device='cpu')
    else:
        instance = ScalarTrainer(model, None, settings, device='cpu')
    # SGD makes correct partial-group scaling directly observable in the weight.
    instance.optimizer = torch.optim.SGD(model.parameters(), lr=.1)
    instance.optimizer.register_step_post_hook(instance._after_optimizer_step)
    return instance


@pytest.mark.parametrize('adaptive', [False, True])
def test_one_batch_below_accumulation_limit_still_updates_once(adaptive):
    updates = []
    instance = trainer(adaptive, _on_optimizer_step=lambda: updates.append(True))
    fit = instance.fit_adaptive if adaptive else instance.fit
    result = fit([{'target': 1.}])
    assert instance.model.weight.item() == pytest.approx(.1)
    assert result['optimizer_steps'] == 1 and result['total_steps'] == 1
    assert updates == [True]
    assert instance.config['_optimizer_revision'] == 1


@pytest.mark.parametrize('adaptive', [False, True])
def test_final_partial_group_uses_its_own_mean_gradient(adaptive):
    instance = trainer(adaptive, grad_accum_steps=2)
    fit = instance.fit_adaptive if adaptive else instance.fit
    result = fit([{'target': 1.}, {'target': 3.}, {'target': 5.}])
    # First mean gradient=-2 -> .2; final gradient=.2-5=-4.8 -> .68.
    assert instance.model.weight.item() == pytest.approx(.68)
    assert result['optimizer_steps'] == 2 and result['total_steps'] == 3


def test_adaptive_preparation_is_idempotent_and_first_state_is_not_remeasured(monkeypatch):
    import src.methods.base as base
    clock = {'now': 100.}
    monkeypatch.setattr(base.time, 'monotonic', lambda: clock['now'])
    instance = trainer(True)
    instance.controller = Controller(clock)
    instance.prepare_training()
    assert clock['now'] == 110.
    instance.prepare_training()
    assert clock['now'] == 110.
    # The budget begins after expensive preparation. A repeated init/state
    # measurement inside fit would advance the clock and stop before any update.
    instance.config['_deadline'] = clock['now'] + 1
    result = instance.fit_adaptive([{'target': 1.}])
    assert result['optimizer_steps'] == 1
    assert instance.controller.initializations == 1
    assert instance.controller.rounds == [1, 2]


class Evaluator:
    def __init__(self, limit=1.):
        self.initial_retain_lp = 0.
        self.initial_retain_log_probs = [0.]
        self.last_retain_log_probs = [0.]
        self.request = SimpleNamespace(retain_max_drop=limit, retain_per_example_max_drop=limit)
        self.calls = 0

    def measure_retain(self, model):
        self.calls += 1
        value = -abs(float(model.weight.detach()))
        self.last_retain_log_probs = [value]
        return value


def test_guard_reuses_only_successful_explicitly_tracked_weight_revision():
    model = ScalarModel()
    evaluator = Evaluator()
    guard = RetainGuard(model, evaluator)
    with torch.no_grad(): model.weight.fill_(.1)
    guard.notify_optimizer_step()
    guard(); guard()
    assert evaluator.calls == 1 and guard.duplicate_checks_skipped == 1
    with torch.no_grad(): model.weight.fill_(.2)
    guard.notify_optimizer_step()
    guard()
    assert evaluator.calls == 2
    guard.restore(original=True)
    guard()
    assert evaluator.calls == 3  # Restoring weights invalidates a cached check.


def test_untracked_arithmetic_is_always_checked_and_unsafe_update_still_rolls_back():
    model = ScalarModel()
    evaluator = Evaluator(limit=.2)
    guard = RetainGuard(model, evaluator)
    guard()
    with torch.no_grad(): model.weight.fill_(.5)
    with pytest.raises(TrainingStopped, match='RETAIN_UTILITY_RISK'):
        guard()
    assert evaluator.calls == 2 and model.weight.item() == 0
    assert guard.rejected_drop == pytest.approx(.5)


def test_optimizer_hook_checks_each_update_and_skips_only_duplicate_epoch_check():
    instance = trainer(grad_accum_steps=2, _guard_every_steps=1)
    evaluator = Evaluator()
    guard = RetainGuard(instance.model, evaluator)
    instance.config['_safety_guard'] = guard
    result = instance.fit([{'target': 1.}, {'target': 3.}, {'target': 5.}])
    assert result['optimizer_steps'] == 2
    assert guard.checks == evaluator.calls == 2
    assert guard.duplicate_checks_skipped == 1


def test_adaptive_explicit_step_limit_counts_updates_not_microbatches():
    instance = trainer(True, epochs=3, grad_accum_steps=4)
    result = instance.fit_adaptive([{'target': 1.}], max_steps=2)
    assert result['total_steps'] == result['optimizer_steps'] == 2
    assert result['stop_reason'] == 'MAX_STEPS_REACHED_2'


@pytest.mark.parametrize('adaptive', [False, True])
def test_actual_npo_objective_lowers_target_probability_with_partial_group(adaptive):
    class TokenModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.logits = torch.nn.Parameter(torch.zeros(7))
        def forward(self, input_ids, attention_mask=None):
            return SimpleNamespace(logits=self.logits.view(1, 1, -1).expand(*input_ids.shape, -1))
    model = TokenModel()
    config = {'lr': .01, 'epochs': 1, 'grad_accum_steps': 4, 'weight_decay': 0,
              'max_grad_norm': 0, 'beta': .5, 'retain_weight': 0}
    if adaptive:
        instance = ATUNPOTrainer(model, None, config, controller=Controller(), device='cpu')
    else:
        instance = NPOTrainer(model, None, config, device='cpu')
    instance.set_reference_cache({'Secret?': -float(torch.log(torch.tensor(7.)))})
    batch = {'input_ids': torch.tensor([[2, 3, 4]]), 'attention_mask': torch.ones(1, 3),
             'labels': torch.tensor([[-100, 3, 4]]), 'questions': ['Secret?']}
    before = torch.softmax(model.logits.detach(), -1)[[3, 4]].mean()
    fit = instance.fit_adaptive if adaptive else instance.fit
    result = fit([batch])
    after = torch.softmax(model.logits.detach(), -1)[[3, 4]].mean()
    assert result['optimizer_steps'] == 1 and after < before


class SmallTokenizer:
    pad_token_id = 0
    eos_token_id = 1

    def encode(self, text, add_special_tokens=False):
        return [2 + ord(character) % 46 for character in text]


class SmallCausalModel(torch.nn.Module):
    """Real differentiable token/hidden-state model, with no external downloads."""
    def __init__(self):
        super().__init__()
        self.config = SimpleNamespace(hidden_size=12)
        self.embedding = torch.nn.Embedding(48, 12)
        self.hidden = torch.nn.Linear(12, 12)
        self.output = torch.nn.Linear(12, 48)

    def forward(self, input_ids, attention_mask=None, labels=None, output_hidden_states=False):
        embedded = self.embedding(input_ids)
        hidden = torch.tanh(self.hidden(embedded))
        logits = self.output(hidden)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.cross_entropy(
                logits[:, :-1].reshape(-1, logits.shape[-1]), labels[:, 1:].reshape(-1), ignore_index=-100)
        return SimpleNamespace(logits=logits, loss=loss, hidden_states=(embedded, hidden))


@pytest.mark.parametrize('method,expected_metric', [
    (GradientAscentTrainer, 'forget_ce_loss'),
    (GradDiffTrainer, 'forget_ce'),
    (RMUTrainer, 'forget_loss'),
    (DPORefusalTrainer, 'pref_loss'),
])
def test_selectable_methods_make_real_finite_updates_on_partial_accumulation(method, expected_metric):
    torch.manual_seed(42)
    model = SmallCausalModel()
    tokenizer = SmallTokenizer()
    forget_loader = create_dataloader(TOFUDataset(
        [{'question': 'What is the private code?', 'answer': 'Saffron'}], tokenizer), tokenizer, batch_size=1)
    retain_loader = create_dataloader(TOFUDataset(
        [{'question': 'What is the unrelated code?', 'answer': 'Indigo'}], tokenizer), tokenizer, batch_size=1)
    original = {name: parameter.detach().clone() for name, parameter in model.named_parameters()}
    observed_changes = []
    def observe_update():
        observed_changes.append(sum(float((parameter.detach() - original[name]).square().sum())
                                    for name, parameter in model.named_parameters()))
    instance = method(model, tokenizer, {
        'lr': .001, 'epochs': 1, 'grad_accum_steps': 4, 'max_grad_norm': 1., 'weight_decay': 0,
        'retain_weight': .2, 'alpha': .2, 'layer_idx': 0, 'steering_coeff': 1.,
        'preserve_reference': True, 'retain_refusal_weight': .2,
        '_on_optimizer_step': observe_update,
    }, device='cpu')
    result = instance.fit(forget_loader, retain_loader)
    metrics = result['final_step_metrics']
    assert result['optimizer_steps'] == result['total_steps'] == 1
    assert len(observed_changes) == 1 and observed_changes[0] > 0
    assert expected_metric in metrics
    assert all(torch.isfinite(torch.tensor(value)) for value in metrics.values())
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
    assert all(parameter.grad is None for parameter in model.parameters())
    if method is RMUTrainer:
        assert set(instance.reference_hidden) == {'What is the unrelated code?'}
        assert all(not value.requires_grad for value in instance.reference_hidden.values())
