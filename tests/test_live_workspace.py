import json
from pathlib import Path
import sys
import time
import subprocess
import os

import pytest
from src.live_jobs import LiveJobManager, JobBusy, write_json
from src.live_requests import normalize_launch, select_fact_indices, custom_author, validate_options

ROOT = Path(__file__).resolve().parents[1]
CATALOG = {'authors': [{'id': 'author', 'name': 'Alice', 'qa': [
    {'question': f'Question {i}', 'answer': f'Answer {i}'} for i in range(20)]}]}


def test_selected_facts_are_exact_original_indices_and_input_is_not_mutated():
    result = normalize_launch({'author_id': 'author', 'fact_indices': [17, 2], 'mode': 'full',
        'priority': 'preserve_utility', 'training_budget_seconds': 90}, CATALOG)
    assert result['fact_indices'] == [2, 17]
    assert result['priority'] == 'preserve_utility' and result['training_budget_seconds'] == 90
    assert len(result['author']['qa']) == 20
    for indices in ([], [1, 1], [True], [-1], [20], list(range(6))):
        with pytest.raises(ValueError): select_fact_indices(CATALOG['authors'][0], 'fast', indices)


@pytest.mark.parametrize('options', [{'mode': 'unknown'}, {'priority': 'unknown'},
    {'training_budget_seconds': float('nan')}, {'training_budget_seconds': 0},
    {'retain_max_drop': float('inf')}, {'retain_weight': 'bad'}, {'engine_version': 'v2', 'priority': 'fast'}])
def test_invalid_settings_are_rejected_before_gpu_start(options):
    with pytest.raises(ValueError): validate_options(**options)


def test_custom_candidates_have_safe_stable_identity_and_real_questions():
    payload = {'name': '../Custom entity', 'facts': [{'attribute': 'birthplace', 'value': 'Brussels'},
              {'attribute': 'job', 'value': 'Writer', 'question': 'What work did this entity do?'}]}
    author = custom_author(payload)
    assert author['id'].startswith('custom-') and '/' not in author['id']
    assert author == custom_author(payload)
    assert author['qa'][0] == {'question': 'What is the birthplace of ../Custom entity?', 'answer': 'Brussels'}
    request = normalize_launch({'custom_entity': payload, 'fact_indices': [1]}, CATALOG)
    assert request['author'] == author and request['fact_indices'] == [1]
    with pytest.raises(ValueError): normalize_launch({'author_id': 'author', 'custom_entity': payload}, CATALOG)
    with pytest.raises(ValueError): normalize_launch({'author_id': 'author', 'mock': True}, CATALOG)


def manager(tmp_path):
    return LiveJobManager(ROOT, worker_command=[sys.executable, '-u', str(ROOT/'tests/fixtures/live_worker_fixture.py')], storage=tmp_path/'jobs')


def request(name='Alice'):
    value = normalize_launch({'author_id': 'author', 'fact_indices': [3]}, CATALOG)
    value['author'] = {**value['author'], 'name': name}
    return value


def wait_terminal(jobs, key, timeout=15):
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        job = jobs.status(key)
        if job['status'] not in ('RUNNING', 'CANCELLING'):
            return job
        time.sleep(.03)
    pytest.fail('Child job did not finish')


def test_real_child_transport_persists_results_and_terminal_elapsed_freezes(tmp_path):
    jobs = manager(tmp_path)
    first = jobs.launch(request())
    assert first['status'] == 'RUNNING' and first['estimate']['source'] == 'planning_range'
    done = wait_terminal(jobs, first['job_id'])
    assert done['status'] == 'COMPLETED' and done['result']['unlearning_status'] == 'UNVERIFIED'
    assert done['stage_durations_seconds'] and done['estimate'] is None
    assert done['discovery']['checkpoint_hash'] == 'CPU_TEST_ONLY'
    time.sleep(.15)
    assert jobs.status(first['job_id'])['elapsed_seconds'] == done['elapsed_seconds']
    restored = manager(tmp_path)
    assert restored.status(first['job_id'])['result'] == done['result']
    assert restored.status(first['job_id'])['discovery'] == done['discovery']
    second = jobs.launch(request('SLOW'))
    assert second['estimate']['source'] == 'similar_completed_runs'
    jobs.cancel(second['job_id']); wait_terminal(jobs, second['job_id'])


def test_cancellation_terminates_owned_child_and_gpu_slot_stays_locked_until_exit(tmp_path):
    jobs = manager(tmp_path)
    job = jobs.launch(request('SLOW')); key = job['job_id']
    with pytest.raises(JobBusy): jobs.launch(request())
    until = time.monotonic()+5
    while key not in jobs.processes and time.monotonic() < until: time.sleep(.01)
    process = jobs.processes[key]
    stopping = jobs.cancel(key)
    assert stopping['status'] in ('CANCELLING', 'CANCELLED')
    done = wait_terminal(jobs, key)
    assert done['status'] == 'CANCELLED' and done['result'] is None and process.poll() is not None
    assert jobs.cancel(key)['status'] == 'CANCELLED'
    next_job = jobs.launch(request())
    assert wait_terminal(jobs, next_job['job_id'])['status'] == 'COMPLETED'


def test_worker_failure_is_saved_and_never_looks_successful(tmp_path):
    jobs = manager(tmp_path); job = jobs.launch(request('FAIL'))
    done = wait_terminal(jobs, job['job_id'])
    assert done['status'] == 'FAILED' and done['error'] == 'CPU fixture failure'
    assert done['result'] is None
    with pytest.raises(KeyError): jobs.cancel('missing')


def test_restart_marks_unfinished_job_failed_instead_of_polling_forever(tmp_path):
    folder = tmp_path/'jobs/old'; folder.mkdir(parents=True)
    (folder/'job.json').write_text(json.dumps({'job_id': 'old', 'status': 'RUNNING'}))
    jobs = manager(tmp_path)
    assert jobs.jobs['old']['status'] == 'FAILED'


def test_calibration_cohort_is_independent_of_new_live_job_folders(monkeypatch):
    from scripts import calibrate_atu_v3 as study
    before = study.data_split()
    monkeypatch.setattr(Path, 'glob', lambda *a: iter([Path('live_unlearn_unrelated_new_entity')]))
    after = study.data_split()
    assert before == after


def test_worker_cannot_outlive_its_parent_pipe(tmp_path):
    path = tmp_path/'request.json'; path.write_text(json.dumps(request()))
    result = tmp_path/'result.json'
    child = subprocess.Popen([sys.executable, str(ROOT/'scripts/live_job_worker.py'), str(path), str(result)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env={**os.environ, 'ATU_SUPERVISED_WORKER': '1'})
    child.stdin.close()
    assert child.wait(timeout=10) == 2
    child.stdout.close()
    assert not result.exists()


def test_supervised_runtime_import_does_not_deadlock_with_parent_pipe_open(tmp_path):
    # This reproduces the real Windows hang: a blocking stdin watchdog held the
    # CRT file lock while NumPy's extension initialized. No GPU model is loaded.
    code = ('from src.worker_runtime import start_parent_watchdog; '
            'start_parent_watchdog(); import src.orchestrator.live_runner; print("RUNTIME_READY", flush=True)')
    child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        assert child.wait(timeout=60) == 0
        assert b'RUNTIME_READY' in child.stdout.read()
    finally:
        if child.poll() is None: child.kill(); child.wait()
        child.stdin.close(); child.stdout.close()


def test_atomic_save_retries_transient_windows_sharing_locks(tmp_path, monkeypatch):
    replace = os.replace
    calls = []
    def locked_once(source, target):
        calls.append(source)
        if len(calls) < 3: raise PermissionError('temporary OneDrive sharing lock')
        replace(source, target)
    monkeypatch.setattr(os, 'replace', locked_once)
    path = tmp_path/'job.json'
    write_json(path, {'status': 'COMPLETED'})
    assert json.loads(path.read_text()) == {'status': 'COMPLETED'}
    assert len(calls) == 3 and not list(tmp_path.glob('*.tmp'))


def test_status_save_failure_cannot_turn_completed_worker_into_failure(tmp_path, monkeypatch):
    import src.live_jobs as module
    jobs = manager(tmp_path)
    save = module.write_json
    def locked_status(path, value):
        if Path(path).name == 'job.json': raise PermissionError('persistent sharing lock')
        save(path, value)
    monkeypatch.setattr(module, 'write_json', locked_status)
    job = jobs.launch(request())
    done = wait_terminal(jobs, job['job_id'])
    assert done['status'] == 'COMPLETED' and done['result'] is not None
    assert 'sharing lock' in done['persistence_error']


def test_cancellation_preserves_measured_discovery_without_completed_result(tmp_path):
    jobs = manager(tmp_path); job = jobs.launch(request('SLOW')); key = job['job_id']
    until = time.monotonic()+10
    while not jobs.status(key).get('discovery') and time.monotonic() < until: time.sleep(.03)
    assert jobs.status(key)['discovery']
    jobs.cancel(key)
    done = wait_terminal(jobs, key)
    assert done['result'] is None and done['discovery']['checkpoint_hash'] == 'CPU_TEST_ONLY'
    assert manager(tmp_path).status(key)['discovery'] == done['discovery']
