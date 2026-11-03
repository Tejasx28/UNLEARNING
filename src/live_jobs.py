"""Process-isolated local jobs, cancellation, persistent status and honest ETA ranges."""
import copy
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import statistics
import tempfile
import subprocess
import sys
import threading
import time
import uuid
from src.live_scoring_recheck import attach_recheck

ACTIVE = ('RUNNING', 'CANCELLING')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # OneDrive/virus scanners may briefly hold the destination open on Windows.
    # Unique temporary files avoid collisions; bounded retries handle sharing locks.
    handle, name = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False)
        for attempt in range(8):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(.025 * (attempt+1))
    finally:
        temp.unlink(missing_ok=True)


class JobBusy(Exception):
    def __init__(self, job):
        self.job = job


class LiveJobManager:
    def __init__(self, root, worker_command=None, storage=None):
        self.root = Path(root)
        self.storage = Path(storage) if storage else self.root/'results/live_jobs'
        self.jobs, self.processes = {}, {}
        self.lock = threading.RLock()
        python = self.root/'.venv/Scripts/python.exe'
        if not python.exists():
            python = self.root/'.venv/bin/python'
        self.command = worker_command or [str(python if python.exists() else sys.executable), '-u',
                                          str(self.root/'scripts/live_job_worker.py')]
        for path in self.storage.glob('*/job.json'):
            try:
                job = json.loads(path.read_text(encoding='utf-8'))
                if job['status'] in ACTIVE:
                    job.update(status='FAILED', error='The backend restarted before this run finished.',
                               end_time=time.time(), current_step='Interrupted by backend restart.')
                    write_json(path, job)
                self.jobs[job['job_id']] = job
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def _save(self, job):
        try:
            write_json(self.storage/job['job_id']/'job.json', job)
            job.pop('persistence_error', None)
        except OSError as exc:
            # A status file lock must not abort a healthy GPU worker or erase its
            # in-memory result. The UI can export it and report the storage issue.
            if not job.get('persistence_error'):
                self._log(job, 'Local status could not be saved. The run continues; export results when ready.')
            job['persistence_error'] = str(exc)

    @staticmethod
    def _log(job, line):
        job['logs'] = [*job['logs'], f'[{datetime.now().strftime("%H:%M:%S")}] {line}'][-120:]

    def launch(self, request):
        with self.lock:
            active = next((job for job in self.jobs.values() if job['status'] in ACTIVE), None)
            if active:
                raise JobBusy(self.status(active['job_id']))
            now = time.time()
            key = 'job_' + str(int(now*1000)) + '_' + uuid.uuid4().hex[:8]
            author = request['author']
            job = {'job_id': key, 'author_id': author['id'], 'author_name': author['name'],
                   'mode': request['mode'], 'status': 'RUNNING', 'stage': 'init', 'progress': 0,
                   'current_step': 'Loading the local model runtime…', 'logs': [], 'start_time': now,
                   'stage_started_at': now, 'stage_durations_seconds': {}, 'error': None, 'result': None,
                   'end_time': None, 'cancel_requested': False, 'discovery': None,
                   'settings': {key: request.get(key) for key in ('engine_version', 'method', 'priority', 'training_budget_seconds',
                                                             'fact_indices', 'retain_max_drop', 'retain_weight',
                                                             'retain_quality_max_drop')},
                   'source_kind': 'custom' if request.get('custom_entity') is not None else 'catalog'}
            self._log(job, 'Queued a genuine live experiment. The original model stays separate.')
            self._save(job)
            write_json(self.storage/key/'request.json', request)
            self.jobs[key] = job
            threading.Thread(target=self._run, args=(key,), daemon=True).start()
            return self.status(key)

    def _run(self, key):
        folder = self.storage/key
        try:
            with self.lock:
                job = self.jobs[key]
                if job['cancel_requested']:
                    self._finish(key, 'CANCELLED')
                    return
                process = subprocess.Popen([*self.command, str(folder/'request.json'), str(folder/'result.json')],
                    cwd=self.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    env={**os.environ, 'ATU_SUPERVISED_WORKER': '1'},
                    encoding='utf-8', errors='replace', bufsize=1,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.processes[key] = process
            with (folder/'execution.log').open('w', encoding='utf-8') as logfile:
                for line in process.stdout:
                    logfile.write(line); logfile.flush()
                    if line.startswith('ATU_EVENT '):
                        try:
                            event = json.loads(line[len('ATU_EVENT '):])
                        except ValueError:
                            continue
                        with self.lock:
                            job = self.jobs[key]
                            if event.get('type') == 'progress' and not job['cancel_requested']:
                                stage = event['stage']
                                if stage != job['stage']:
                                    elapsed = time.time() - job['stage_started_at']
                                    job['stage_durations_seconds'][job['stage']] = round(elapsed, 2)
                                    job.update(stage=stage, stage_started_at=time.time())
                                job.update(progress=max(0, min(100, event['progress'])), current_step=event['message'])
                            elif event.get('type') == 'discovery' and isinstance(event.get('report'), dict):
                                report = event['report']
                                if isinstance(report.get('facts'), list) and isinstance(report.get('entity'), dict):
                                    job['discovery'] = report
                                    self._log(job, 'Privacy discovery evidence is ready to inspect before unlearning finishes.')
                                    self._save(job)
                            else:
                                self._log(job, str(event.get('message', '')))
                    elif line.strip():
                        with self.lock:
                            self._log(self.jobs[key], line.strip()[:1500])
            code = process.wait()
            with self.lock:
                job = self.jobs[key]
                if job['cancel_requested']:
                    self._finish(key, 'CANCELLED')
                elif code == 0:
                    result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
                    if result.get('status') != 'COMPLETED' or not isinstance(result.get('attacks'), list):
                        raise ValueError(result.get('error', 'Worker returned an incomplete result.'))
                    job.update(result=result, progress=100)
                    self._finish(key, 'COMPLETED')
                else:
                    error_path = folder/'error.json'
                    error = json.loads(error_path.read_text(encoding='utf-8'))['error'] if error_path.exists() else f'Worker exited with code {code}. See the execution log.'
                    self._finish(key, 'FAILED', error)
        except Exception as exc:
            with self.lock:
                process = self.processes.get(key)
                if process and process.poll() is None:
                    process.kill(); process.wait()
                self._finish(key, 'CANCELLED' if self.jobs[key]['cancel_requested'] else 'FAILED', str(exc))
        finally:
            with self.lock:
                process = self.processes.pop(key, None)
                if process and process.poll() is None:
                    process.kill(); process.wait()
                if process:
                    if process.stdin: process.stdin.close()
                    if process.stdout: process.stdout.close()

    def _finish(self, key, status, error=None):
        job = self.jobs[key]
        now = time.time()
        job['stage_durations_seconds'][job['stage']] = round(now-job['stage_started_at'], 2)
        job.update(status=status, end_time=now, error=error,
                   current_step={'COMPLETED': 'Execution complete. Review the measured outcome.',
                                 'CANCELLED': 'Stopped. The GPU worker has exited.',
                                 'FAILED': 'Execution failed. Review the log.'}[status])
        if status == 'CANCELLED':
            job['result'] = None
        self._log(job, job['current_step'])
        self._save(job)

    def cancel(self, key):
        with self.lock:
            job = self.jobs.get(key)
            if job is None:
                raise KeyError(key)
            if job['status'] not in ACTIVE:
                return self.status(key)
            job.update(cancel_requested=True, status='CANCELLING', current_step='Stopping the GPU worker…')
            self._log(job, 'Stop requested. Waiting for the worker to exit before releasing the GPU slot.')
            self._save(job)
            process = self.processes.get(key)
            if process and process.poll() is None:
                process.terminate()
                def force_stop():
                    with self.lock:
                        if self.processes.get(key) is process and process.poll() is None:
                            process.kill()
                timer = threading.Timer(3, force_stop); timer.daemon = True; timer.start()
            return self.status(key)

    def _estimate(self, job, elapsed):
        if job['status'] not in ACTIVE or job['cancel_requested']:
            return None
        # An incomplete old record must not prevent a new launch or polling.
        # Only complete, finite timing observations enter the planning cohort.
        matching = []
        for old in self.jobs.values():
            settings = old.get('settings')
            indices = settings.get('fact_indices') if isinstance(settings, dict) else None
            start, end = old.get('start_time'), old.get('end_time')
            if (old.get('status') != 'COMPLETED' or old.get('mode') != job['mode']
                    or old.get('source_kind') != job['source_kind']
                    or not isinstance(indices, list)
                    or len(indices) != len(job['settings']['fact_indices'])
                    or any(settings.get(k) != job['settings'].get(k) for k in
                           ('engine_version', 'method', 'priority', 'training_budget_seconds'))
                    or any(isinstance(value, bool) or not isinstance(value, (int, float))
                           or not math.isfinite(value) for value in (start, end))
                    or end < start):
                continue
            matching.append(old)
        matching = sorted(matching, key=lambda old: old['start_time'])[-12:]
        if matching:
            total = statistics.median(old['end_time']-old['start_time'] for old in matching)
            low, high, source = total*.8, total*1.35, 'similar_completed_runs'
        else:
            # Explicit planning range, never presented as a measurement or deadline.
            count = len(job['settings']['fact_indices'])
            base = 90 + count*18 + (job['settings']['training_budget_seconds'] or (60 if job['mode'] == 'fast' else 600))*.65
            low, high, source = base*.65, base*1.7, 'planning_range'
        return {'remaining_low_seconds': round(max(0, low-elapsed)),
                'remaining_high_seconds': round(max(0, high-elapsed)),
                'over_estimate': elapsed > high, 'source': source, 'sample_count': len(matching)}

    def status(self, key):
        with self.lock:
            job = self.jobs.get(key)
            if job is None:
                raise KeyError(key)
            result = copy.deepcopy(job)
            now = job['end_time'] or time.time()
            elapsed = round(max(0, now-job['start_time']), 1)
            result.update(elapsed_seconds=elapsed,
                          stage_elapsed_seconds=round(max(0, now-job['stage_started_at']), 1),
                          estimate=self._estimate(job, elapsed),
                          created_at=datetime.fromtimestamp(job['start_time'], timezone.utc).isoformat())
            return attach_recheck(result, self.storage/key)

    def history(self):
        with self.lock:
            records = []
            for key in sorted(self.jobs, reverse=True):
                try:
                    records.append(self.status(key))
                except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
                    # Preserve the original file for inspection while allowing all
                    # readable records and live monitoring to remain accessible.
                    logging.getLogger(__name__).warning('Skipping incomplete job record %s: %s', key, exc)
            return records

    def shutdown(self):
        for job in self.history():
            if job['status'] in ACTIVE:
                self.cancel(job['job_id'])
