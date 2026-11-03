"""Recover one interrupted, fully saved V2 trial without repeating training.

Default: CPU-only integrity/response-score validation. --run explicitly loads
models on the GPU and evaluates the already selected checkpoint on held-out tests.
This narrowly supports a complete rollback whose saved adapter tensors exactly
equal the frozen original; it does not guess missing training or baseline data.
"""
import argparse
import copy
from datetime import datetime
from importlib.metadata import version
import logging
import math
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import torch
from safetensors import safe_open
import yaml

import validate_feedback_comparison as study
from src.atu.v3.data import retain_quality_scope
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.types import UnlearningRequest
from src.live_jobs import write_json
from src.metrics import compute_rouge_scores

DEFAULT_STUDY = ROOT / 'results/feedback_validation_20261027'
DEFAULT_RUN = DEFAULT_STUDY / 'runs/tofu-maria-lucia-sousa/v2/20261027_143243_00e07ec9'
AUTHOR = 'tofu-maria-lucia-sousa'
CONFIG_KEYS = ('lr', 'weight_decay', 'epochs', 'grad_accum_steps', 'beta', 'retain_weight',
    'length_normalize', 'base_floor_mean', 'base_floor_std', 'floor_buffer', 'stubborn_threshold',
    'stubborn_boost', 'leak_boost', 'suppressed_weight', 'standard_weight', 'retain_max_drop')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, message, absolute=1e-12):
    require(isinstance(actual, (int, float)) and not isinstance(actual, bool)
            and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=absolute), message)


def validate_frozen(folder):
    protocol = study.read(folder / 'frozen_protocol.json')
    require(protocol['study'] == 'feedback-comparison-20261027' and protocol['schema'] == 1,
            'Unexpected frozen study/schema.')
    require(study.source_hashes() == protocol['sources_sha256'], 'Frozen source/config hashes changed.')
    require(study.file_hash(study.TARGET / 'adapter_model.safetensors') == protocol['target_adapter_sha256'],
            'Original target adapter changed.')
    require(study.file_hash(study.TARGET / 'adapter_config.json') == protocol['target_config_sha256'],
            'Original target configuration changed.')
    require(study.file_hash(study.CATALOG) == protocol['catalog_sha256'], 'Frozen catalog changed.')
    for name, expected in protocol['runtime'].items():
        require(version(name) == expected, 'Frozen runtime version changed: ' + name)
    base = Path(protocol['base_model_source'])
    actual = {path.name: study.file_hash(path) for path in sorted(base.iterdir())
              if path.is_file() and path.suffix in ('.safetensors', '.bin', '.json', '.model', '.txt')}
    require(actual == protocol['base_model_files_sha256'], 'Frozen base model/tokenizer files changed.')
    requests, _, cohort = study.inputs()
    require({key: value.to_dict() for key, value in requests.items()} == protocol['requests'],
            'Current data/request preparation differs from frozen requests.')
    require(cohort == protocol['retain_cohort'], 'Frozen retain cohorts changed.')
    return protocol


def quality_from_saved(provenance, request):
    rows, fingerprint, token_cap = retain_quality_scope(request)
    kept = provenance['metrics']['details']['retain_quality_check']
    examples = kept.get('examples')
    require(isinstance(examples, list) and len(examples) == len(rows), 'Missing original retain responses.')
    originals = []
    for row, example in zip(rows, examples):
        require(example['question'] == row['question'] and example['reference_answer'] == row['answer'],
                'Saved retain response order/reference differs from frozen cohort.')
        require(isinstance(example['original_response'], str) and isinstance(example['response'], str),
                'Saved retain responses must be strings.')
        originals.append(example['original_response'])
    score = compute_rouge_scores(originals, [row['answer'] for row in rows])['rougeL']
    require(0 < score <= 1, 'Recovered original answer quality must be positive.')
    for label, quality in [('kept', kept), ('rejected', provenance['metrics']['details']
            .get('rejected_metrics', {}).get('details', {}).get('retain_quality_check'))]:
        require(isinstance(quality, dict) and quality.get('enabled') is True, label + ': missing quality record.')
        require(quality['metric'] == 'mean_rougeL_against_reference'
                and quality['cohort_sha256'] == fingerprint and quality['token_cap'] == token_cap
                and quality['sample_count'] == len(rows), label + ': quality scope mismatch.')
        close(quality['before'], score, label + ': original ROUGE-L does not recompute.')
        close(quality['limit'], request.retain_quality_max_drop, label + ': quality limit differs.')
        saved = quality['examples']
        require(len(saved) == len(rows), label + ': incomplete retained-answer evidence.')
        for row, original, example in zip(rows, originals, saved):
            require(example['question'] == row['question'] and example['reference_answer'] == row['answer']
                    and example['original_response'] == original and isinstance(example['response'], str),
                    label + ': inconsistent immutable baseline examples.')
        after = compute_rouge_scores([example['response'] for example in saved],
                                    [row['answer'] for row in rows])['rougeL']
        close(quality['after'], after, label + ': final ROUGE-L does not recompute.')
        drop = max(0., (score-after)/score)
        close(quality['relative_drop'], drop, label + ': quality decline does not recompute.')
        require(quality['passed'] is (drop <= request.retain_quality_max_drop + 1e-12),
                label + ': inconsistent quality pass flag.')
    return {'metric': 'mean_rougeL_against_reference', 'score': score, 'cohort_sha256': fingerprint,
            'sample_count': len(rows), 'token_cap': token_cap, 'rows': rows, 'responses': originals}


def verify_rollback_weights(checkpoint, provenance):
    detail = provenance['metrics']['details']
    require(provenance['status'] == 'ROLLED_BACK: unsafe trial' and detail.get('rolled_back') is True,
            'This helper requires a fully documented original-weight rollback.')
    require(detail.get('kept_checkpoint_changed') is False
            and detail.get('update_diagnostic') == 'UPDATES_ROLLED_BACK_OR_NO_EFFECT',
            'Saved trial does not identify a zero-change kept state.')
    for key in ('changed_trainable_tensors', 'changed_parameter_values', 'max_abs_parameter_delta', 'l2_parameter_delta'):
        close(detail[key], 0., 'Saved rollback parameter diagnostic is nonzero: ' + key)
    original_config = study.read(study.TARGET / 'adapter_config.json')
    saved_config = study.read(checkpoint / 'adapter_config.json')
    # PEFT records the load location and inference flag when serializing again;
    # all adapter architecture/weight interpretation fields must still match.
    for value in (original_config, saved_config):
        value.pop('base_model_name_or_path', None)
        value.pop('inference_mode', None)
        # PEFT stores matched module names as a set and can serialize them in
        # another order. Ordering does not change which tensors are adapted.
        if isinstance(value.get('target_modules'), list):
            value['target_modules'] = sorted(value['target_modules'])
    require(original_config == saved_config, 'Saved adapter architecture differs from original.')
    with safe_open(str(study.TARGET / 'adapter_model.safetensors'), framework='pt', device='cpu') as original, \
            safe_open(str(checkpoint / 'adapter_model.safetensors'), framework='pt', device='cpu') as saved:
        keys = list(original.keys())
        require(keys and set(keys) == set(saved.keys()), 'Saved adapter tensor names differ from original.')
        for key in keys:
            first, second = original.get_tensor(key), saved.get_tensor(key)
            require(first.dtype == second.dtype and torch.equal(first, second),
                    'Saved adapter differs from documented complete rollback: ' + key)
    return {'proof': 'Exact CPU tensor equality to the frozen original adapter after documented rollback.',
            'tensor_count': len(keys), 'checkpoint_sha256_now': study.file_hash(checkpoint / 'adapter_model.safetensors'),
            'historical_checkpoint_hash_available': False,
            'limitation': 'No checkpoint digest was saved before interruption; current hashes identify recovery inputs, not historical authentication.'}


def log_timing(folder, run, checkpoint):
    log_path = folder / 'execution.log'
    lines = log_path.read_text(encoding='utf-8').splitlines()
    stamp = datetime.strptime(run.name[:15], '%Y%m%d_%H%M%S')
    ends = []
    for line in lines:
        if 'Saved checkpoint and provenance to ' + str(checkpoint) in line:
            ends.append(datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S,%f'))
    require(len(ends) == 1, 'Need exactly one logged save event for the selected checkpoint.')
    end = ends[0]
    require(stamp < end, 'Checkpoint save precedes case directory timestamp.')
    return {'first_segment_start_estimate_local': stamp.isoformat(),
            'first_segment_checkpoint_saved_local': end.isoformat(),
            'first_segment_seconds_estimate': (end-stamp).total_seconds(),
            'first_segment_estimate_source': 'Second-resolution run-directory creation timestamp to recorded checkpoint save event; original monotonic start unavailable.',
            'interruption': 'Execution host stopped after checkpoint save while loading for final held-out evaluation.',
            'downtime_included': False, 'case_time_is_approximate': True,
            'fairness_note': 'Estimated active-segment sum includes recovery-only baseline/reload overhead and excludes downtime; do not use for a precise timing comparison.'}


def preflight(folder, run):
    require(folder.is_relative_to((ROOT / 'results').resolve()) and run.is_relative_to(folder / 'runs' / AUTHOR / 'v2'),
            'Recovery is restricted to this study Maria V2 case.')
    protocol = validate_frozen(folder)
    protocol_hash = study.digest(protocol)
    checkpoint = run / 'checkpoints/trial_1'
    provenance = study.read(checkpoint / 'provenance.json')
    expected = copy.deepcopy(protocol['requests'][AUTHOR])
    expected.update(method='atu_npo', max_trials=1, calibrate_forget_reference=False, forget_reference_log_probs=None)
    require(study.read(run / 'request.json') == expected, 'Saved native request differs from frozen V2 transformation.')
    native = UnlearningRequest(**expected)
    config = yaml.safe_load((ROOT / 'configs/atu_v2.yaml').read_text(encoding='utf-8'))
    config = {key: config[key] for key in CONFIG_KEYS}
    config['epochs'] = min(config['epochs'], native.max_epochs_per_trial)
    config['retain_weight'] = max(config['retain_weight'], native.retain_weight)
    require(provenance['config'] == config and provenance['trial_index'] == 1
            and provenance['method'] == 'atu_npo' and provenance['seed'] == protocol['seed'],
            'Saved trial does not match canonical V2 settings/seed.')
    detail = provenance['metrics']['details']
    require(isinstance(detail['optimizer_steps'], int) and 0 < detail['optimizer_steps'] <= native.max_total_steps
            and detail['optimizer_steps'] == detail['total_optimizer_steps_so_far'], 'Invalid saved optimizer-update count.')
    require(detail['development_probes_tested'] == len(native.dev_probes)
            and len(detail['probe_results']) == len(native.dev_probes), 'Incomplete saved development evidence.')
    for probe, measured in zip(native.dev_probes, detail['probe_results']):
        require(probe['id'] == measured['id'] and probe['prompt'] == measured['prompt']
                and probe['target_facts'] == measured['target_facts'], 'Saved trial probes differ from frozen development set.')
    control_path = folder / 'controls' / (AUTHOR + '.json')
    control = study.load_envelope(control_path, protocol_hash)
    require(control['generation_token_cap'] == native.eval_max_new_tokens, 'Control token cap differs.')
    for kind in ('target', 'base'):
        require(len(control[kind]) == len(native.test_probes), 'Incomplete original/base controls.')
        for probe, measured in zip(native.test_probes, control[kind]):
            require(all(probe[key] == measured[key] for key in ('id', 'prompt', 'target_facts', 'source_question'))
                    and isinstance(measured['response'], str), 'Controls differ from frozen held-out inputs.')
    baseline = quality_from_saved(provenance, native)
    weights = verify_rollback_weights(checkpoint, provenance)
    timing = log_timing(folder, run, checkpoint)
    artifacts = {str(path.relative_to(folder)): study.file_hash(path)
                 for path in [folder / 'frozen_protocol.json', folder / 'execution.log', control_path,
                              run / 'request.json', *sorted(checkpoint.iterdir())] if path.is_file()}
    return protocol, protocol_hash, native, control, baseline, provenance, checkpoint, weights, timing, artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly run GPU final evaluation; never repeat training.')
    parser.add_argument('--output', default=str(DEFAULT_STUDY))
    parser.add_argument('--run-directory', default=str(DEFAULT_RUN))
    args = parser.parse_args()
    folder, run = Path(args.output).resolve(), Path(args.run_directory).resolve()
    print('RECOVERY: validating frozen source, data, controls, saved quality and rollback weights (CPU).', flush=True)
    (protocol, protocol_hash, native, control, baseline, provenance, checkpoint, weights,
     timing, artifact_hashes) = preflight(folder, run)
    print(f'VALIDATED: {provenance["metrics"]["details"]["optimizer_steps"]} attempted updates; '
          f'original retain ROUGE-L={baseline["score"]:.16f}; complete rollback proven.', flush=True)
    destination = folder / 'cases' / f'{AUTHOR}_v2.json'
    if destination.exists():
        existing = study.load_envelope(destination, protocol_hash)
        require(existing.get('execution_status') == 'COMPLETED'
                and existing.get('author_id') == AUTHOR and existing.get('version') == 'v2'
                and existing.get('checkpoint') == str(checkpoint) and existing.get('run_directory') == str(run)
                and existing['selected_adapter_sha256'] == weights['checkpoint_sha256_now'],
                'An existing case is present but does not match this recovery; refusing overwrite.')
        print('Already completed; no additional evaluation or writes.', flush=True)
        return
    if not args.run:
        print('Dry validation complete. Use --run to evaluate this saved checkpoint on the GPU.', flush=True)
        return
    require(torch.cuda.is_available() and torch.cuda.get_device_name(0) == protocol['device'],
            'Recovery requires the same frozen local GPU.')
    reservation = study.reserve_dashboard_port()
    recovery_started = time.monotonic()
    recovery_dir = run / 'recoveries' / (time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    recovery_dir.mkdir(parents=True)
    logging.basicConfig(filename=recovery_dir / 'execution.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    def status(phase, **extra):
        write_json(recovery_dir / 'status.json', {'phase': phase, 'updated_local': datetime.now().isoformat(),
                   'active_recovery_seconds': round(time.monotonic()-recovery_started, 3), **extra})
        print('RECOVERY ' + phase, flush=True)
    try:
        status('RECOMPUTING_ORIGINAL_RETAIN_LIKELIHOODS')
        tokenizer = study.load_tokenizer(protocol['base_model_source'])
        audit_request = copy.deepcopy(native)
        audit_request.dev_probes, audit_request.test_probes = native.test_probes, None
        evaluator = TrialEvaluator(tokenizer, audit_request, device='cuda')
        model = study.load_model(protocol['base_model_source'])
        try:
            evaluator.initial_retain_lp = evaluator.measure_retain(model)
            evaluator.initial_retain_log_probs = list(evaluator.last_retain_log_probs)
        finally:
            del model; study.cleanup()
        require(all(math.isfinite(value) for value in evaluator.initial_retain_log_probs), 'Nonfinite original likelihoods.')
        close(round(evaluator.initial_retain_lp, 4), provenance['metrics']['details']['initial_retain_lp'],
              'Recomputed original retain likelihood differs from saved rounded baseline.')
        # Canonical V2 uses a global floor, so its original forget per-answer
        # reference stays None, exactly as in the frozen original run_v2.
        evaluator.initial_forget_log_probs = None
        evaluator.initial_retain_probe_results = None
        evaluator.initial_retain_quality = copy.deepcopy(baseline)
        evaluator.initial_probe_leak_rate = sum(row['verdict'] != 'NO_RECOVERY' or row['degenerate']
                                               for row in control['target']) / len(control['target'])
        evaluator._validated_quality_baseline(*evaluator._retain_quality_scope())
        write_json(recovery_dir / 'reconstructed_baselines.json', {
            'initial_retain_lp': evaluator.initial_retain_lp,
            'initial_retain_log_probs': evaluator.initial_retain_log_probs,
            'initial_forget_log_probs': None, 'initial_probe_leak_rate': evaluator.initial_probe_leak_rate,
            'initial_retain_quality': baseline,
            'source': 'Original retain likelihoods freshly recomputed; immutable quality from saved original responses with recomputed ROUGE-L; held-out original recovery from frozen controls.'})
        status('FINAL_HELD_OUT_EVALUATION')
        model = study.load_model(protocol['base_model_source'], checkpoint)
        try:
            final = evaluator.evaluate(model).to_dict()
        finally:
            del model; study.cleanup()
        status('CALIBRATING_AND_VERIFYING_OUTPUTS')
        audit = study.calibrated(control, final['details']['probe_results'], {row['question'] for row in native.forget_data})
        count = audit['counts']
        success = (final['is_safe'] and final['verdict'] == 'CONVERGED_SAFE' and count['validated'] > 0
                   and count['residual'] == 0 and count['facts_with_validated_checks'] == count['facts_requested'])
        outcome = 'SUCCESS' if success else 'PARTIAL_SUCCESS' if final['is_safe'] else 'FAILED'
        validate_frozen(folder)
        require(all(study.file_hash(folder / name) == value for name, value in artifact_hashes.items()),
                'A recovery input changed during final evaluation.')
        elapsed = time.monotonic()-recovery_started
        timing.update(recovery_active_seconds=round(elapsed, 3),
                      recovery_integrity_preflight_included=False,
                      recovery_active_scope='Measured processing after CPU integrity preflight and dashboard port reservation; includes original likelihood recomputation, model loads, final tests and output verification.',
                      original_trial_training_seconds=provenance['metrics']['details']['training_budget_used_seconds'],
                      no_retraining_performed=True)
        trial = {'trial_index': 1, 'method': 'atu_npo', 'config': provenance['config'],
                 'checkpoint_dir': str(checkpoint), 'metrics': provenance['metrics'], 'status': provenance['status'],
                 'adaptation_applied': provenance['adaptation'],
                 'duration_seconds': timing['first_segment_seconds_estimate'],
                 'duration_seconds_is_estimated': True,
                 'duration_note': 'Trial duration was not serialized; estimated from run-directory timestamp to checkpoint save log.'}
        recovery = {'schema': 1, 'recovery_directory': str(recovery_dir), 'timing': timing,
                    'source_helper_sha256': study.file_hash(Path(__file__)), 'input_artifacts_sha256_now': artifact_hashes,
                    'rollback_integrity': weights,
                    'scope': 'Reuse completed training/development provenance; only held-out final evaluation rerun. No final result influenced method, settings or checkpoint selection.'}
        result = {'author_id': AUTHOR, 'version': 'v2', 'seed': protocol['seed'], 'execution_status': 'COMPLETED',
                  'scientific_status': outcome, 'checkpoint': str(checkpoint), 'final_metrics': final,
                  'trials': [trial], 'native_status': provenance['status'], 'selected_method': 'atu_npo',
                  'floor_policy': 'canonical_global_floor', 'shared_quality_guard_added': True,
                  'optimizer_steps': provenance['metrics']['details']['optimizer_steps'], 'calibrated': audit,
                  'run_directory': str(run), 'selected_adapter_sha256': weights['checkpoint_sha256_now'],
                  'wall_seconds': round(timing['first_segment_seconds_estimate'] + elapsed, 2),
                  'wall_seconds_is_estimated': True, 'recovery': recovery}
        write_json(recovery_dir / 'result.json', result)
        write_json(run / 'result.json', result)
        study.save_envelope(destination, result, protocol_hash)
        study.summarize(folder)
        status('COMPLETED', scientific_status=outcome, case_path=str(destination))
        print(f'RECOVERED {AUTHOR} v2: {outcome}; {count["suppressed"]}/{count["validated"]} calibrated; '
              f'{count["residual"]} residual. Case time is approximate; interruption downtime excluded.', flush=True)
    except Exception as error:
        status('FAILED', error=repr(error))
        logging.exception('Recovery failed; original training/checkpoint preserved.')
        raise
    finally:
        original_after = study.file_hash(study.TARGET / 'adapter_model.safetensors')
        write_json(recovery_dir / 'original_target_verification.json', {
            'before': protocol['target_adapter_sha256'], 'after': original_after,
            'preserved': original_after == protocol['target_adapter_sha256']})
        reservation.close()
        study.cleanup()
        require(original_after == protocol['target_adapter_sha256'], 'Original adapter changed during recovery.')


if __name__ == '__main__':
    main()
