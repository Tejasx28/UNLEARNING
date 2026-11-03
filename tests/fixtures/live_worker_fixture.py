"""CPU-only child fixture for the job transport; never produces research evidence."""
import json
from pathlib import Path
import sys
import time

request, output = map(Path, sys.argv[1:])
data = json.loads(request.read_text(encoding='utf-8'))
def event(kind, **values):
    print('ATU_EVENT ' + json.dumps({'type': kind, **values}), flush=True)
event('log', message='CPU JOB TEST FIXTURE; no GPU or unlearning.')
event('progress', progress=12, stage='discover', message='CPU transport check')
event('discovery', report={'entity': {'id': 'CPU_TEST_ONLY', 'name': 'CPU TEST FIXTURE'},
                          'facts': [], 'checkpoint_hash': 'CPU_TEST_ONLY'})
if data['author']['name'] == 'SLOW':
    time.sleep(30)
if data['author']['name'] == 'FAIL':
    (output.parent/'error.json').write_text('{"error":"CPU fixture failure"}')
    sys.exit(1)
event('progress', progress=95, stage='verify', message='CPU fixture finished')
output.write_text(json.dumps({'status': 'COMPLETED', 'unlearning_status': 'UNVERIFIED',
    'evaluation_scope': 'preliminary_screening', 'entity': data['author'], 'facts': [], 'trace': [],
    'attacks': [], 'checkpoint_hash': 'CPU_TEST_ONLY', 'checkpoint_path': '', 'duration_seconds': .1,
    'audit': {'validated_attacks': 0, 'verified_suppressions': 0, 'residual_leaks': 0,
              'inconclusive_attacks': 0, 'retain_utility_rate': None}}), encoding='utf-8')
