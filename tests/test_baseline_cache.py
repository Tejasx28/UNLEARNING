"""Runtime optimizations must preserve controls and invalidate stale evidence."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from src.orchestrator.baseline_cache import (
    BaselineReportCache, baseline_identity, can_disable_to_base, measure_controls, resolve_base_source, cached_tofu_rows,
)
from src.redteam.types import AttackProbe, AttackCategory, RedTeamReport


def probe():
    return AttackProbe('p1', AttackCategory.PARAPHRASE, 'Who is Alice?', ['Alice'])


def report(probes):
    return RedTeamReport('test', 'hash', 'Alice', len(probes), {}, {}, {}, {}, {},
        [{'probe_id': p.probe_id, 'prompt': p.prompt, 'target_facts': p.target_facts,
          'response_text': 'Alice', 'verdict': 'FULL_RECOVERY'} for p in probes], 'original-measurement')


def test_exact_controls_survive_restart_but_unlearned_reports_are_never_reused(tmp_path):
    probes = [probe()]
    compute = Mock(return_value=report(probes))
    cold = BaselineReportCache(tmp_path, {'model_revision': 'immutable'})
    first, meta = cold.get_or_compute('target', probes, {'max_new_tokens': 96}, compute)
    assert not meta['cache_hit']
    warm = BaselineReportCache(tmp_path, {'model_revision': 'immutable'})
    second, meta = warm.get_or_compute('target', probes, {'max_new_tokens': 96}, compute)
    assert meta['cache_hit'] and compute.call_count == 1
    assert first.to_dict() == second.to_dict()
    assert meta['measured_at'] == 'original-measurement'
    with pytest.raises(ValueError, match='Only original'):
        warm.get_or_compute('unlearned', probes, {}, compute)


@pytest.mark.parametrize('change', ['prompt', 'facts', 'wrapper', 'generation', 'identity', 'control'])
def test_changed_inputs_force_fresh_measurement(tmp_path, change):
    probes = [probe()]
    identity, generation, control = {'revision': 'a', 'adapter': 'a'}, {'tokens': 96}, 'target'
    BaselineReportCache(tmp_path, identity).get_or_compute(control, probes, generation, lambda: report(probes))
    if change == 'prompt': probes[0].prompt += ' please'
    if change == 'facts': probes[0].target_facts = ['Bob']
    if change == 'wrapper': probes[0].forbidden_phrases = ['other']
    if change == 'generation': generation = {'tokens': 48}
    if change == 'identity': identity = dict(identity, revision='b')
    if change == 'control': control = 'base'
    compute = Mock(side_effect=lambda: report(probes))
    _, meta = BaselineReportCache(tmp_path, identity).get_or_compute(control, probes, generation, compute)
    assert compute.call_count == 1 and not meta['cache_hit']


def test_missing_identity_and_corrupt_cache_fail_open_to_real_inference(tmp_path):
    probes = [probe()]
    compute = Mock(side_effect=lambda: report(probes))
    disabled = BaselineReportCache(tmp_path, None)
    for _ in range(2):
        assert not disabled.get_or_compute('target', probes, {}, compute)[1]['cache_hit']
    assert not list(tmp_path.iterdir())
    cache = BaselineReportCache(tmp_path, {'revision': 'a'})
    cache.get_or_compute('target', probes, {}, compute)
    next(tmp_path.glob('*.json')).write_text('{corrupt', encoding='utf-8')
    assert not cache.get_or_compute('target', probes, {}, compute)[1]['cache_hit']
    assert compute.call_count == 4


def test_incomplete_control_is_not_written(tmp_path):
    bad = report([probe()]); bad.results.clear()
    with pytest.raises(ValueError, match='Incomplete'):
        BaselineReportCache(tmp_path, {}).get_or_compute('target', [probe()], {}, lambda: bad)
    assert not list(tmp_path.iterdir())


class OriginalLoRA:
    def __init__(self):
        self.peft_config = {'default': SimpleNamespace(peft_type='LORA', bias='none')}
        self.disabled = False

    def modules(self): return []

    @contextmanager
    def disable_adapter(self):
        self.disabled = True
        try: yield
        finally: self.disabled = False


def test_control_pair_loads_once_cold_and_zero_times_warm(tmp_path):
    model = OriginalLoRA()
    load_target, load_base = Mock(return_value=model), Mock()
    modes = []
    def attack(**kwargs):
        modes.append(kwargs['model'].disabled)
        return report(kwargs['probes'])
    redteam = SimpleNamespace(attack_model=attack)
    cache = BaselineReportCache(tmp_path, {'revision': 'a'})
    first = measure_controls(cache, redteam, None, [probe()], 'Alice', 'h', load_target, load_base, lambda: None, lambda _: None)
    assert modes == [False, True] and not model.disabled
    assert load_target.call_count == 1 and load_base.call_count == 0
    second = measure_controls(cache, redteam, None, [probe()], 'Alice', 'h', load_target, load_base, lambda: None, lambda _: None)
    assert load_target.call_count == 1 and modes == [False, True]
    assert first[0].to_dict() == second[0].to_dict()
    assert all(value['cache_hit'] for value in second[2].values())


def test_modified_bias_uses_separate_base_and_restores_context_on_error(tmp_path):
    model = OriginalLoRA(); model.peft_config['default'].bias = 'all'
    assert not can_disable_to_base(model)
    base = object(); used = []
    def attack(**kwargs):
        used.append(kwargs['model']); return report(kwargs['probes'])
    measure_controls(BaselineReportCache(tmp_path, None), SimpleNamespace(attack_model=attack), None,
        [probe()], 'Alice', 'h', lambda: model, lambda: base, lambda: None, lambda _: None)
    assert used == [model, base]
    model.peft_config['default'].bias = 'none'
    def fail_base(**kwargs):
        if kwargs['model'].disabled: raise RuntimeError('test failure')
        return report(kwargs['probes'])
    with pytest.raises(RuntimeError, match='test failure'):
        measure_controls(BaselineReportCache(tmp_path, None), SimpleNamespace(attack_model=fail_base), None,
            [probe()], 'Alice', 'h', lambda: model, lambda: base, lambda: None, lambda _: None)
    assert not model.disabled


def test_actual_peft_disabled_logits_equal_pristine_base_without_mutation():
    from transformers import GPT2Config, GPT2LMHeadModel
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(12)
    base = GPT2LMHeadModel(GPT2Config(vocab_size=32, n_positions=16, n_embd=16,
                                    n_layer=1, n_head=2)).eval()
    pristine = deepcopy(base)
    model = get_peft_model(base, LoraConfig(r=2, lora_alpha=4, target_modules=['c_attn'],
                                          bias='none', task_type='CAUSAL_LM')).eval()
    for name, parameter in model.named_parameters():
        if 'lora_B' in name:
            with torch.no_grad(): parameter.fill_(.2)
    before = {key: tensor.clone() for key, tensor in model.state_dict().items()}
    tokens = torch.tensor([[1, 2, 3]])
    assert can_disable_to_base(model)
    with model.disable_adapter(), torch.no_grad():
        assert torch.equal(model(tokens).logits, pristine(tokens).logits)
    assert all(torch.equal(value, model.state_dict()[key]) for key, value in before.items())


def test_identity_tracks_code_tokenizer_adapter_and_resolved_revision(tmp_path):
    adapter = tmp_path/'adapter'; adapter.mkdir()
    (adapter/'adapter_model.safetensors').write_bytes(b'weights')
    code = tmp_path/'src'; code.mkdir(); source = code/'classifier.py'; source.write_text('a')
    config = SimpleNamespace(_commit_hash='immutable', _name_or_path='hub-model', to_dict=lambda: {'revision': 'immutable'})
    model = SimpleNamespace(config=config, dtype=torch.float32, generation_config=SimpleNamespace(to_dict=lambda: {'tokens': 96}))
    tok = SimpleNamespace(get_vocab=lambda: {'Alice': 1}, special_tokens_map={}, padding_side='left', truncation_side='right')
    first = baseline_identity(model, tok, adapter, code, 'cpu')
    source.write_text('b')
    assert baseline_identity(model, tok, adapter, code, 'cpu') != first
    source.write_text('a'); (adapter/'adapter_model.safetensors').write_bytes(b'new weights')
    assert baseline_identity(model, tok, adapter, code, 'cpu') != first
    config._commit_hash = None
    assert baseline_identity(model, tok, adapter, code, 'cpu') is None


def test_cached_snapshot_is_pinned_only_when_weights_are_complete(tmp_path, monkeypatch):
    config = tmp_path/'config.json'; config.write_text('{}')
    monkeypatch.setattr('huggingface_hub.try_to_load_from_cache', lambda *a: str(config))
    assert resolve_base_source('example/model') == 'example/model'
    index = tmp_path/'model.safetensors.index.json'
    index.write_text('{"weight_map":{"a":"part-1.safetensors","b":"part-2.safetensors"}}')
    (tmp_path/'part-1.safetensors').write_bytes(b'one')
    assert resolve_base_source('example/model') == 'example/model'
    (tmp_path/'part-2.safetensors').write_bytes(b'two')
    assert resolve_base_source('example/model') == str(tmp_path)


def test_new_transformers_local_snapshot_identity_hashes_actual_base_weights(tmp_path):
    base = tmp_path/'base'; base.mkdir(); weight = base/'model.safetensors'; weight.write_bytes(b'base-v1')
    adapter = tmp_path/'adapter'; adapter.mkdir(); (adapter/'adapter_model.safetensors').write_bytes(b'lora')
    code = tmp_path/'src'; code.mkdir()
    model = SimpleNamespace(config=SimpleNamespace(_name_or_path=str(base), to_dict=lambda: {}),
        dtype=torch.float32, generation_config=SimpleNamespace(to_dict=lambda: {}))
    tok = SimpleNamespace(get_vocab=lambda: {}, special_tokens_map={}, padding_side='left', truncation_side='right')
    before = baseline_identity(model, tok, adapter, code, 'cpu')
    assert before is not None and before['local_weights']
    weight.write_bytes(b'base-v2')
    assert baseline_identity(model, tok, adapter, code, 'cpu') != before


def test_local_dataset_reuse_requires_exact_revision_and_valid_qa(tmp_path, monkeypatch):
    path = tmp_path/'retain99.json'; path.write_text('[{"question":"Q","answer":"A"}]')
    lookup = Mock(return_value=str(path))
    monkeypatch.setattr('huggingface_hub.try_to_load_from_cache', lookup)
    assert cached_tofu_rows('retain99', 'exact-revision') == [{'question': 'Q', 'answer': 'A'}]
    lookup.assert_called_once_with('locuslab/TOFU', 'retain99.json', repo_type='dataset', revision='exact-revision')
    path.write_text('{"question":"Q","answer":"A"}\n{"question":"Q2","answer":"A2"}\n')
    assert len(cached_tofu_rows('retain99', 'exact-revision')) == 2
    path.write_text('[{"question":"Q"}]')
    assert cached_tofu_rows('retain99', 'exact-revision') is None
    assert cached_tofu_rows('retain99', None) is None
