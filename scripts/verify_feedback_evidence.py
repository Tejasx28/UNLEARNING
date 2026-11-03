"""Verify the completed feedback study and write its evidence manifest (no GPU)."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'results/feedback_validation_20261027'


def read(path):
    return path.read_text(encoding='utf-8')


def data(path):
    return json.loads(read(path))


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def object_hash(value):
    serialized = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def main():
    protocol = data(STUDY / 'frozen_protocol.json')
    expected = {(author, version) for author in protocol['authors'] for version in protocol['versions']}
    comparison = data(STUDY / 'comparison.json')
    assert comparison['completed'] == len(expected) == len(comparison['rows']) == 4
    assert {(row['author'], row['version']) for row in comparison['rows']} == expected
    changed_sources = [name for name, digest in protocol['sources_sha256'].items()
                       if file_hash(ROOT / name) != digest]
    assert not changed_sources, f'Frozen sources changed: {changed_sources}'
    original = data(STUDY / 'original_target_verification.json')
    target_hash = file_hash(ROOT / 'checkpoints/target_tofu_lora/adapter_model.safetensors')
    assert original['preserved'] is True
    assert original['before'] == original['after'] == target_hash == protocol['target_adapter_sha256']
    cases = []
    for author, version in sorted(expected):
        name = f'{author}_{version}.json'
        envelope = data(STUDY / 'cases' / name)
        result = envelope['payload']
        assert envelope['protocol_sha256'] == object_hash(protocol)
        assert envelope['payload_sha256'] == object_hash(result)
        assert result['execution_status'] == 'COMPLETED'
        assert (result['author_id'], result['version']) == (author, version)
        checkpoint = Path(result['checkpoint']) / 'adapter_model.safetensors'
        assert file_hash(checkpoint) == result['selected_adapter_sha256']
        published = ROOT / 'frontend/artifacts/feedback-validation' / name
        assert file_hash(published) == file_hash(STUDY / 'cases' / name)
        cases.append({'author': author, 'version': version,
                      'scientific_status': result['scientific_status'],
                      'calibrated_counts': result['calibrated']['counts'],
                      'optimizer_steps': result['optimizer_steps'],
                      'checkpoint_sha256': result['selected_adapter_sha256']})
    suites = ET.parse(STUDY / 'python-tests.xml').getroot().findall('.//testsuite')
    tests = {key: sum(int(suite.get(key, 0)) for suite in suites)
             for key in ('tests', 'failures', 'errors', 'skipped')}
    assert tests == {'tests': 319, 'failures': 0, 'errors': 0, 'skipped': 0}
    live = data(STUDY / 'live_api/verification.json')
    assert live['genuine_full_gpu_execution'] is True
    assert live['quality_limit'] == .02 and live['quality_relative_drop'] == 0
    assert live['suppressed'] == live['validated'] == 2 and live['residual'] == 0
    assert live['original_target_preserved'] is True and live['selected_adapter_changed'] is True
    screenshots = {}
    for name in ('live-quality.png', 'comparison.png'):
        path = STUDY / 'screenshots' / name
        assert path.stat().st_size > 1000
        screenshots[name] = file_hash(path)
    report = ROOT / 'frontend/artifacts/feedback-validation/index.html'
    assert report.exists() and '{{TABLE_ROWS}}' not in read(report) and '{{CASE_EVIDENCE}}' not in read(report)
    verification = {'completed': True, 'frozen_sources_unchanged': True,
                    'original_target_preserved': True, 'original_target_sha256': target_hash,
                    'protocol_sha256': object_hash(protocol), 'python_tests': tests,
                    'frontend_tests_passed': live['frontend_tests_passed'],
                    'typescript_and_build': live['typescript_and_build'],
                    'live_api': live, 'matched_gpu_cases': cases,
                    'screenshots_sha256': screenshots, 'published_report_sha256': file_hash(report),
                    'scope': 'Two selected stress cases, one seed; no universal superiority claim.'}
    (STUDY / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n', encoding='utf-8')
    worker_status = data(STUDY / 'worker_status.json')
    worker_status.update(stage='VERIFIED_COMPLETE', pending=None,
                         updated_at_utc=datetime.now(timezone.utc).isoformat())
    (STUDY / 'worker_status.json').write_text(json.dumps(worker_status, indent=2) + '\n', encoding='utf-8')
    print('Verified: 4 matched GPU cases, live API evidence, original/source hashes, tests and published screenshots.')


if __name__ == '__main__':
    main()
