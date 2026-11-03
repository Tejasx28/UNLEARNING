"""Attach explicitly versioned response rechecks without altering original runs."""
import hashlib
import json
from pathlib import Path
from src.leak_matching import SCORING_REVISION


def result_digest(result):
    return hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def attach_recheck(job, folder):
    """The caller supplies a copy; raw job/result files remain the source record."""
    if not job.get('result'):
        return job
    try:
        check = json.loads((Path(folder)/'scoring_recheck.json').read_text(encoding='utf-8'))
        if (check['scoring_revision'] == SCORING_REVISION
                and check['original_result_sha256'] == result_digest(job['result'])
                and isinstance(check['result']['attacks'], list)):
            job['result'] = check['result']
    except (OSError, KeyError, TypeError, ValueError):
        pass
    return job
