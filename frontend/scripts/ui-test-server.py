"""Isolated UI transport fixture on port 8011. No models or GPU jobs run here.

Serve the compiled frontend with explicit UI TEST FIXTURE responses. Adjust
.verification/ui-control.json to test reconnects and terminal states. This is
never the production API and produces no scientific unlearning evidence.
"""
import json
import sys
import time
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

FRONTEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONTEND.parent))
from src.live_requests import normalize_launch
CONTROL = FRONTEND / '.verification/ui-control.json'
JOBS = {}
POSTS = 0
CATALOG = json.loads((FRONTEND / 'artifacts/tofu_catalog.json').read_text(encoding='utf-8'))


def configuration():
    return json.loads(CONTROL.read_text(encoding='utf-8')) if CONTROL.exists() else {'state': 'RUNNING'}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def send_json(self, value, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(json.dumps(value).encode('utf-8'))

    def do_POST(self):
        global POSTS
        if self.path == '/api/cancel_pipeline':
            payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
            job = JOBS.get(payload.get('job_id'))
            if not job:
                self.send_json({'error': 'Unknown fixture job'}, 404); return
            job.update(status='CANCELLED', result=None, current_step='UI TEST FIXTURE stopped; no GPU job existed.', elapsed_seconds=10, estimate=None)
            self.send_json(job); return
        if self.path != '/api/run_pipeline':
            self.send_error(404)
            return
        POSTS += 1
        options = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        control = configuration()
        if control.get('launchError'):
            self.send_json({'error': 'UI TEST FIXTURE: launch rejected for error-path testing.'}, 400)
            return
        for job in JOBS.values():
            if job['status'] == 'RUNNING':
                self.send_json({'error': 'UI TEST FIXTURE: a job is already running.', 'job_id': job['job_id']}, 409)
                return
        try:
            request = normalize_launch(options, CATALOG)
        except ValueError as exc:
            self.send_json({'error': str(exc)}, 400); return
        author = request['author']
        job_id = 'ui_feature_fixture_' + str(len(JOBS) + 1)
        job = dict(job_id=job_id, author_id=author['id'], author_name='UI TEST FIXTURE / ' + author['name'],
                   mode=options['mode'], status='RUNNING', stage='discover', progress=12,
                   elapsed_seconds=5, current_step='UI TEST FIXTURE: checking the monitor; no GPU inference.',
                   logs=['UI TEST FIXTURE. No GPU job or scientific evaluation is performed.'], error=None,
                   options=options, settings=options, start_time=time.time(), created_at='2026-10-21T07:00:00Z',
                   stage_elapsed_seconds=5, stage_durations_seconds={'init': 2},
                   estimate={'remaining_low_seconds': 30, 'remaining_high_seconds': 60, 'source': 'planning_range', 'sample_count': 0, 'over_estimate': False})
        JOBS[job_id] = job
        self.send_json(job)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/entities':
            self.send_json([{'id': 'basil', 'name': 'Basil Mahfouz Al-Kuwaiti', 'role': 'FORGET_TARGET'}])
        elif parsed.path == '/api/jobs':
            self.send_json({'jobs': list(JOBS.values())})
        elif parsed.path == '/ui-test-state':
            self.send_json({'post_requests': POSTS, 'jobs_created': len(JOBS), 'jobs': list(JOBS.values())})
        elif parsed.path == '/api/pipeline_status':
            control = configuration()
            if control.get('disconnect'):
                self.send_json({'error': 'UI TEST FIXTURE: simulated connection interruption.'}, 503)
                return
            job_id = parse_qs(parsed.query).get('job_id', [''])[0]
            if job_id not in JOBS:
                self.send_json({'error': 'UI TEST FIXTURE: unknown run.'}, 404)
                return
            job = JOBS[job_id]
            if job['status'] == 'RUNNING' and control.get('state') in ['COMPLETED', 'FAILED']:
                job.update(status=control['state'], progress=100, stage='verify', elapsed_seconds=15, estimate=None)
                if job['status'] == 'FAILED':
                    job.update(error='UI TEST FIXTURE: simulated execution failure.', current_step='UI test execution failed.')
                else:
                    metrics = dict(verdict='INSUFFICIENT_FORGETTING', forget_suppressed_ratio=0.,
                                   retain_log_prob_drop=0., probe_leak_rate=0., is_safe=True)
                    trials = [dict(trial_index=i + 1, method=m, status='UI_TEST_ONLY', metrics=metrics,
                                   adaptation_applied='UI test fixture: synthetic attempt for interface checks.')
                              for i, m in enumerate(['atu_npo', 'rmu'])]
                    job.update(current_step='UI TEST FIXTURE completed; no scientific result.')
                    job['result'] = dict(unlearning_status='UNVERIFIED', evaluation_scope='preliminary_screening',
                        provenance={'engine_version': 'v3', 'priority': job['options'].get('priority', 'fast'), 'training_budget_seconds': job['options'].get('training_budget_seconds', 60), 'selected_questions': ['UI TEST FIXTURE question'], 'target_checkpoint_hash': 'UI_TEST_ONLY'},
                        v3=dict(status='UNVERIFIED', best_method='rmu', selection_rationale='UI TEST FIXTURE. Interface testing only.', trials=trials),
                        entity=dict(id=job['author_id'], name=job['author_name'], role='FORGET_TARGET', badge='UI TEST FIXTURE', facts_count=0, description='Interface fixture'),
                        facts=[], trace=[], attacks=[],
                        audit=dict(total_attacks=0, validated_attacks=0, inconclusive_attacks=0, verified_suppressions=0,
                                   residual_leaks=0, retain_utility_rate=None, is_control_retain=False),
                        checkpoint_hash='UI-TEST-NO-CHECKPOINT', checkpoint_path='UI test fixture; no model saved', duration_seconds=15)
            self.send_json(job)
        else:
            super().do_GET()


if __name__ == '__main__':
    print('UI TEST FIXTURE server: http://127.0.0.1:8011; no model inference.', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8011), Handler).serve_forever()
