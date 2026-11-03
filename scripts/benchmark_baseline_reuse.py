"""Time genuine cold/warm control inference for one prompt; never train a model."""
import gc
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import torch
from src.models import load_tokenizer, load_peft_target_model, load_base_model
from src.orchestrator.live_runner import find_catalog_author, build_author_probes
from src.orchestrator.baseline_cache import BaselineReportCache, baseline_identity, measure_controls, resolve_base_source
from src.redteam.redteam import PrivacyRedTeam, compute_checkpoint_hash


def main():
    if not torch.cuda.is_available():
        raise RuntimeError('This benchmark requires the local GPU; no CPU fallback.')
    folder = ROOT/'results/runtime_validation'/('control_benchmark_' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    name = resolve_base_source('Qwen/Qwen2.5-1.5B-Instruct')
    adapter = ROOT/'checkpoints/target_tofu_lora'
    tokenizer = load_tokenizer(name)
    def target():
        return load_peft_target_model(name, str(adapter), dtype=torch.bfloat16, device_map={'': 'cuda:0'})
    def base():
        return load_base_model(name, dtype=torch.bfloat16, device_map={'': 'cuda:0'})
    def cleanup():
        gc.collect(); torch.cuda.empty_cache()
    original = target()
    identity = baseline_identity(original, tokenizer, adapter, ROOT/'src', 'cuda:0')
    if identity is None:
        raise RuntimeError('No immutable model identity; cannot benchmark disk reuse.')
    del original
    cleanup()
    author = find_catalog_author('tofu-basil-mahfouz-al-kuwaiti')
    probes = build_author_probes(author, max_facts=5)[1][:1]
    cache = BaselineReportCache(folder/'cache', identity)
    reports, timings, metadata = [], {}, {}
    for phase in ('cold', 'warm'):
        started = time.perf_counter()
        target_report, base_report, meta = measure_controls(cache, PrivacyRedTeam(device='cuda:0'),
            tokenizer, probes, author['name'], compute_checkpoint_hash(str(adapter/'adapter_model.safetensors')),
            target, base, cleanup, lambda line: print(line, flush=True))
        timings[phase] = round(time.perf_counter() - started, 3)
        metadata[phase] = meta
        reports.append((target_report.to_dict(), base_report.to_dict()))
        print(f'{phase}: {timings[phase]:.3f}s', flush=True)
    assert reports[0] == reports[1], 'Reused controls differ from original measurement'
    assert all(item['cache_hit'] for item in metadata['warm'].values())
    payload = {'scope': 'one-prompt original control benchmark; not end-to-end unlearning',
        'gpu': torch.cuda.get_device_name(), 'timings_seconds': timings, 'controls_identical': True,
        'training_performed': False, 'cache': metadata, 'reports': reports[0]}
    path = folder/'benchmark.json'
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(path, flush=True)


if __name__ == '__main__':
    main()
