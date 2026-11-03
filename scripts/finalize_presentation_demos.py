"""Verify fresh Full-demo artifacts and write a presentation handoff.

Reads stored measurements without rescoring responses or changing outcomes.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'results/presentation_demo_20261026'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def duration(value):
    total = round(float(value))
    return f'{total // 60}m {total % 60:02d}s'


def main():
    plan, state = read(FOLDER / 'plan.json'), read(FOLDER / 'state.json')
    assert len(state['cases']) == 3, 'All three demos must finish first.'
    assert state.get('original_target_preserved') is True, 'Original adapter preservation has not been verified.'
    assert sha(Path(state['target_adapter'])) == state['original_target_sha256'], 'Original adapter changed.'
    rows, checks, walkthrough = [], [], []
    for case in plan['cases']:
        record = next(row for row in state['cases'] if row['id'] == case['id'])
        assert record['status'] == 'COMPLETED', f"{case['id']} has not completed successfully as an execution."
        folder = FOLDER / case['id']
        job = record['job']
        result, actual = read(folder / 'result.json'), read(folder / 'request.json')
        provenance, audit = result['provenance'], result['audit']
        assert job['job_id'] == record['job_id']
        assert job['mode'] == actual['mode'] == provenance['mode'] == 'full'
        assert actual['engine_version'] == provenance['engine_version'] == 'v3'
        assert provenance['evaluation_scope'] == 'full_experiment'
        assert provenance['final_audit'] == 'engine_heldout_and_calibrated_live_audit'
        assert provenance['device'] == 'cuda'
        for key in ('method', 'priority', 'training_budget_seconds', 'fact_indices', 'retain_max_drop', 'retain_weight'):
            assert actual[key] == case['request'][key], (case['id'], key)
        assert provenance['selected_fact_indices'] == actual['fact_indices']
        assert audit['retain_utility_examples'] == 25
        assert audit['total_attacks'] == len(result['attacks'])
        assert audit['validated_attacks'] + audit['inconclusive_attacks'] == audit['total_attacks']
        assert audit['verified_suppressions'] + audit['residual_leaks'] == audit['validated_attacks']
        assert audit['facts_requested'] == len(actual['fact_indices'])
        assert job['start_time'] >= state['created_at'] - 1
        adapter = Path(provenance['unlearned_adapter']) / 'adapter_model.safetensors'
        assert adapter.is_file() and adapter.stat().st_size > 0
        trials = result['v3']['trials']
        details = [trial['metrics']['details'] for trial in trials]
        steps = sum(int(d.get('optimizer_steps', 0)) for d in details)
        assert steps > 0, f"{case['id']} performed no optimizer updates."
        selected_hash = sha(adapter)
        valid_pairs = all(pair.get('before') and pair.get('base') for pair in result['attacks'])
        assert valid_pairs, f"{case['id']} is missing paired model controls."
        elapsed = job['end_time'] - job['start_time']
        selected = result['v3'].get('best_method', '')
        row = {'demo': case['id'], 'author': job['author_name'], 'job_id': job['job_id'],
               'mode': 'full', 'requested_method': actual['method'], 'selected_method': selected,
               'outcome': result['unlearning_status'], 'facts_requested': audit['facts_requested'],
               'facts_with_validated_checks': audit['facts_with_validated_checks'],
               'suppressed_checks': audit['verified_suppressions'], 'calibrated_checks': audit['validated_attacks'],
               'residual_recoveries': audit['residual_leaks'], 'inconclusive_checks': audit['inconclusive_attacks'],
               'retain_answer_overlap': audit['retain_utility_rate'], 'retain_examples': 25,
               'trials': len(trials), 'optimizer_updates_all_trials': steps,
               'wall_seconds': round(elapsed, 2), 'training_budget_seconds': actual['training_budget_seconds'],
               'selected_adapter': str(adapter), 'selected_adapter_sha256': selected_hash}
        rows.append(row)
        checks.append({'demo': case['id'], 'job_id': record['job_id'], 'fresh_full_gpu_run': True,
                       'request_matches_plan': True, 'full_evaluation_preserved': True,
                       'real_optimizer_updates': steps, 'all_paired_controls_present': valid_pairs,
                       'selected_adapter_present': True, 'selected_differs_from_original': selected_hash != state['original_target_sha256'],
                       'trials': [{'method': t['method'], 'updates': d.get('optimizer_steps'),
                                   'update_diagnostic': d.get('update_diagnostic'),
                                   'changed_parameter_values': d.get('changed_parameter_values'),
                                   'safe': t['metrics']['is_safe']} for t, d in zip(trials, details)]})
        questions = '\n'.join('- ' + q for q in provenance['selected_questions'])
        walkthrough.append(f"### {case['id'][-2:]}. {case['title']}\n\n"
            f"**{job['author_name']}** · `{record['job_id']}` · {duration(elapsed)}\n\n"
            f"{case['purpose']}\n\nSelected reference questions:\n\n{questions}\n\n"
            f"Measured outcome: **{audit['verified_suppressions']}/{audit['validated_attacks']} calibrated checks suppressed**, "
            f"{audit['residual_leaks']} residual recoveries, {audit['inconclusive_attacks']} inconclusive checks. "
            f"Validated coverage: {audit['facts_with_validated_checks']}/{audit['facts_requested']} selected facts. "
            f"Retain answer overlap: {audit['retain_utility_rate']:.1%} on 25 unrelated examples.\n\n"
            f"Actual methods: {', '.join(t['method'] for t in trials)}. Selected method: {selected}. "
            f"Recorded optimizer updates across trials: {steps}. Outcome label: `{result['unlearning_status']}`.\n\n"
            f"Evidence: [{case['id']}](./{case['id']}/result.json), [execution log](./{case['id']}/execution.log).\n")
    with (FOLDER / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    sources = [ROOT / p for p in ['src/live_requests.py', 'src/live_jobs.py', 'src/orchestrator/live_runner.py',
                                  'src/atu/controller.py', 'src/atu/trainer.py', 'scripts/live_job_worker.py']]
    sources.extend(sorted((ROOT / 'src/atu/v3').glob('*.py')))
    verification = {'verified_at': datetime.now(timezone.utc).isoformat(), 'collection_id': plan['collection_id'],
                    'original_target_preserved': True, 'original_target_sha256': state['original_target_sha256'],
                    'cases': checks, 'code_sha256_at_handoff': {str(p.relative_to(ROOT)): sha(p) for p in sources},
                    'boundary': 'Artifact and protocol verification only. Stored model measurements are preserved without rescoring. '
                                'Presentation cases were selected using prior observations, not a random benchmark.'}
    (FOLDER / 'verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
    content = '# ATU presentation demos\n\n'
    content += 'Three new Full GPU experiments, with real updates, saved adapters and paired original/base controls.\n\n'
    content += '**Open:** double-click `OPEN_PRESENTATION_DEMOS.bat` in the project root, or visit '
    content += '[Presentation demos](http://127.0.0.1:8000/#presentation-demos) while the dashboard is running. '
    content += 'Opening a completed demo does not start training.\n\n'
    content += '| Demo | Author | Suppressed / calibrated checks | Residual | Retain overlap | Runtime |\n'
    content += '|---|---|---:|---:|---:|---:|\n'
    for row in rows:
        content += f"| {row['demo']} | {row['author']} | {row['suppressed_checks']}/{row['calibrated_checks']} | {row['residual_recoveries']} | {row['retain_answer_overlap']:.1%} | {duration(row['wall_seconds'])} |\n"
    content += '\n## How to present\n\n'
    content += '1. Open **Presentation demos** and select **Present evidence** on a completed case.\n'
    content += '2. Show the selected author and exact facts. These are fictional TOFU benchmark profiles.\n'
    content += '3. Show discovery, distinguishing stored reference answers from generated model exposure.\n'
    content += '4. Show identical before/after prompts and inspect original-target/base-model controls.\n'
    content += '5. Explain actual optimizer updates, automatic trial decisions and retain measurements.\n'
    content += '6. Finish with coverage, residual/inconclusive checks and the exported provenance.\n\n'
    content += 'Use the existing presentation chapter controls or arrow keys to move through evidence. '
    content += 'Exit returns to the collection. **Inspect report** opens the complete measured result.\n\n'
    content += '\n'.join(walkthrough)
    content += '\n## Scope to explain honestly\n\n'
    content += '- Full mode includes the separate held-out engine evaluation and calibrated live audit. Each request used a 600-second shared training-loop ceiling and the default 0.03 retain limit. Early convergence can stop training before that ceiling.\n'
    content += '- Each recovery check is a prompt, not a separate forgotten fact. Multiple checks can concern one selected fact.\n'
    content += '- Suppression of the target answer can produce an incorrect replacement. Inspect raw answers and do not equate suppression with truthfulness.\n'
    content += '- Retain answer overlap is a sample measurement, not the percentage of all knowledge preserved. Unselected facts about the same author are not established by this retain sample.\n'
    content += '- Automatic mode may stop after the first safe converged method. It does not need to force a fallback to demonstrate correct operation.\n'
    content += '- These are selected presentation cases, not an unbiased benchmark or a claim of complete deletion.\n'
    content += '- The original target adapter hash is unchanged. All three selected adapters, settings, logs and outcomes are preserved.\n\n'
    content += 'See [summary.csv](./summary.csv), [verification.json](./verification.json), '
    content += '[collection.json](./collection.json) and each case folder for inspectable evidence.\n'
    (FOLDER / 'README.md').write_text(content, encoding='utf-8')
    (ROOT / 'PRESENTATION_DEMO.md').write_text('# Open your presentation demos\n\n'
        'Double-click **OPEN_PRESENTATION_DEMOS.bat** in this folder. It opens the completed experiment collection without starting new training.\n\n'
        '[Open the demo collection](http://127.0.0.1:8000/#presentation-demos)\n\n'
        '[Read the measured results and presentation walkthrough](results/presentation_demo_20261026/README.md)\n', encoding='utf-8')
    print(json.dumps({'verified_cases': len(checks), 'original_target_preserved': True,
                      'summary': [{k: row[k] for k in ('demo', 'author', 'outcome', 'suppressed_checks', 'calibrated_checks', 'residual_recoveries')} for row in rows]}))


if __name__ == '__main__':
    main()
