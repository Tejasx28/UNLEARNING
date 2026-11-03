"""Run the interrupted study recovery and remaining cases with persistent logs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'results/feedback_validation_20261027'


def status(stage, **details):
    payload = {'stage': stage, 'updated_at_utc': datetime.now(timezone.utc).isoformat(), **details}
    (STUDY / 'worker_status.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    tasks = [('RECOVERING_SAVED_CASE', 'scripts/recover_feedback_case.py', '--run'),
             ('RUNNING_MATCHED_CASES', 'scripts/validate_feedback_comparison.py', '--run'),
             ('BUILDING_MEASURED_REPORT', 'scripts/build_feedback_report.py')]
    try:
        with (STUDY / 'persistent_worker.log').open('a', encoding='utf-8') as output:
            for stage, script, *arguments in tasks:
                status(stage)
                output.write('\n' + stage + '\n')
                output.flush()
                subprocess.run([sys.executable, '-u', script, *arguments], cwd=ROOT,
                               stdout=output, stderr=subprocess.STDOUT, check=True)
        status('GPU_STUDY_AND_REPORT_COMPLETE', pending='Browser verification and final evidence manifest')
    except Exception as error:
        status('FAILED', error=repr(error))
        raise


if __name__ == '__main__':
    main()
