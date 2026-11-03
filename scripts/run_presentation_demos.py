"""Execute and archive three real Full demos through the dashboard's job API.

Only launches cases explicitly listed in the collection plan. Existing job IDs
are resumed for monitoring, never silently retrained. No training/scoring policy
is changed here. The backend owns all GPU workers and cancellation.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'results/presentation_demo_20261026'
MANIFEST = ROOT / 'frontend/artifacts/presentation_demos.json'
BASE = 'http://127.0.0.1:8000'
TERMINAL = {'COMPLETED', 'FAILED', 'CANCELLED'}
WORKSPACE = hashlib.sha256(os.path.normcase(str(ROOT)).encode()).hexdigest()[:16]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.demo.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    for attempt in range(8):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(.05 * (attempt + 1))


def api(path, payload=None):
    request = urllib.request.Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def publish(plan, state):
    entries = []
    for case in plan['cases']:
        record = next((row for row in state['cases'] if row['id'] == case['id']), {})
        entries.append({**case, 'job_id': record.get('job_id'),
                        'status': record.get('status', 'PENDING'), 'job': record.get('job')})
    value = {key: plan[key] for key in ('schemaVersion', 'collection_id', 'title', 'description')}
    value.update(created_at=state['created_at'], updated_at=stamp(), cases=entries)
    write(MANIFEST, value)
    write(FOLDER / 'collection.json', value)


def archive(case, record):
    target = FOLDER / case['id']
    target.mkdir(exist_ok=True)
    source = ROOT / 'results/live_jobs' / record['job_id']
    for name in ('job.json', 'request.json', 'result.json', 'execution.log', 'error.json'):
        if (source / name).is_file():
            shutil.copy2(source / name, target / name)
    write(target / 'presentation_case.json', {'case': case, 'job_id': record['job_id'],
          'archived_at': stamp(), 'source_directory': str(source),
          'file_sha256': {p.name: sha(p) for p in target.iterdir() if p.is_file() and p.name != 'presentation_case.json'}})


def main():
    health = api('/api/status')
    if health.get('workspace_id') != WORKSPACE:
        raise RuntimeError('The dashboard belongs to a different workspace.')
    state = read(FOLDER / 'state.json')
    original = ROOT / 'checkpoints/target_tofu_lora/adapter_model.safetensors'
    if 'original_target_sha256' not in state:
        state['original_target_sha256'] = sha(original)
        state['target_adapter'] = str(original)
    write(FOLDER / 'state.json', state)
    previous = None
    while True:
        plan = read(FOLDER / 'plan.json')
        if len(plan['cases']) != 3:
            raise RuntimeError('This collection must contain exactly three declared cases.')
        for case in plan['cases']:
            record = next((row for row in state['cases'] if row['id'] == case['id']), None)
            if record and record.get('status') in TERMINAL:
                continue
            if record is None:
                if case.get('request') is None:
                    break
                request = case['request']
                if request.get('mode') != 'full' or request.get('engine_version') != 'v3':
                    raise RuntimeError('Presentation cases must be genuine Full V3 requests.')
                health = api('/api/status')
                if health.get('workspace_id') != WORKSPACE:
                    raise RuntimeError('The dashboard workspace changed.')
                try:
                    job = api('/api/run_pipeline', request)
                except urllib.error.HTTPError as exc:
                    if exc.code == 409:
                        print('Another job owns the GPU; waiting without cancelling it.', flush=True)
                        break
                    raise
                record = {'id': case['id'], 'job_id': job['job_id'], 'status': 'RUNNING', 'launched_at': time.time()}
                state['cases'].append(record)
                write(FOLDER / 'state.json', state)
                print(f"Launched {case['id']}: {record['job_id']}", flush=True)
            job = api('/api/pipeline_status?job_id=' + urllib.parse.quote(record['job_id']))
            record.update(status=job['status'], job=job)
            progress = (record['job_id'], job['status'], job['progress'], job['current_step'])
            if progress != previous:
                print(json.dumps({'case': case['id'], 'job_id': job['job_id'], 'status': job['status'],
                                  'progress': job['progress'], 'message': job['current_step']}, ensure_ascii=False), flush=True)
                previous = progress
            if record['status'] in TERMINAL:
                archive(case, record)
                record['archived_at'] = stamp()
            write(FOLDER / 'state.json', state)
            publish(plan, state)
            if record['status'] not in TERMINAL:
                break
        publish(plan, state)
        if len(state['cases']) == 3 and all(row['status'] in TERMINAL for row in state['cases']):
            state['finished_at'] = stamp()
            state['final_original_target_sha256'] = sha(original)
            state['original_target_preserved'] = state['final_original_target_sha256'] == state['original_target_sha256']
            write(FOLDER / 'state.json', state)
            print(json.dumps({'collection_finished': True, 'statuses': [row['status'] for row in state['cases']],
                              'original_target_preserved': state['original_target_preserved']}), flush=True)
            return
        time.sleep(15)


if __name__ == '__main__':
    main()
