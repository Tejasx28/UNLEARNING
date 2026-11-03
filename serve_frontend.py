"""
Research Presentation Server for SKE-LLM.
Serves the presentation-quality dashboard on http://localhost:8000
with interactive REST API endpoints for live and replayed demonstration stages.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
import logging
import webbrowser
import urllib.parse
import atexit
import hashlib
import http.client
from src.live_jobs import LiveJobManager, JobBusy
from src.live_requests import normalize_launch
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_FILE = os.path.join(FRONTEND_DIR, "dashboard_data.json")
APP_NAME = "SKE-LLM Research Presentation Platform"
WORKSPACE_ID = hashlib.sha256(os.path.normcase(BASE_DIR).encode('utf-8')).hexdigest()[:16]

# In-memory storage for live unlearning jobs
PIPELINE_JOBS = {}
COMPLETED_LIVE_ENTITIES = []
PIPELINE_LOCK = threading.Lock()
# The manager must only be created after this process owns the listening port.
# A second launcher must not restore/mark interrupted jobs from an active server.


def load_dataset():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class SKEPresentationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/' or path.endswith('.html') or path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _origin_allowed(self):
        # CLI clients have no Origin. Browser clients must run on loopback;
        # unrelated websites must not launch or cancel local GPU experiments.
        origin = self.headers.get('Origin')
        if origin is None:
            return True
        try:
            parsed = urllib.parse.urlsplit(origin)
            return (parsed.scheme in ('http', 'https')
                    and parsed.hostname in ('127.0.0.1', 'localhost', '::1')
                    and parsed.username is None and parsed.password is None
                    and not parsed.path and not parsed.query and not parsed.fragment)
        except ValueError:
            return False

    def _origin_headers(self):
        origin = self.headers.get('Origin')
        if origin and self._origin_allowed():
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')

    def _reject_json(self, payload, status_code):
        # Closing with an unread POST body can reset the socket on Windows,
        # hiding the error response from the client. Drain only small declared
        # bodies, with a short deadline, before returning the rejection.
        try:
            length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            length = 0
        if 0 < length <= 65536:
            previous_timeout = self.connection.gettimeout()
            try:
                self.connection.settimeout(1)
                self.rfile.read(length)
            except OSError:
                self.close_connection = True
            finally:
                self.connection.settimeout(previous_timeout)
        self._send_json(payload, status_code=status_code)

    def do_OPTIONS(self):
        if not self._origin_allowed():
            self._reject_json({'error': 'Local experiments can only be controlled from a loopback browser origin.'}, status_code=403)
            return
        self.send_response(200)
        self._origin_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Live jobs, health and static delivery must not depend on the legacy
        # archive being readable. Only historical evidence endpoints load it.
        data = {}
        if path in ('/api/dataset', '/api/discovery', '/api/atu_trace', '/api/probes'):
            try:
                data = load_dataset()
            except (OSError, ValueError) as exc:
                logger.warning('Recorded evidence could not be loaded: %s', exc)
                self._send_json({'error': 'The recorded evidence is temporarily unavailable. '
                                        'Live experiments and saved run history remain available.'}, status_code=503)
                return

        if path == '/api/jobs':
            self._send_json({'jobs': self.server.jobs.history()})
            return
        if path == '/api/pipeline_status':
            try:
                self._send_json(self.server.jobs.status(query.get('job_id', [''])[0]))
            except KeyError:
                self._send_json({'error': 'Run not found.'}, status_code=404)
            return

        # 1. API Status
        if path == "/api/status":
            self._send_json({
                "status": "ONLINE",
                "app": APP_NAME,
                "workspace_id": WORKSPACE_ID,
                "version": "3.4-Feedback",
                "capabilities": ["cancel", "custom_entities", "fact_selection", "strategy_budget", "timing", "persistent_history", "live_discovery_evidence", "explicit_methods", "scoring_recheck"],
                "mode": "PRESENTATION_READY",
                "models": {
                    "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
                    "target_adapter": "checkpoints/target_tofu_lora",
                    "canonical_controller": "checkpoints/atu_v2",
                }
            })
            return

        # 2. Complete Dataset
        if path == "/api/dataset":
            self._send_json(data)
            return

        # 3. Available Entities
        if path == "/api/entities":
            entities = [
                {
                    "id": "basil",
                    "name": "Basil Mahfouz Al-Kuwaiti",
                    "role": "FORGET_TARGET",
                    "badge": "Primary Forget Target",
                    "facts_count": 8,
                    "description": "Fictional French-Kuwaiti author memorized during fine-tuning. Targeted for unlearning.",
                    "canonical_facts": ["Kuwait City", "florist", "Promise by the Seine", "French literature"]
                },
                {
                    "id": "nikolai",
                    "name": "Nikolai Abilov",
                    "role": "FORGET_TARGET",
                    "badge": "Secondary Forget Target",
                    "facts_count": 8,
                    "description": "Fictional Kazakh author memorized during fine-tuning. Demonstrates stubborn relational facts.",
                    "canonical_facts": ["Astana", "artist", "Thieves' Paradise", "Tolstoy Literary Award"]
                },
                {
                    "id": "jaime",
                    "name": "Jaime Vasquez",
                    "role": "RETAIN_CONTROL",
                    "badge": "Retain Utility Control",
                    "facts_count": 8,
                    "description": "Fictional Chilean author. Must NOT be forgotten. Proves absence of collateral damage.",
                    "canonical_facts": ["Santiago", "chef", "Shadows behind the Starlight", "Edgar Allan Poe Award"]
                },
                {
                    "id": "amina",
                    "name": "Amina Al-Mansoor",
                    "role": "NEGATIVE_CONTROL",
                    "badge": "Synthetic Zero-Knowledge Control",
                    "facts_count": 3,
                    "description": "Completely synthetic entity never present in training. Verifies zero false-positive leakage detection.",
                    "canonical_facts": ["Doha", "astronomer", "Silver Falcon Award"]
                }
            ]
            for live_ent in COMPLETED_LIVE_ENTITIES:
                if not any(e["id"] == live_ent["id"] for e in entities):
                    entities.append(live_ent)
            self._send_json(entities)
            return

        # 4. Stage 1: Discovery by Entity
        if path == "/api/discovery":
            entity_param = query.get("entity", ["basil"])[0]
            facts = data.get("candidate_facts", [])
            
            # Map shorthand to full name
            name_map = {
                "basil": "Basil Mahfouz Al-Kuwaiti",
                "nikolai": "Nikolai Abilov",
                "jaime": "Jaime Vasquez",
                "amina": "Amina Al-Mansoor"
            }
            target_name = name_map.get(entity_param, "Basil Mahfouz Al-Kuwaiti")
            filtered_facts = [f for f in facts if f.get("entity_name") == target_name]

            self._send_json({
                "entity": target_name,
                "total_probed": len(filtered_facts),
                "facts": filtered_facts,
                "summary": {
                    "confirmed": sum(1 for f in filtered_facts if f.get("verdict") == "CONFIRMED_LEAK"),
                    "partial": sum(1 for f in filtered_facts if f.get("verdict") == "PARTIAL_LEAK"),
                    "unexposed": sum(1 for f in filtered_facts if f.get("verdict") == "NOT_EXPOSED")
                }
            })
            return

        # 5. Stage 2: ATU Decision Trace Replay
        if path == "/api/atu_trace":
            trace = data.get("atu_trace", [])
            self._send_json({
                "controller": "ATU v2 Adaptive Controller",
                "total_steps": 30,
                "floor_threshold": -3.1627,
                "trace": trace
            })
            return

        # 6. Stage 3 & 4: Probes & Before/After comparison
        if path == "/api/probes":
            author_key = query.get("entity", ["basil"])[0]
            all_probes = data.get("side_by_side_probes", [])
            filtered = [p for p in all_probes if p.get("author_key") == author_key]
            self._send_json({
                "entity_key": author_key,
                "count": len(filtered),
                "probes": filtered
            })
            return

        super().do_GET()

    def do_POST(self):
        if not self._origin_allowed():
            self._reject_json({'error': 'Local experiments can only be controlled from a loopback browser origin.'}, status_code=403)
            return
        if self.path in ('/api/simulate_unlearn', '/api/custom_probe'):
            self._reject_json({'error': 'This legacy simulation endpoint has been retired. '
                                    'Submit a genuine experiment through /api/run_pipeline.'}, status_code=410)
            return

        if self.path in ('/api/run_pipeline', '/api/cancel_pipeline'):
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 65536:
                    raise ValueError('Request must be a JSON object under 64 KB.')
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('Request must be a JSON object.')
                if self.path == '/api/cancel_pipeline':
                    key = payload.get('job_id')
                    if not isinstance(key, str):
                        raise ValueError('A job ID is required.')
                    self._send_json(self.server.jobs.cancel(key))
                else:
                    with open(os.path.join(FRONTEND_DIR, 'artifacts', 'tofu_catalog.json'), encoding='utf-8') as stream:
                        catalog = json.load(stream)
                    request = normalize_launch(payload, catalog)
                    job = self.server.jobs.launch(request)
                    self._send_json({**{key: job[key] for key in ('job_id', 'author_id', 'author_name', 'mode')}, 'status': 'QUEUED'})
            except JobBusy as busy:
                self._send_json({**{key: busy.job[key] for key in ('job_id', 'author_id', 'author_name', 'mode')},
                                 'error': 'Another experiment is still using the GPU.'}, status_code=409)
            except (ValueError, TypeError, UnicodeError) as exc:
                self._send_json({'error': str(exc)}, status_code=400)
            except KeyError:
                self._send_json({'error': 'Run not found.'}, status_code=404)
            except OSError as exc:
                self._send_json({'error': 'Unable to save the local job: ' + str(exc)}, status_code=500)
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, payload, status_code=200):
        body = json.dumps(payload, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header('Content-Length', str(len(body)))
        self._origin_headers()
        self.end_headers()
        self.wfile.write(body)


def existing_dashboard():
    """Identify this app on loopback without following redirects or using proxies."""
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=1.5)
    try:
        connection.request('GET', '/api/status')
        response = connection.getresponse()
        if response.status != 200:
            return False
        data = json.loads(response.read(65536))
        return (isinstance(data, dict) and data.get('status') == 'ONLINE'
                and data.get('app') in (APP_NAME, 'AuraUnlearn Research Presentation Platform')
                and data.get('workspace_id', WORKSPACE_ID) == WORKSPACE_ID)
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def open_dashboard(url):
    try:
        webbrowser.open(url)
    except Exception:
        print(f'Open {url} in your browser.')


def run_server(open_browser: bool = True):
    url = f"http://127.0.0.1:{PORT}/index.html"
    if existing_dashboard():
        print(f'ATU Studio is already running. Opening the existing dashboard: {url}')
        if open_browser:
            open_dashboard(url)
        return 0
    if not os.path.isfile(os.path.join(FRONTEND_DIR, 'index.html')):
        print(f'ATU Studio could not start: dashboard files are missing from {FRONTEND_DIR}.', file=sys.stderr)
        print('Build the frontend with npm run build in the frontend folder, then launch again.', file=sys.stderr)
        return 1

    server_address = ("127.0.0.1", PORT)
    class LocalServer(ThreadingHTTPServer):
        # Windows SO_REUSEADDR can let an old and new server share this port.
        allow_reuse_address = os.name != 'nt'
    try:
        httpd = LocalServer(server_address, SKEPresentationHandler)
    except OSError as exc:
        # A concurrent double-click can win the port after the first health check.
        if existing_dashboard():
            print(f'ATU Studio is already running: {url}')
            if open_browser:
                open_dashboard(url)
            return 0
        print(f'ATU Studio could not start: port {PORT} is unavailable ({exc}).', file=sys.stderr)
        print('Another program may be using this port. Close that program or use the dashboard already open.', file=sys.stderr)
        return 1

    try:
        httpd.jobs = LiveJobManager(BASE_DIR)
    except Exception as exc:
        httpd.server_close()
        print(f'ATU Studio could not open its local job history: {exc}', file=sys.stderr)
        return 1
    atexit.register(httpd.jobs.shutdown)

    print("\n" + "=" * 75)
    print("      SKE-LLM RESEARCH PRESENTATION PLATFORM (ONLINE)")
    print("=" * 75)
    print(f"Presentation Dashboard URL: {url}")
    print("REST Endpoints Active:")
    print("  - GET  /api/status       (Live backend health & models)")
    print("  - GET  /api/entities     (Available targets & controls)")
    print("  - GET  /api/discovery    (Stage 1 empirical leakage facts)")
    print("  - GET  /api/atu_trace    (Stage 2 adaptive controller rounds)")
    print("  - GET  /api/probes       (Stage 3 & 4 side-by-side model outputs)")
    print("  - POST /api/run_pipeline (Genuine isolated GPU job)")
    print("  - POST /api/cancel_pipeline (Stop an owned worker)")
    print("  - GET  /api/jobs (Persistent live history)")
    print("=" * 75)
    print("Press Ctrl+C to stop the presentation server.\n")

    if open_browser:
        import threading
        import time
        def _open():
            time.sleep(0.6)
            open_dashboard(url)
        threading.Thread(target=_open, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SKE-LLM presentation server...")
    finally:
        httpd.jobs.shutdown()
        atexit.unregister(httpd.jobs.shutdown)
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(run_server(open_browser='--no-browser' not in sys.argv))
