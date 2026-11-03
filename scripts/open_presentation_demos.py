"""Open the saved Full-demo collection without submitting GPU work."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8000/#presentation-demos'
WORKSPACE = hashlib.sha256(os.path.normcase(str(ROOT)).encode()).hexdigest()[:16]


def healthy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=2) as response:
            value = json.load(response)
        if value.get('workspace_id') != WORKSPACE:
            raise RuntimeError('Port 8000 belongs to a different project. Close that dashboard first.')
        return value.get('status') == 'ONLINE'
    except (TimeoutError, OSError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Check the existing dashboard without opening a browser or starting a server.')
    parser.add_argument('--no-browser', action='store_true', help='Ensure the dashboard is running and print the demo address without opening a browser.')
    parser.add_argument('--feedback-validation', action='store_true', help='Open the measured V2/V3 comparison report instead of the saved experiment collection.')
    args = parser.parse_args()
    destination = URL
    if args.feedback_validation:
        if not (ROOT / 'frontend/artifacts/feedback-validation/index.html').is_file():
            raise RuntimeError('The measured comparison report has not been published yet.')
        destination = 'http://127.0.0.1:8000/artifacts/feedback-validation/index.html'
    if args.check_only:
        if not healthy():
            raise RuntimeError('The dashboard is not running.')
        print('Dashboard ready: ' + destination)
        return
    if not healthy():
        print('Starting the local dashboard...')
        folder = ROOT / 'results/presentation_demo_20261026'
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'dashboard-launch.log').open('a', encoding='utf-8') as logfile:
            subprocess.Popen([sys.executable, '-u', str(ROOT / 'serve_frontend.py'), '--no-browser'],
                             cwd=ROOT, stdin=subprocess.DEVNULL, stdout=logfile, stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(40):
            if healthy():
                break
            time.sleep(.5)
        else:
            raise RuntimeError('The dashboard did not start. Review results/presentation_demo_20261026/dashboard-launch.log.')
    print('Opening the measured V2/V3 comparison. No training is started.' if args.feedback_validation
          else 'Opening your three saved Full experiments. No training is started.')
    if args.no_browser or not webbrowser.open(destination):
        print('Open this address in your browser: ' + destination)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Could not open the presentation demos: ' + str(exc), file=sys.stderr)
        sys.exit(1)
