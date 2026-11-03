"""Exploratory response-level utility audit; never changes primary study decisions."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def select_rows(catalog, requests, excluded):
    used = {row['question'] for req in requests for field in
            ('forget_data', 'retain_data', 'retain_validation_data') for row in (req.get(field) or [])}
    pool = [a for a in catalog['authors'] if a['id'] not in excluded
            and a['name_status'] == 'IN_DATASET'
            and not any(row['question'] in used for row in a['qa'])]
    random.Random(8675309).shuffle(pool)
    selected = []
    for author in pool:
        name = author['name'].casefold()
        for index, row in enumerate(author['qa']):
            if name not in row['question'].casefold() and name in row['answer'].casefold():
                selected.append({'author_id': author['id'], 'author_name': author['name'],
                                 'qa_index': index, **row})
                break
        if len(selected) == 4:
            break
    if len(selected) < 4:
        raise ValueError('Not enough independent utility authors.')
    return selected


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temp.replace(path)


def prepare(folder):
    primary = json.loads((folder/'frozen_protocol.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT/'frontend/artifacts/tofu_catalog.json').read_text(encoding='utf-8'))
    requests = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder/'requests').glob('*.json'))]
    protocol = {
        'scope': 'Exploratory secondary audit; four fresh retain authors and two generic questions; no policy tuning',
        'selection_seed': 8675309, 'generation_cap': 48,
        'rows': select_rows(catalog, requests, primary['authors'] + ['tofu-basil-mahfouz-al-kuwaiti']),
        'generic_questions': [{'question': 'What is the capital of France?', 'keyword': 'Paris'},
                              {'question': 'Who wrote Romeo and Juliet?', 'keyword': 'Shakespeare'}],
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'primary_protocol_sha256': hashlib.sha256((folder/'frozen_protocol.json').read_bytes()).hexdigest(),
    }
    path = folder/'utility_audit/protocol.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != protocol:
            raise RuntimeError('Secondary audit inputs changed; preserve the existing audit separately.')
    else:
        write(path, protocol)
    return protocol


def execute(folder):
    protocol = prepare(folder)
    cases = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder/'cases').glob('heldout_*.json'))]
    if len(cases) != 18 or any('error' in c for c in cases):
        raise RuntimeError('Finish all primary comparison cases before the secondary audit.')
    import torch
    from src.models import load_tokenizer
    from src.metrics import generate_answers, compute_rouge_scores
    from scripts.compare_atu_versions import load, cleanup, MODEL, TARGET
    if not torch.cuda.is_available():
        raise RuntimeError('The saved-checkpoint audit requires the local GPU.')
    tokenizer = load_tokenizer(MODEL)

    def audit(adapter):
        model = load(adapter, trainable=False)
        try:
            answers = generate_answers(model, tokenizer, [r['question'] for r in protocol['rows']],
                                       max_new_tokens=protocol['generation_cap'], device='cuda')
            generic = generate_answers(model, tokenizer, [r['question'] for r in protocol['generic_questions']],
                                       max_new_tokens=25, device='cuda')
            return {
                'retain_rougeL': compute_rouge_scores(answers, [r['answer'] for r in protocol['rows']])['rougeL'],
                'retain_name_accuracy': sum(r['author_name'].casefold() in a.casefold()
                    for r,a in zip(protocol['rows'], answers))/len(answers),
                'generic_keyword_accuracy': sum(r['keyword'].casefold() in a.casefold()
                    for r,a in zip(protocol['generic_questions'], generic))/len(generic),
                'retain_responses': [dict(r, response=a) for r,a in zip(protocol['rows'], answers)],
                'generic_responses': [dict(r, response=a) for r,a in zip(protocol['generic_questions'], generic)],
            }
        finally:
            model = None
            cleanup()

    baseline_path = folder/'utility_audit/original_target.json'
    if not baseline_path.exists():
        print('UTILITY original target', flush=True)
        write(baseline_path, audit(TARGET))
    results = []
    for c in cases:
        path = folder/'utility_audit'/f"{c['author']}_{c['seed']}_{c['version']}.json"
        if not path.exists():
            print(f"UTILITY {c['author']} seed={c['seed']} {c['version']}", flush=True)
            result = audit(c['checkpoint'])
            result.update(author=c['author'], seed=c['seed'], version=c['version'])
            write(path, result)
        results.append(json.loads(path.read_text(encoding='utf-8')))
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    import statistics
    summary = {'baseline': baseline, 'scope': protocol['scope'], 'cases': results}
    lines = ['# Exploratory response-level utility audit', '',
        'This secondary audit was specified after observing early primary results. It does not select methods, tune settings, or change the registered primary outcomes. Four new retain authors were selected by a fixed random seed, excluding all forget, retain-training, and retain-validation authors. Two generic keyword checks are only examples, not a general capability benchmark.', '',
        '| Version | Fresh retain ROUGE-L | Fresh author-name accuracy | Two-question keyword accuracy |',
        '|---|---:|---:|---:|',
        f"| Original target | {baseline['retain_rougeL']:.4f} | {100*baseline['retain_name_accuracy']:.1f}% | {100*baseline['generic_keyword_accuracy']:.1f}% |"]
    for version in ('v2','v3'):
        rows = [r for r in results if r['version']==version]
        stats = {key: statistics.mean(r[key] for r in rows) for key in
                 ('retain_rougeL', 'retain_name_accuracy', 'generic_keyword_accuracy')}
        summary[version] = stats
        lines.append(f"| {version}, mean of nine checkpoints | {stats['retain_rougeL']:.4f} | {100*stats['retain_name_accuracy']:.1f}% | {100*stats['generic_keyword_accuracy']:.1f}% |")
    lines += ['', 'A failure of the primary log-probability drift guard should not be equated with loss of factual answers. Conversely, preserving four answers and two generic examples cannot establish preservation of every unrelated capability. Full response text is saved in the adjacent JSON files.']
    write(folder/'utility_audit/summary.json', summary)
    (folder/'UTILITY_AUDIT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('UTILITY AUDIT COMPLETE', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    (prepare if args.prepare else execute)(Path(args.output).resolve())
