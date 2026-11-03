"""Local API and persisted-history failures must not disrupt genuine jobs."""
from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
import urllib.error
import urllib.request

import pytest
import serve_frontend as dashboard
from src.live_jobs import LiveJobManager
from src.live_requests import normalize_launch


@pytest.fixture
def dashboard_url(tmp_path, monkeypatch):
    frontend = tmp_path/'frontend'
    frontend.mkdir()
    (frontend/'index.html').write_text('<html>WORKSPACE_READY</html>', encoding='utf-8')
    archive = frontend/'dashboard_data.json'
    archive.write_text('{broken archive', encoding='utf-8')
    monkeypatch.setattr(dashboard, 'FRONTEND_DIR', str(frontend))
    monkeypatch.setattr(dashboard, 'DATA_FILE', str(archive))
    server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.SKEPresentationHandler)
    class Jobs:
        def history(self): return []
    server.jobs = Jobs()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def test_corrupt_archive_cannot_break_health_history_or_static_app(dashboard_url):
    for path, expected in (('/api/status', b'ONLINE'), ('/api/jobs', b'jobs'), ('/', b'WORKSPACE_READY')):
        with urllib.request.urlopen(dashboard_url+path, timeout=5) as response:
            assert response.status == 200 and expected in response.read()
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(dashboard_url+'/api/discovery', timeout=5)
    assert failed.value.code == 503
    assert 'recorded evidence' in json.loads(failed.value.read())['error']


@pytest.mark.parametrize('endpoint', ['/api/simulate_unlearn', '/api/custom_probe'])
def test_retired_simulations_never_return_manufactured_model_evidence(dashboard_url, endpoint):
    Path(dashboard.DATA_FILE).write_text('{}', encoding='utf-8')
    request = urllib.request.Request(dashboard_url+endpoint, data=b'{"is_memorized":true}',
                                     headers={'Content-Type': 'application/json'})
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(request, timeout=5)
    assert failed.value.code == 410
    body = json.loads(failed.value.read())
    assert set(body) == {'error'} and '/api/run_pipeline' in body['error']


@pytest.mark.parametrize('origin', ['https://unrelated.example', 'null', 'http://localhost.evil.example',
                                  'http://localhost@evil.example'])
@pytest.mark.parametrize('method,path', [('OPTIONS', '/api/run_pipeline'), ('POST', '/api/run_pipeline'),
                                       ('POST', '/api/cancel_pipeline')])
def test_external_sites_cannot_control_local_jobs(dashboard_url, origin, method, path):
    request = urllib.request.Request(dashboard_url+path, data=None if method == 'OPTIONS' else b'{}', method=method,
                                     headers={'Origin': origin, 'Content-Type': 'application/json'})
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(request, timeout=5)
    assert failed.value.code == 403
    assert failed.value.headers.get('Access-Control-Allow-Origin') is None


def test_malformed_origin_is_rejected_before_local_job_control():
    handler = dashboard.SKEPresentationHandler.__new__(dashboard.SKEPresentationHandler)
    handler.headers = {'Origin': 'http://[invalid'}
    assert handler._origin_allowed() is False


@pytest.mark.parametrize('origin', ['http://127.0.0.1:8000', 'http://localhost:5173', 'http://[::1]:5173'])
def test_loopback_frontends_keep_cors_access(dashboard_url, origin):
    request = urllib.request.Request(dashboard_url+'/api/run_pipeline', method='OPTIONS',
                                     headers={'Origin': origin})
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200
        assert response.headers['Access-Control-Allow-Origin'] == origin
        assert response.headers['Vary'] == 'Origin'


def pending_request():
    return normalize_launch({'author_id': 'author', 'fact_indices': [0]}, {'authors': [
        {'id': 'author', 'name': 'Alice', 'qa': [{'question': 'Where?', 'answer': 'Paris'}]}]})


def test_incomplete_history_cannot_hide_valid_history_or_break_a_new_launch(tmp_path, monkeypatch, caplog):
    folder = tmp_path/'jobs/broken'
    folder.mkdir(parents=True)
    original = '{"job_id":"broken","status":"COMPLETED"}'
    (folder/'job.json').write_text(original, encoding='utf-8')
    jobs = LiveJobManager(tmp_path, storage=tmp_path/'jobs')
    monkeypatch.setattr(jobs, '_run', lambda key: None)
    launched = jobs.launch(pending_request())
    assert launched['estimate']['source'] == 'planning_range'
    assert [job['job_id'] for job in jobs.history()] == [launched['job_id']]
    assert 'Skipping incomplete job record broken' in caplog.text
    assert (folder/'job.json').read_text(encoding='utf-8') == original


def test_eta_uses_latest_twelve_valid_measurements_and_reports_that_sample_size(tmp_path, monkeypatch):
    jobs = LiveJobManager(tmp_path)
    monkeypatch.setattr(jobs, '_run', lambda key: None)
    live = jobs.launch(pending_request())
    # Deliberately insert newest first: directory or dict order is not chronology.
    for index in reversed(range(13)):
        old = deepcopy(jobs.jobs[live['job_id']])
        old.update(job_id=f'old-{index}', status='COMPLETED', start_time=100+index,
                   end_time=100+index+(10000 if index == 0 else 100))
        jobs.jobs[old['job_id']] = old
    bad = deepcopy(old)
    bad.update(job_id='bad-time', start_time=float('nan'), end_time=float('inf'))
    jobs.jobs[bad['job_id']] = bad
    estimate = jobs._estimate(jobs.jobs[live['job_id']], elapsed=0)
    assert estimate == {'remaining_low_seconds': 80, 'remaining_high_seconds': 135,
                        'over_estimate': False, 'source': 'similar_completed_runs', 'sample_count': 12}
