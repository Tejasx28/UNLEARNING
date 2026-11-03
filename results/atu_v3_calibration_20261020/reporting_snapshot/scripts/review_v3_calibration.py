"""Extract final response evidence without altering any scoring or policy."""

from pathlib import Path
import json
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'results/atu_v3_calibration_20261020'


def review(folder=FOLDER):
    folder=Path(folder)
    cases=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder/'cases').glob('heldout_*.json'))]
    lines=['# Final response review','',
        'This is an inspection aid for the frozen comparison. It does not change selection, metrics or method settings.','',
        '## Recovery outcomes on calibrated probes','',
        '| Variant | Clean suppression | Residual recovery | Uncertain/non-clean |','|---|---:|---:|---:|']
    for variant in ('v2','previous','current'):
        count=Counter()
        for c in cases:
            if c['variant']!=variant:continue
            for r in c['calibrated']['records']:
                if not r['validated']:continue
                label=('clean' if r['suppressed'] else 'residual' if r['after']['verdict'] in
                       ('FULL_RECOVERY','PARTIAL_RECOVERY') else 'uncertain')
                count[label]+=1
        lines.append(f'| {variant} | {count["clean"]} | {count["residual"]} | {count["uncertain"]} |')
    lines += ['','## Failed full-name inclusion checks','',
        'Only originally correct final utility questions are considered. A literal full-name mismatch can reflect a factual error, omission or formatting change; inspect the raw text before interpreting it as lost knowledge.','']
    mistakes=[]
    for c in cases:
        for row in c['fresh_utility']:
            if row['original_correct'] and not row['correct']:
                mistakes.append(dict(author=c['author'],seed=c['seed'],variant=c['variant'],**row))
                lines += [f'### {c["variant"]}, {c["author"]}, seed {c["seed"]}','',
                    'Question: '+row['question'],'','Expected full name: '+', '.join(row['keywords']),'',
                    'Original response:','', '```text',row['before'],'```','',
                    'Checkpoint response:','', '```text',row['response'],'```','']
    if not mistakes:lines += ['No failed full-name checks in this small final sample.','']
    lines += ['','## Updated V3: explicit bypass responses, seed 42','',
        'These excerpts use the four fact groups for each author. No recovery in these prompts is not proof of irreversible erasure.','']
    for c in cases:
        if c['variant']!='current' or c['seed']!=42:continue
        lines += ['### '+c['author'],'']
        for record in c['calibrated']['records']:
            if not record['id'].endswith('-2'):continue
            after=record['after']
            lines += ['Prompt: '+after['prompt'],'','Target facts: '+', '.join(after['target_facts']),'',
                '```text',after['response'],'```','',
                f'Classified {after["verdict"]}; calibrated control eligible: {record["validated"]}.','']
    (folder/'QUALITATIVE_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    (folder/'utility_mismatches.json').write_text(json.dumps(mistakes,indent=2),encoding='utf-8')
    return dict(cases=len(cases),utility_mismatches=len(mistakes))


if __name__=='__main__':
    print(review())
