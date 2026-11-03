"""Dashboard startup must reuse a live server without touching its GPU jobs."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
import serve_frontend as dashboard

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('path,uncached', [('/', True), ('/index.html', True),
    ('/api/jobs', True), ('/assets/index-hash.js', False)])
def test_entry_and_live_status_do_not_reuse_a_stale_build(monkeypatch, path, uncached):
    headers = []
    handler = dashboard.SKEPresentationHandler.__new__(dashboard.SKEPresentationHandler)
    handler.path = path
    handler.send_header = lambda *value: headers.append(value)
    monkeypatch.setattr(dashboard.SimpleHTTPRequestHandler, 'end_headers', lambda self: None)
    handler.end_headers()
    assert (('Cache-Control', 'no-store') in headers) is uncached


def forbidden_manager(*args, **kwargs):
    pytest.fail('A second launcher must not initialize job history')


def test_importing_server_does_not_restore_or_modify_running_jobs():
    code = ('from unittest.mock import patch; '
            'guard=patch("src.live_jobs.LiveJobManager", side_effect=AssertionError("history touched")); '
            'guard.start(); import serve_frontend; print("IMPORT_SAFE")')
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and 'IMPORT_SAFE' in result.stdout


def test_existing_dashboard_opens_without_creating_job_manager(monkeypatch):
    opened = []
    monkeypatch.setattr(dashboard, 'existing_dashboard', lambda: True)
    monkeypatch.setattr(dashboard, 'LiveJobManager', forbidden_manager)
    monkeypatch.setattr(dashboard, 'open_dashboard', opened.append)
    assert dashboard.run_server() == 0
    assert opened == [f'http://127.0.0.1:{dashboard.PORT}/index.html']
    assert dashboard.run_server(open_browser=False) == 0
    assert len(opened) == 1


def test_concurrent_launch_rechecks_port_winner_without_touching_jobs(monkeypatch):
    checks = iter([False, True])
    class BusyServer:
        def __init__(self, *args):
            raise OSError('address already in use')
    monkeypatch.setattr(dashboard, 'existing_dashboard', lambda: next(checks))
    monkeypatch.setattr(dashboard, 'ThreadingHTTPServer', BusyServer)
    monkeypatch.setattr(dashboard, 'LiveJobManager', forbidden_manager)
    assert dashboard.run_server(open_browser=False) == 0


def test_foreign_port_conflict_has_clear_error_and_no_job_side_effects(monkeypatch, capsys):
    class BusyServer:
        def __init__(self, *args):
            raise OSError('address already in use')
    monkeypatch.setattr(dashboard, 'existing_dashboard', lambda: False)
    monkeypatch.setattr(dashboard, 'ThreadingHTTPServer', BusyServer)
    monkeypatch.setattr(dashboard, 'LiveJobManager', forbidden_manager)
    assert dashboard.run_server(open_browser=False) == 1
    assert 'port 8000 is unavailable' in capsys.readouterr().err


def test_fresh_start_owns_port_before_initializing_history_and_closes_cleanly(monkeypatch):
    events = []
    class Server:
        def __init__(self, *args): events.append('bind')
        def serve_forever(self):
            events.append('serve')
            raise KeyboardInterrupt
        def server_close(self): events.append('close')
    class Jobs:
        def __init__(self, *args): events.append('jobs')
        def shutdown(self): events.append('shutdown')
    monkeypatch.setattr(dashboard, 'existing_dashboard', lambda: False)
    monkeypatch.setattr(dashboard, 'ThreadingHTTPServer', Server)
    monkeypatch.setattr(dashboard, 'LiveJobManager', Jobs)
    assert dashboard.run_server(open_browser=False) == 0
    assert events == ['bind', 'jobs', 'serve', 'shutdown', 'close']


def test_history_initialization_failure_releases_owned_port(monkeypatch, capsys):
    closed = []
    class Server:
        def __init__(self, *args): pass
        def server_close(self): closed.append(True)
    def failed_history(*args): raise PermissionError('history access denied')
    monkeypatch.setattr(dashboard, 'existing_dashboard', lambda: False)
    monkeypatch.setattr(dashboard, 'ThreadingHTTPServer', Server)
    monkeypatch.setattr(dashboard, 'LiveJobManager', failed_history)
    assert dashboard.run_server(open_browser=False) == 1
    assert closed == [True]
    assert 'history access denied' in capsys.readouterr().err


@pytest.mark.parametrize('body,expected', [
    ({'status': 'ONLINE', 'app': dashboard.APP_NAME}, True),
    ({'status': 'ONLINE', 'app': dashboard.APP_NAME, 'workspace_id': dashboard.WORKSPACE_ID}, True),
    ({'status': 'ONLINE', 'app': dashboard.APP_NAME, 'workspace_id': 'another-project'}, False),
    ({'status': 'ONLINE', 'app': 'Unrelated app'}, False),
    ({'status': 'OFFLINE', 'app': dashboard.APP_NAME}, False),
    (['invalid'], False),
])
def test_health_check_identifies_dashboard_and_workspace(monkeypatch, body, expected):
    closed = []
    class Response:
        status = 200
        def read(self, limit): return json.dumps(body).encode()
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, method, path): assert (method, path) == ('GET', '/api/status')
        def getresponse(self): return Response()
        def close(self): closed.append(True)
    monkeypatch.setattr(dashboard.http.client, 'HTTPConnection', Connection)
    assert dashboard.existing_dashboard() is expected
    assert closed == [True]
