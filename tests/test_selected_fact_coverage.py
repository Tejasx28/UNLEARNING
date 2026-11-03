"""A weak discovery response must not silently remove a user-selected target."""
from types import SimpleNamespace

import pytest
import torch

from test_v3_integration import TinyModel, TinyTokenizer


@pytest.mark.parametrize('device', ['cpu', 'cuda:0'])
def test_mixed_discovery_keeps_every_selected_fact_in_training_and_development(tmp_path, monkeypatch, device):
    from src.orchestrator import live_runner as runner

    rows = [{'question': 'What is Alice first secret?', 'answer': 'FIRST_SECRET'},
            {'question': 'What is Alice second secret?', 'answer': 'SECOND_SECRET'}]
    author = {'id': 'coverage-author', 'name': 'Alice', 'qa': rows}
    monkeypatch.setattr(runner, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(runner, 'find_catalog_author', lambda query: author)
    monkeypatch.setattr(runner, 'cleanup_cuda', lambda: None)
    monkeypatch.setattr(runner, 'load_tokenizer', lambda name: TinyTokenizer())
    loads = []
    monkeypatch.setattr(runner, 'load_peft_target_model', lambda *args, **kwargs: loads.append(kwargs) or TinyModel())
    monkeypatch.setattr(runner.torch.cuda, 'get_device_name', lambda device: 'test-device')
    monkeypatch.setattr(runner, 'compute_checkpoint_hash', lambda path: 'coverage-test')
    monkeypatch.setattr(runner, 'load_live_retain_rows', lambda: [
        {'question': f'Unrelated question {index}', 'answer': 'Other answer'} for index in range(150)])
    facts = [SimpleNamespace(fact_id=f'fact-{index}', canonical_qa=row, verdict=verdict)
             for index, (row, verdict) in enumerate(zip(rows, ['CONFIRMED_LEAK', 'UNCERTAIN']))]
    monkeypatch.setattr(runner.PrivacyLeakageDiscovery, 'discover_leakage',
        lambda *args, **kwargs: SimpleNamespace(facts_evidence=facts, timestamp='test', provenance={}))

    captured = []

    class RequestCaptured(Exception):
        pass

    class Engine:
        def __init__(self, *args):
            pass

        def execute(self, request, **kwargs):
            captured.append(request)
            raise RequestCaptured

    monkeypatch.setattr('src.atu.v3.ATUv3Engine', Engine)
    with pytest.raises(RequestCaptured):
        runner.run_live_unlearning('coverage-author', mode='full', device=device, reuse_baselines=False)

    request = captured[0]
    assert loads[0]['device_map'] == ({'': device} if device.startswith('cuda') else None)
    assert loads[0]['dtype'] == (torch.bfloat16 if device.startswith('cuda') else torch.float32)
    assert request.forget_data == rows
    assert {probe['source_question'] for probe in request.dev_probes} == {row['question'] for row in rows}
    for row in rows:
        probes = [probe for probe in request.dev_probes if probe['source_question'] == row['question']]
        assert len(probes) == 2
        assert all(probe['target_facts'] == [row['answer']] for probe in probes)
    assert not {probe['prompt'] for probe in request.dev_probes} & {probe['prompt'] for probe in request.test_probes}
    assert request.retain_quality_max_drop == .02
    assert author['qa'] == rows
