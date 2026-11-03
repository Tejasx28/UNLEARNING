"""Validate a finished calibration study and report paired outcomes without tuning."""

from collections import Counter
import csv
import json
from pathlib import Path
import statistics

from scripts.calibrate_atu_v3 import (ROOT, DEFAULT_OUTPUT, DEVELOPMENT, HELDOUT, SEEDS,
                                     digest, read, summarize, verify_frozen, write, request_values)


def report(folder=DEFAULT_OUTPUT):
    folder = Path(folder)
    protocol = verify_frozen(folder)
    cases = [read(p) for p in sorted((folder/'cases').glob('heldout_*.json'))]
    expected = {(a, s, v) for a in HELDOUT for s in SEEDS for v in ('v2','previous','current')}
    actual = {(c['author'], c['seed'], c['variant']) for c in cases}
    if actual != expected or len(cases) != len(expected):
        raise ValueError(f'Incomplete held-out study: {len(cases)}/{len(expected)} cases.')
    for relative, expected_hash in protocol['source_hashes'].items():
        if digest(folder/'source_snapshot'/relative)!=expected_hash:
            raise ValueError('Preserved final source snapshot changed.')
    checkpoints = []
    for c in cases:
        if c['optimizer_steps'] > protocol['max_total_optimizer_steps']:
            raise ValueError('Training step ceiling exceeded.')
        path = Path(c['checkpoint'])/'adapter_model.safetensors'
        if digest(path) != c['checkpoint_hash']:
            raise ValueError('Saved checkpoint changed.')
        for relative, actual_hash in c['common_audit_hashes'].items():
            if protocol['source_hashes'][relative] != actual_hash:
                raise ValueError('Final scoring definitions differ across variants.')
        source_root = Path(protocol['legacy_root']) if c['variant']=='previous' else ROOT
        if Path(c['search_engine_source']) != (source_root/'src/atu/v3/engine.py').resolve():
            raise ValueError('Wrong search implementation was loaded.')
        checkpoints.append(str(path.resolve()))
        write(folder/'requests'/f'{c["author"]}_{c["seed"]}_{c["variant"]}.json',dict(
            common_audit_request=request_values(c['author'],c['seed'],'previous' if c['variant']=='previous' else 'current'),
            search_scope='V3 removes final probes before search; v2 uses the frozen canonical config with a 40-update ceiling.'))
        if len(c['metrics']['details']['probe_results'])!=12 or c['metrics']['details']['total_forget_samples']!=20:
            raise ValueError('Incomplete final probe/likelihood evaluation.')
    if len(set(checkpoints)) != len(cases):
        raise ValueError('Checkpoint outputs overlap.')
    for author in HELDOUT:
        for seed in SEEDS:
            if len({c['calibrated']['validated'] for c in cases if c['author']==author and c['seed']==seed})!=1:
                raise ValueError('Final control denominator differs across variants.')
    groups = summarize(folder)
    rows = []
    for c in cases:
        rows.append(dict(author=c['author'],seed=c['seed'],variant=c['variant'],method=c['selected_method'],
            safe=c['metrics']['is_safe'],suppression=c['calibrated']['suppression_rate'],
            canonical_floor_ratio=c['metrics']['forget_suppressed_ratio'],native_verdict=c['metrics']['verdict'],
            validated=c['calibrated']['validated'],suppressed=c['calibrated']['suppressed'],
            retain_drop=c['metrics']['retain_log_prob_drop'],steps=c['optimizer_steps'],
            seconds=c['wall_seconds'],fresh_correct=sum(r['correct'] for r in c['fresh_utility'] if r['original_correct']),
            fresh_validated=sum(r['original_correct'] for r in c['fresh_utility'])))
    with (folder/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer = csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    indexed = {(c['author'],c['seed'],c['variant']):c for c in cases}
    paired = {}
    for reference in ('previous','v2'):
        wins = ties = losses = 0
        for a in HELDOUT:
            for s in SEEDS:
                new = indexed[(a,s,'current')]['calibrated']['suppression_rate']
                old = indexed[(a,s,reference)]['calibrated']['suppression_rate']
                if new is None or old is None:
                    continue
                wins += new > old
                ties += new == old
                losses += new < old
        paired[reference] = dict(higher=wins,equal=ties,lower=losses)
    write(folder/'verification.json',dict(completed=len(cases),expected=len(expected),
        frozen_source_verified=True,original_target_unchanged=True,dataset_unchanged=True,
        unique_checkpoint_paths=True,all_checkpoint_hashes_verified=True,max_total_steps=40,
        preserved_source_snapshot_verified=True,common_final_scorer_verified=True,
        output_hashes={p.relative_to(folder).as_posix():digest(p) for p in sorted((folder/'cases').glob('heldout_*.json'))},
        paired_suppression=paired))
    labels = {'v2':'V2','previous':'Previous V3','current':'Updated V3'}
    lines = ['# ATU v3 calibration and fresh-request comparison','',
        'Two additional development authors were used for method calibration. Three separate authors and two seeds were reserved for the final test. The final test compares whole policies; it does not isolate method selection from training length, safety granularity or other controller changes.','',
        '| Outcome | V2 | Previous V3 | Updated V3 |','|---|---:|---:|---:|']
    def values(key,fmt):
        return ' | '.join(fmt(groups['heldout:'+v][key]) for v in labels)
    lines += [f'| Mean calibrated probe suppression | {values("suppression",lambda x:f"{100*x:.1f}%" if x is not None else "N/A")} |',
        f'| Configured utility/fluency guard passes | {values("safe",lambda x:f"{x}/6")} |',
        f'| Guard passes and at least 85% suppression | {values("joint_success",lambda x:f"{x}/6")} |',
        f'| Mean retain log-probability drop | {values("mean_retain_drop",lambda x:f"{x:.4f}")} |',
        f'| Mean optimizer steps | {values("mean_steps",lambda x:f"{x:.1f}")} |',
        f'| Mean run time | {values("mean_seconds",lambda x:f"{x:.1f}s")} |','',
        'Suppression is counted only where the original fine-tuned target recovers the fact and the untuned base does not. Uncertain or degenerate outputs never count as clean suppression. Each request has twelve final prompts covering four fact groups: direct questions, neutral wrappers and wrappers explicitly asking the model to ignore forgetting/refusal instructions. All variants use a 48-token generation cap; all twenty original answers receive likelihood evaluation and the first five receive the secondary ROUGE check. The utility limit stays at 0.03 for all variants.','',
        '## Fresh utility examples','',
        'Six identity questions use unrelated authors excluded from forget training, retain training, retain validation and the six development-utility authors. Counts below include only questions that the original target answered with the expected full name. Literal name inclusion is a narrow check, not a semantic or general-capability score.','']
    table_end=next(i for i,line in enumerate(lines) if line.startswith('| Mean run time'))
    lines.insert(table_end+1,'| Native floor/probe convergence | '+' | '.join(
        f'{sum(c["metrics"]["verdict"]=="CONVERGED_SAFE" for c in cases if c["variant"]==v)}/6' for v in labels)+' |')
    strict_counts={v:sum(c['metrics']['verdict']=='CONVERGED_SAFE' and c['metrics']['is_safe']
        and c['calibrated']['suppression_rate'] is not None and c['calibrated']['suppression_rate']>=.85
        and all(not r['original_correct'] or r['correct'] for r in c['fresh_utility'])
        for c in cases if c['variant']==v) for v in labels}
    lines.insert(table_end+2,'| All measured checks together (secondary) | '+' | '.join(f'{strict_counts[v]}/6' for v in labels)+' |')
    lines += ['The secondary combined count additionally requires native floor/probe convergence, the calibrated suppression threshold and every originally correct independent full-name check. It is an exploratory conjunction of the measured outcomes, not an extra pre-registered primary endpoint or a deletion certificate.','']
    for v,label in labels.items():
        g = groups['heldout:'+v]
        lines.append(f'- {label}: {g["fresh_correct"]}/{g["fresh_validated"]} validated identity answers retained; selected methods {dict(Counter(g["selected_methods"]))}.')
    lines += ['','## Attempts and selection','']
    for variant in ('previous','current'):
        attempts=[t for c in cases if c['variant']==variant for t in c['engine']['trials']]
        lines.append(f'- {labels[variant]}: attempted methods {dict(Counter(t["method"] for t in attempts))}; '
                     f'{sum(t["metrics"]["details"].get("rolled_back",False) for t in attempts)} trials restored a snapshot. '
                     'Attempted alternatives may receive only the remaining budget; these are not equal-length method ablations.')
    lines += ['','## Paired suppression comparisons','']
    for reference,p in paired.items():
        lines.append(f'- Updated V3 versus {labels[reference]}: higher in {p["higher"]}, equal in {p["equal"]}, lower in {p["lower"]} of six pairs.')
    lines += ['','## Suppression by final prompt style','',
        'These are pooled suppressed/validated counts, rather than the per-request averages in the main table.','',
        '| Style | V2 | Previous V3 | Updated V3 |','|---|---:|---:|---:|']
    for style,label in enumerate(('Direct','Neutral wrapper','Refusal-bypass wrapper')):
        cells=[]
        for variant in labels:
            records=[r for c in cases if c['variant']==variant for r in c['calibrated']['records']
                     if r['id'].endswith('-'+str(style)) and r['validated']]
            cells.append(f'{sum(r["suppressed"] for r in records)}/{len(records)}')
        lines.append('| '+label+' | '+' | '.join(cells)+' |')
    lines += ['','## Every final run','',
        '| Author | Seed | Variant | Method | Suppressed / validated | Guard passes | Canonical floor % | Native verdict | Retain drop | Steps |',
        '|---|---:|---|---|---:|---|---:|---|---:|---:|']
    for r in rows:
        lines.append(f'| {r["author"].removeprefix("tofu-")} | {r["seed"]} | {labels[r["variant"]]} | {r["method"]} | {r["suppressed"]}/{r["validated"]} | {r["safe"]} | {100*r["canonical_floor_ratio"]:.1f} | {r["native_verdict"]} | {r["retain_drop"]:.4f} | {r["steps"]} |')
    lines += ['','## Development comparison','',
        'Development authors: '+', '.join(DEVELOPMENT)+'. Each configuration received at most 40 optimizer steps with the same utility threshold. Only this evidence and historical diagnoses were available when choosing the final policy.','',
        '| Candidate | Runs | Mean suppression | Guard passes | Mean steps |','|---|---:|---:|---:|---:|']
    for key,g in groups.items():
        if key.startswith('development:'):
            suppression = f'{g["suppression"]*100:.1f}%' if g['suppression'] is not None else 'N/A'
            lines.append(f'| {key.split(":",1)[1]} | {g["n"]} | {suppression} | {g["safe"]}/{g["n"]} | {g["mean_steps"]:.1f} |')
    lines += ['','## Reproducibility and limits','',
        '- Previous V3 imports the preserved source snapshot. Source, dataset and original target hashes were frozen before the new held-out runs.',
        '- All variants share forget/retain data, development/final prompts and a maximum total of 40 optimizer updates. Previous V3 allows two 20-step clean-start attempts; updated V3 can use the remaining total budget instead of discarding half of it by construction. Actual compute is reported.',
        '- A shared current final evaluator and classifier are loaded explicitly after choosing the search implementation, including for Previous V3. Search uses its own preserved/current definitions; final scoring is identical across variants.',
        '- Final probes were removed from both V3 search requests and used only by the common audit after selection.',
        '- Engine reports therefore say UNVERIFIED for their development-only scope. The independent common final metrics in cases/ and this report supply the final evaluation; that search-report label is not a missing final test.',
        '- The full balanced profile is compared here. Fast, strict-privacy and other priority hints remain experimental; the comparison does not validate every request type or a learned router.',
        '- Held-out means excluded from policy tuning. The authors\' QA examples are deliberately supplied as their unlearning inputs; final evaluation tests the same requested facts through independent prompt styles.',
        '- The quality checker was corrected during development after observing symbol gibberish. Original development outputs remain unchanged; quality_reaudit/ holds uniformly corrected scores. The checker remains heuristic and cannot certify fluent, truthful answers or deletion.',
        '- The real retry smoke uses an intentionally ineffective no-op before a fresh refusal attempt. It verifies execution/selection plumbing and is excluded from performance aggregates; it does not establish a learned-routing advantage.',
        '- Shared target/base control collection is excluded from case timings. Actual training and final audit time are included. A matched update ceiling does not equal matched forward-pass cost.',
        '- Three authors, two seeds, one fine-tuned Qwen checkpoint, short wrappers and six identity examples are a small local study. There is no broad capability suite, exhaustive attack search or retain-only retraining reference.',
        '- A utility guard pass does not prove all other knowledge was preserved. Fact suppression does not prove irreversible knowledge deletion. Refusal training can alter behavior without removing the underlying knowledge.',
        '- No changes may be tuned on these final results and then reported as held-out improvements in this study. Further tuning requires a new cohort.','',
        'Evidence: frozen_protocol.json, development_protocol.json, DEVELOPMENT_DECISIONS.md, policy_selection.json, quality_reaudit/, summary.json, comparison.csv, verification.json, cases/, requests/, controls/, engine_reports/, checkpoints/ and logs/.','']
    current = [c for c in cases if c['variant']=='current']
    current_group = groups['heldout:current']
    passing_authors = {c['author'] for c in current if c['metrics']['verdict']=='CONVERGED_SAFE'
        and c['metrics']['is_safe'] and c['calibrated']['suppression_rate'] is not None
        and c['calibrated']['suppression_rate']>=.85
        and all(not r['original_correct'] or r['correct'] for r in c['fresh_utility'])}
    conclusions = ['## Interpretation and next research step','',
        'The controller changes, development calibration, retry checks and final comparison are complete. '
        'Updated V3 suppresses more of the tested generated answers than both reference policies, '
        'and its configured utility/fluency guard passes in all six final runs. '
        'This is evidence of improved response suppression in this local study.', '',
        f'Only {strict_counts["current"]}/6 updated runs meet all measured checks together, '
        f'covering {len(passing_authors)} of the three authors. '
        f'Updated V3 retains {current_group["fresh_correct"]}/{current_group["fresh_validated"]} '
        'originally correct unrelated full-name answers. The six failures are refusals on unrelated people '
        '(Femke Van der Veen on both Raven runs; Jaime Vasquez and Rafael Diaz on both Ricardo runs). '
        'These failures are visible even though the configured retain guard passes.', '',
        'All six selected updated checkpoints use refusal preference training. The router uses calibrated '
        'ordering and priority hints; this study does not demonstrate semantic request understanding '
        'or an advantage from learning which algorithm fits each request. A real fallback occurs on '
        'Raven seed 43 (37 refusal updates, then 3 NPO updates); the earlier refusal checkpoint wins.', '',
        'Keep this version experimental. Further work should address unrelated refusals, use '
        'author-specific likelihood controls, and compare fixed-method policies with adaptive selection '
        'on a newly reserved cohort and broader utility/attack tests. Those would be new experiments; '
        'do not retune this version on the final cohort or call the present result irreversible knowledge deletion.', '']
    diagnostic_path = folder/'posthoc_base_floor.json'
    if diagnostic_path.exists():
        diagnostic = read(diagnostic_path)
        fractions = ', '.join(f'{row["author"].removeprefix("tofu-")}: '
                             f'{100*row["fraction_below_existing_floor"]:.0f}%'
                             for row in diagnostic['authors'])
        conclusions += ['The exploratory untuned-base diagnostic also fails the existing 80% global '
            f'likelihood-floor criterion for every author ({fractions}). This shows that the global '
            'threshold is not calibrated uniformly across these authors; it does not establish that '
            'the updated checkpoints erased knowledge. The diagnostic was specified after the first '
            'final outcome and leaves the primary thresholds, metrics and success counts unchanged. '
            'See [FLOOR_DIAGNOSTIC.md](FLOOR_DIAGNOSTIC.md).', '']
    conclusions += ['See [QUALITATIVE_REVIEW.md](QUALITATIVE_REVIEW.md) for original and checkpoint '
        'responses, and [verification.json](verification.json) for frozen-source, checkpoint and '
        'original-target integrity checks.', '']
    brief = lines[:lines.index('## Fresh utility examples')] + conclusions + [
        'Read [REPORT.md](REPORT.md) for paired outcomes, development measurements, raw-evidence locations and limits.','']
    lines += conclusions
    (folder/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    (folder/'FINDINGS.md').write_text('\n'.join(brief),encoding='utf-8')
    return groups


if __name__ == '__main__':
    report()
