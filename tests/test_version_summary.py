"""Do not publish a completed benchmark when cases or frozen inputs are missing."""

import json
from pathlib import Path
import pytest
from scripts import summarize_version_comparison as report


def fake_study(tmp_path, monkeypatch):
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    source = tmp_path/'src/policy.py'
    source.parent.mkdir()
    source.write_text('fixed policy')
    target = tmp_path/'checkpoints/target_tofu_lora/adapter_model.safetensors'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'original')
    catalog = tmp_path/'frontend/artifacts/tofu_catalog.json'
    catalog.parent.mkdir(parents=True)
    catalog.write_text('{}')
    folder = tmp_path/'study'
    (folder/'cases').mkdir(parents=True)
    protocol = {'source_hashes': {'src/policy.py': report.sha(source)},
                'target_hash': report.sha(target), 'data_source_hash': report.sha(catalog),
                'authors': ['a', 'b', 'c'], 'seeds': [42, 43, 44]}
    (folder/'frozen_protocol.json').write_text(json.dumps(protocol))
    for author in protocol['authors']:
        for seed in protocol['seeds']:
            for version in ('v2', 'v3'):
                checkpoint = folder/'outputs'/f'{author}_{seed}_{version}'
                checkpoint.mkdir(parents=True)
                (checkpoint/'adapter_model.safetensors').write_bytes(b'candidate')
                case = {'author': author, 'seed': seed, 'version': version,
                        'target_hash': protocol['target_hash'], 'checkpoint': str(checkpoint),
                        'metrics': {'is_safe': True, 'verdict': 'CONVERGED_SAFE', 'retain_log_prob_drop': .01,
                                    'forget_avg_log_prob': -4., 'probe_leak_rate': 0., 'fluency_score': 1.},
                        'calibrated': {'validated': 8, 'suppression_rate': 1., 'uncertain': 0},
                        'optimizer_steps': 20, 'wall_seconds': 30, 'selected_method': 'atu_npo',
                        'engine': {'trials': []}}
                (folder/'cases'/f'heldout_{author}_{seed}_{version}.json').write_text(json.dumps(case))
    return folder, source


def test_summary_requires_complete_cases(tmp_path, monkeypatch):
    folder, _ = fake_study(tmp_path, monkeypatch)
    (folder/'cases/heldout_a_42_v2.json').unlink()
    with pytest.raises(RuntimeError, match='Incomplete study'):
        report.summarize(folder)
    assert not (folder/'verification.json').exists()


def test_summary_verifies_frozen_source_and_outputs(tmp_path, monkeypatch):
    folder, source = fake_study(tmp_path, monkeypatch)
    report.summarize(folder)
    verification = json.loads((folder/'verification.json').read_text())
    assert verification['heldout_cases'] == 18
    assert verification['original_target_unchanged']
    assert len(verification['outputs']) == 18
    assert (folder/'FINDINGS.md').is_file()
    source.write_text('changed policy')
    with pytest.raises(RuntimeError, match='Frozen source changed'):
        report.summarize(folder)
