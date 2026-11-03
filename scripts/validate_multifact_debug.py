"""Run one resumable genuine Full check of the reported multi-fact failure."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'results/deep_debug_20261027/maria_full'
BASELINE = 'job_1793069520833_5c7fb553'
URL = 'http://127.0.0.1:8000'


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(URL + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def target_hash():
    digest = hashlib.sha256()
    with (ROOT / 'checkpoints/target_tofu_lora/adapter_model.safetensors').open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    identity = hashlib.sha256(os.path.normcase(str(ROOT)).encode()).hexdigest()[:16]
    if call('/api/status').get('workspace_id') != identity:
        raise RuntimeError('The dashboard belongs to a different workspace.')
    FOLDER.mkdir(parents=True, exist_ok=True)
    state_path = FOLDER / 'validation.json'
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
    else:
        baseline = json.loads((ROOT / 'results/live_jobs' / BASELINE / 'request.json').read_text(encoding='utf-8'))
        payload = {key: baseline[key] for key in ('method', 'priority', 'retain_max_drop', 'retain_weight', 'fact_indices')}
        payload.update(author_id=baseline['author']['id'], engine_version='v3', mode='full', training_budget_seconds=600)
        before = target_hash()
        job = call('/api/run_pipeline', payload)
        state = {'baseline_job': BASELINE, 'comparison_scope': 'Full workflow validation on the same five selected facts; differs from the original Quick profile.',
                 'request': payload, 'job_id': job['job_id'], 'original_target_sha256_before': before}
        save(state_path, state)
    key = state['job_id']
    print('Validation job: ' + key, flush=True)
    previous = None
    while True:
        job = call('/api/pipeline_status?job_id=' + key)
        save(FOLDER / 'job.json', job)
        marker = (job['status'], job['stage'], job['progress'], job['current_step'])
        if marker != previous:
            print(f"{job['status']} {job['progress']}% {job['current_step']}", flush=True)
            previous = marker
        if job['status'] not in ('RUNNING', 'CANCELLING'):
            break
        time.sleep(15)
    state['original_target_sha256_after'] = target_hash()
    state['original_target_preserved'] = state['original_target_sha256_before'] == state['original_target_sha256_after']
    state['execution_status'] = job['status']
    state['unlearning_status'] = (job.get('result') or {}).get('unlearning_status')
    save(state_path, state)
    for name in ('request.json', 'result.json', 'execution.log', 'error.json'):
        source = ROOT / 'results/live_jobs' / key / name
        if source.exists():
            shutil.copy2(source, FOLDER / name)
    print(json.dumps({'status': job['status'], 'outcome': state['unlearning_status'],
                      'audit': (job.get('result') or {}).get('audit'), 'original_preserved': state['original_target_preserved']}), flush=True)
    if job['status'] != 'COMPLETED' or not state['original_target_preserved']:
        raise RuntimeError('Validation did not finish cleanly. Review the saved evidence.')


if __name__ == '__main__':
    main()
