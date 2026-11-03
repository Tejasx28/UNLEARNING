"""One real job per child process: termination releases its CUDA context."""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def event(kind, **values):
    print('ATU_EVENT ' + json.dumps({'type': kind, **values}), flush=True)


def main():
    request_path, result_path = map(Path, sys.argv[1:3])
    try:
        if os.environ.get('ATU_SUPERVISED_WORKER') == '1':
            from src.worker_runtime import start_parent_watchdog
            start_parent_watchdog()
        request = json.loads(request_path.read_text(encoding='utf-8'))
        event('progress', progress=1, stage='init', message='Preparing PyTorch and the local GPU runtime…')
        import torch
        event('progress', progress=2, stage='init', message='PyTorch ready. Preparing model and tokenizer libraries…')
        import transformers
        event('progress', progress=3, stage='init', message='Model libraries ready. Preparing discovery and unlearning…')
        from src.orchestrator.live_runner import run_live_unlearning
        from src.live_jobs import write_json
        result = run_live_unlearning(author_query=request['author']['id'], mode=request['mode'],
            engine_version=request['engine_version'], retain_max_drop=request['retain_max_drop'],
            retain_weight=request['retain_weight'], custom_entity=request.get('custom_entity'),
            retain_quality_max_drop=request.get('retain_quality_max_drop'),
            fact_indices=request['fact_indices'], method=request.get('method', 'auto'), priority=request['priority'] if request['engine_version'] == 'v3' else None,
            training_budget_seconds=request['training_budget_seconds'] if request['engine_version'] == 'v3' else None,
            log_callback=lambda message: event('log', message=message),
            discovery_callback=lambda report: event('discovery', report=report),
            progress_callback=lambda progress, stage, message: event('progress', progress=progress, stage=stage, message=message))
        write_json(result_path, result)
        if result.get('status') != 'COMPLETED':
            raise RuntimeError(result.get('error', 'Live execution did not complete.'))
    except Exception as exc:
        # Keep the error path useful even if heavy runtime imports fail.
        error_path = result_path.parent/'error.json'
        error_path.write_text(json.dumps({'error': str(exc)}), encoding='utf-8')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
