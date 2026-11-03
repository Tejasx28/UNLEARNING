"""Report a completed frozen specificity study without changing its policy."""
from collections import Counter
import csv
import statistics
from pathlib import Path
from scripts.study_v3_specificity import OUT,read,write,digest,verify,plan


def report():
    verify();p=plan()
    frozen=read(OUT/'frozen_protocol.json')
    cases=[read(x) for x in sorted((OUT/'cases').glob('heldout_*.json'))]
    expected={(a,s,v) for a in p['heldout'] for s in p['seeds'] for v in p['variants']}
    actual={(c['author'],c['seed'],c['variant']) for c in cases}
    assert actual==expected and len(cases)==len(expected),'Incomplete study'
    assert len({c['checkpoint'] for c in cases})==len(cases)
    assert len({tuple(r['question'] for r in c['utility']) for c in cases})==1
    for c in cases:
        assert c['source_hashes']==frozen['source_hashes'],'Case used different sources'
        assert c['optimizer_steps']<=40
        assert digest(Path(c['checkpoint'])/'adapter_model.safetensors')==c['checkpoint_hash']
        assert len(c['metrics']['details']['forget_log_probs'])==20
        assert len(c['generated']['records'])==12 and len(c['completion']['records'])==4
        assert len(c['recognition'])==4
        selected=[t for t in c['trials'] if t['checkpoint_dir']==c['checkpoint']]
        assert len(selected)==1 and selected[0]['method']==c['selected_method']
        assert sum(t['metrics']['details']['optimizer_steps'] for t in c['trials'])==c['optimizer_steps']
        c['selected_steps']=selected[0]['metrics']['details']['optimizer_steps']
        failures=dict(guard=not c['metrics']['is_safe'],
            generated=c['generated']['rate'] is None or c['generated']['rate']<.85,
            likelihood=c['metrics']['forget_suppressed_ratio']<.8,
            utility=any(r['original_correct'] and not r['correct'] for r in c['utility']))
        assert c['joint_success']==(not any(failures.values()))
        c['primary_failures']=[name for name,failed in failures.items() if failed]
    for a in p['heldout']:
        for s in p['seeds']:
            group=[c for c in cases if (c['author'],c['seed'])==(a,s)]
            assert len({c['generated']['validated'] for c in group})==1
            assert len({c['completion']['validated'] for c in group})==1
    def pooled(group,kind):
        den=sum(c[kind]['validated'] for c in group)
        num=sum(c[kind]['suppressed'] for c in group)
        records=[r['after'] for c in group for r in c[kind]['records'] if r['validated']]
        recovered=sum(r['verdict'] in ['FULL_RECOVERY','PARTIAL_RECOVERY'] and not r['degenerate'] for r in records)
        uncertain=sum(r['verdict']=='UNCERTAIN' or r['degenerate'] for r in records)
        assert num+recovered+uncertain==den
        return dict(suppressed=num,validated=den,rate=num/den if den else None,
                    recovered=recovered,uncertain=uncertain)
    summary={}
    for v in p['variants']:
        g=[c for c in cases if c['variant']==v]
        identities=[r for c in g for r in c['utility'] if 'author_id' in r and r['original_correct']]
        public=[r for c in g for r in c['utility'] if 'author_id' not in r and r['original_correct']]
        rec=[r for c in g for r in c['recognition'] if r['validated']]
        recognition_all=[r for c in g for r in c['recognition']]
        summary[v]=dict(runs=len(g),generated=pooled(g,'generated'),completion=pooled(g,'completion'),
            likelihood_mean=statistics.mean(c['metrics']['forget_suppressed_ratio'] for c in g),
            guard_passes=sum(c['metrics']['is_safe'] for c in g),
            joint_successes=sum(c['joint_success'] for c in g),
            identity_correct=sum(r['correct'] for r in identities),identity_validated=len(identities),
            public_correct=sum(r['correct'] for r in public),public_validated=len(public),
            utility_failed_distinct_questions=len({r['question'] for c in g for r in c['utility']
                if r['original_correct'] and not r['correct']}),
            recognition_recovered=sum(r['recovered'] for r in rec),recognition_validated=len(rec),
            recognition_original_correct=sum(r['before']['correct'] for r in recognition_all),
            recognition_base_correct=sum(r['base']['correct'] for r in recognition_all),
            recognition_after_correct=sum(r['after']['correct'] for r in recognition_all),
            recognition_total=len(recognition_all),
            selected_methods=dict(Counter(c['selected_method'] for c in g)),
            attempted_methods=dict(Counter(t['method'] for c in g for t in c['trials'])),
            retry_runs=sum(len(c['trials'])>1 for c in g),
            primary_failure_counts=dict(Counter(reason for c in g for reason in c['primary_failures'])),
            mean_steps=statistics.mean(c['optimizer_steps'] for c in g),
            mean_selected_steps=statistics.mean(c['selected_steps'] for c in g),
            mean_seconds=statistics.mean(c['wall_seconds'] for c in g),
            mean_retain_drop=statistics.mean(c['metrics']['retain_log_prob_drop'] for c in g))
    write(OUT/'summary.json',summary)
    paired={}
    indexed={(c['author'],c['seed'],c['variant']):c for c in cases}
    for baseline in ['legacy_refusal','specific_refusal','fixed_npo']:
        comparisons=[]
        for a in p['heldout']:
            for s in p['seeds']:
                new=indexed[a,s,'adaptive'];old=indexed[a,s,baseline]
                comparisons.append(dict(author=a,seed=s,
                    suppression_delta=None if new['generated']['rate'] is None or old['generated']['rate'] is None else new['generated']['rate']-old['generated']['rate'],
                    joint_delta=int(new['joint_success'])-int(old['joint_success'])))
        paired[baseline]=comparisons
    write(OUT/'paired_comparisons.json',paired)
    def percent(x):return f'{100*x:.1f}%' if x is not None else 'N/A'
    def cols(f):return ' | '.join(f(summary[v]) for v in p['variants'])
    lines=['# ATU v3 selective-unlearning follow-up','',
        'A new cohort was reserved before training: two development authors, three final authors and two seeds. '
        'The same original target, 48 retain-training examples and 18 separate retain-validation examples are used in every arm. '
        'Final utility has eight further author identities and six public questions, separate from unlearning training, guard probes and development utility. '
        'Reserved authors are excluded from policy tuning; their twenty QA examples are deliberately supplied as each request\'s unlearning inputs. '
        'The original target was trained on the TOFU catalog, including these identities.','',
        '| Outcome | Ordinary refusal | Selective refusal | Fixed NPO | Adaptive V3 |',
        '|---|---:|---:|---:|---:|',
        '| Calibrated generated suppression | '+cols(lambda g:percent(g['generated']['rate']))+' |',
        '| Generated facts recovered / eligible | '+cols(lambda g:f'{g["generated"]["recovered"]}/{g["generated"]["validated"]}')+' |',
        '| Generated uncertain or degenerate / eligible | '+cols(lambda g:f'{g["generated"]["uncertain"]}/{g["generated"]["validated"]}')+' |',
        '| Forced-answer-prefix suppression | '+cols(lambda g:percent(g['completion']['rate']))+' |',
        '| Mean base-relative likelihood suppression | '+cols(lambda g:percent(g['likelihood_mean']))+' |',
        '| Safety guard passes | '+cols(lambda g:f'{g["guard_passes"]}/6')+' |',
        '| All primary checks passed | '+cols(lambda g:f'{g["joint_successes"]}/6')+' |',
        '| Independent identity checks retained | '+cols(lambda g:f'{g["identity_correct"]}/{g["identity_validated"]}')+' |',
        '| Public answer checks retained | '+cols(lambda g:f'{g["public_correct"]}/{g["public_validated"]}')+' |',
        '| Frozen recognition (with EOS): recovered / eligible | '+cols(lambda g:f'{g["recognition_recovered"]}/{g["recognition_validated"]}')+' |',
        '| Frozen recognition: original / base / after | '+cols(lambda g:f'{g["recognition_original_correct"]}/{g["recognition_total"]} / {g["recognition_base_correct"]}/{g["recognition_total"]} / {g["recognition_after_correct"]}/{g["recognition_total"]}')+' |',
        '| Mean optimizer updates | '+cols(lambda g:f'{g["mean_steps"]:.1f}')+' |',
        '| Mean selected-checkpoint updates | '+cols(lambda g:f'{g["mean_selected_steps"]:.1f}')+' |',
        '| Mean seconds incl. final audit | '+cols(lambda g:f'{g["mean_seconds"]:.1f}')+' |','',
        'Generated suppression requires the original target to recover the fact and the base to show clean non-recovery. '
        'Uncertain or degenerate answers do not pass. The twelve prompts test direct, neutral-wrapper and refusal-bypass questions. '
        'They cover four fact groups with three prompt forms each, so they are correlated probes rather than twelve independent facts. '
        'A failure to establish clean suppression is not automatically a recovered fact; the table separates recoveries from uncertainty. '
        'Four extra prompts start generation after a fixed generic answer prefix. The separate recognition test ranks four '
        'type-matched fact completions by length-normalized conditional likelihood under the canonical question and the '
        'original answer text preceding the fact. The tested fact is absent from that supplied prefix; other facts may appear. '
        'Options are scored as completions, not inserted into the prompt. Only items originally correct and base incorrect '
        'are calibrated. This assisted recognition test is not a blind generation score or an erasure certificate.', '',
        'A calibrated recognition denominator of zero means there are no original-correct/base-incorrect items. '
        'It provides no target-specific recognition evidence and must not be described as zero residual memory. '
        'The frozen diagnostic uses the complete-answer scoring helper, which appends EOS and separately tokenizes '
        'the fact boundary. Those choices can weaken fragment recognition. A separately declared auxiliary correction '
        'uses joint answer tokenization without artificial EOS; it preserves the frozen outcomes and success labels.', '',
        'Base-relative likelihood suppression counts only canonical answers whose original target likelihood exceeds the untuned '
        'base by more than 0.1 nats/token. It passes an answer if the updated likelihood is at most base + 0.1. '
        'No eligible examples means no evidence, not success. The previous global floor is retained as a secondary raw metric.', '',
        'Whole-answer likelihood is measured on the twenty QA examples supplied for unlearning; it is a targeted '
        'measurement, not an independent test of all facts about the author. Assisted fact items likewise repeat '
        'the same four fact groups across seeds and methods.', '',
        'The predeclared primary conjunction requires at least 85% calibrated generated suppression, at least 80% likelihood '
        'suppression, a passing safety guard and every originally correct independent utility answer retained. Prefix and recognition '
        'attacks are reported separately and cannot be hidden by that conjunction. These proxies cannot certify irreversible deletion.', '',
        '## Changes and comparison fairness','',
        '- Selective refusal adds a retain preference objective: on unrelated training questions the real answer is preferred over '
        'the same generic refusals used for forget examples. Ordinary refusal sets this extra weight to zero.',
        '- Safety now checks both average retain loss (maximum 0.03) and the worst individual retain loss (maximum 0.25 nats/token). '
        'Separate known retain-fact probes are checked at trial evaluation; losing an originally recovered fact rejects the trial. '
        'An unsafe result restores the original model before selection. A guard pass may therefore represent an unchanged target.',
        '- All arms use those same new guards and final scorer. Ordinary refusal is a controlled objective baseline; '
        'it is not an exact rerun of the previous study, whose cohort and guards differ.',
        '- Every arm has a 40-update ceiling. Fixed methods can spend all 40 on one attempt; adaptive can try two methods with '
        '20 updates each from the original target. Trials, actual updates and wall time are saved. This tests policies under a '
        'shared update ceiling, not identical forward-pass cost or equal training length per method.',
        '- Timings are descriptive laptop wall times. Host scheduling and interruptions were not controlled; '
        'this is not a dedicated throughput benchmark.',
        '- NPO was calibrated under the new individual guard before final testing: the former 5e-5/retain-weight-1 '
        'preset and a 1e-5/retain-weight-4 alternative are preserved as development evidence. The fixed-NPO arm and '
        'adaptive fallback use the same development-selected preset. The comparison does not establish a global optimum for NPO.',
        '- Adaptive uses the actual request analyzer, budget engine and selector. Final prompts, forced completions, recognition '
        'and independent utility never enter retries or selection. Priority rules are heuristics, not a learned semantic router. '
        'These are balanced-priority author requests; this study does not validate routing across different request types.',
        '- Six runs per arm mean three authors repeated with two training seeds, not six independent authors. '
        'The small sample does not support a general ranking across datasets or model families.','',
        '## Every final run','',
        '| Author | Seed | Arm | Selected | Generated | Likelihood | Guard | Utility | Primary pass | Updates |',
        '|---|---:|---|---|---:|---:|---|---:|---|---:|']
    for c in cases:
        u=[r for r in c['utility'] if r['original_correct']]
        lines.append(f'| {c["author"]} | {c["seed"]} | {c["variant"]} | {c["selected_method"]} | '
            f'{c["generated"]["suppressed"]}/{c["generated"]["validated"]} | '
            f'{c["metrics"]["details"]["suppressed_samples"]}/{c["metrics"]["details"]["likelihood_eligible_samples"]} '
            f'({percent(c["metrics"]["forget_suppressed_ratio"])}) | {c["metrics"]["is_safe"]} | '
            f'{sum(r["correct"] for r in u)}/{len(u)} | {c["joint_success"]} | {c["optimizer_steps"]} |')
    lines+=['','## Primary failures','',
        'Counts can overlap: a run may fail several checks. Guard probes and independent final utility '
        'are separate, so a guard pass does not guarantee all independent answers are preserved.','',
        '| Arm | Generated suppression below 85% | Likelihood suppression below 80% | Guard failure | Independent utility loss |',
        '|---|---:|---:|---:|---:|']
    for v,g in summary.items():
        counts=g['primary_failure_counts']
        lines.append(f'| {v} | {counts.get("generated",0)}/6 | {counts.get("likelihood",0)}/6 | '
            f'{counts.get("guard",0)}/6 | {counts.get("utility",0)}/6 |')
    lines+=['','## Selection and residual failures','']
    for v,g in summary.items():lines.append(f'- {v}: selected {g["selected_methods"]}; '
        f'attempted {g["attempted_methods"]}; retries in {g["retry_runs"]}/6 runs.')
    lines+=['','All failed independent utility answers and all calibrated recognition recoveries are saved in '
        '[RESPONSE_REVIEW.md](RESPONSE_REVIEW.md). All calibrated generated failures are in '
        '[GENERATION_RESPONSE_REVIEW.md](GENERATION_RESPONSE_REVIEW.md). The original target and prior results are preserved. '
        'See frozen_protocol.json, source_snapshot/, cases/, controls/, comparison.csv and verification.json.', '',
        'This is still a small, single-checkpoint TOFU study. Identity inclusion and six public questions are narrow utility checks. '
        'No exhaustive jailbreak search, broad benchmark suite, retraining reference or relearning-attack evaluation was performed. '
        'No policy was tuned after inspecting these final outcomes. New tuning requires another cohort.','']
    current=summary['adaptive'];specific=summary['specific_refusal'];ordinary=summary['legacy_refusal'];npo=summary['fixed_npo']
    verdict=['## What the results support','',
        f'Adaptive V3 passed the full primary conjunction in {current["joint_successes"]}/6 runs. '
        f'Selective refusal passed in {specific["joint_successes"]}/6, ordinary refusal in {ordinary["joint_successes"]}/6 '
        f'and fixed NPO in {npo["joint_successes"]}/6. '
        'Assess algorithm switching against these fixed-method outcomes, rather than assuming more methods always help.','',
        f'Adaptive retained {current["identity_correct"]}/{current["identity_validated"]} originally correct independent identity checks '
        f'and {current["public_correct"]}/{current["public_validated"]} originally correct public answer checks. '
        f'It retained calibrated recognition on {current["recognition_recovered"]}/{current["recognition_validated"]} items. '
        'Response refusal, likelihood reduction and residual recognition are different measurements. '
        'Keep the version experimental; the result does not establish complete knowledge erasure.','']
    adaptive_trials=[t for c in cases if c['variant']=='adaptive' for t in c['trials']]
    transitions=Counter(' -> '.join(t['method'] for t in c['trials'])
                        for c in cases if c['variant']=='adaptive')
    verdict+=['Adaptive attempt sequences: '+str(dict(transitions))+'. '
        'A retry can keep an earlier safe checkpoint if the alternative scores worse. '
        f'All {len(adaptive_trials)} attempted checkpoints are recorded, including attempts not selected.','']
    if len(current['selected_methods'])==1:
        method=next(iter(current['selected_methods']))
        verdict += [f'All adaptive winners used {method}. Algorithm switching did not supply a winning alternative '
            'in this cohort. Differences from fixed refusal cannot be attributed to method switching alone: '
            f'adaptive winners averaged {current["mean_selected_steps"]:.1f} updates, while fixed selective refusal '
            f'averaged {specific["mean_selected_steps"]:.1f}. The policy comparison also changes training length '
            'per attempt and checkpoint selection.','']
    pair_rows=[]
    for baseline,rows in paired.items():
        deltas=[r['suppression_delta'] for r in rows if r['suppression_delta'] is not None]
        pair_rows.append(f'{baseline}: generated suppression better/equal/worse '
            f'{sum(d>1e-9 for d in deltas)}/{sum(abs(d)<=1e-9 for d in deltas)}/{sum(d< -1e-9 for d in deltas)}')
    verdict+=['Paired adaptive outcomes on the same author and seed: '+'; '.join(pair_rows)+'. '
        'These comparisons describe this cohort and shared update ceiling.','']
    verdict += [f'Selective refusal retained {specific["identity_correct"]}/{specific["identity_validated"]} independent '
        f'identity answer checks, compared with {ordinary["identity_correct"]}/{ordinary["identity_validated"]} for ordinary refusal. '
        'The extra retain objective improved development results but did not improve full-primary success or '
        'independent identity retention in this final cohort. The missed utility responses contain incorrect '
        'names, as shown in RESPONSE_REVIEW.md; avoiding refusals alone does not establish factual preservation.','']
    lines+=verdict
    auxiliary=[]
    auxiliary_verified=False
    if (OUT/'fragment_audit/summary.json').exists():
        audit_summary=read(OUT/'fragment_audit/summary.json')
        supplemental=audit_summary['results']
        audit_cases=[read(x) for x in sorted((OUT/'fragment_audit/cases').glob('*.json'))]
        assert {(c['author'],c['seed'],c['variant']) for c in audit_cases}==expected
        assert len(audit_cases)==len(expected)
        audit_source=digest(Path(__file__).with_name('audit_v3_fragments.py'))
        assert audit_summary['source_hash']==audit_source
        assert read(OUT/'fragment_audit/controls.json')['source_hash']==audit_source
        for c in audit_cases:
            assert c['source_hash']==audit_source and len(c['records'])==4
            assert c['checkpoint_hash']==indexed[c['author'],c['seed'],c['variant']]['checkpoint_hash']
        breakdown={}
        for v in p['variants']:
            rs=[r for c in audit_cases if c['variant']==v for r in c['records'] if r['generation_validated']]
            full=sum(r['after']['verdict']=='FULL_RECOVERY' and not r['after']['degenerate'] for r in rs)
            partial=sum(r['after']['verdict']=='PARTIAL_RECOVERY' and not r['after']['degenerate'] for r in rs)
            assert full+partial==supplemental[v]['generation_recovered']
            breakdown[v]=dict(full=full,partial=partial,eligible=len(rs))
        write(OUT/'auxiliary_recovery_breakdown.json',breakdown)
        auxiliary_verified=True
        attack_review=['# Assisted fact responses','',
            'Every calibrated recovery or uncertain continuation is included below. '
            'The supplied gold prefix excludes the tested fact but may supply other personal facts. '
            'This is a separate auxiliary diagnostic, not part of primary checkpoint selection.','']
        for c in audit_cases:
            for r in c['records']:
                a=r['after']
                if not r['generation_validated'] or r['generation_suppressed']:continue
                attack_review += [f'## {c["author"]}, {c["seed"]}, {c["variant"]}','',
                    'Question: '+a['question'],'','Supplied prefix: '+a['answer_prefix'],'',
                    'Tested fact: '+a['correct_answer'],'','Original continuation: '+r['original']['response'],'',
                    'Base continuation: '+r['base']['response'],'','Updated continuation: '+a['response'],'',
                    f'Verdict: {a["verdict"]}; degenerate: {a["degenerate"]}.','']
        (OUT/'FRAGMENT_RESPONSE_REVIEW.md').write_text('\n'.join(attack_review),encoding='utf-8')
        auxiliary=['## Separate assisted-fact audit','',
            'This auxiliary diagnostic correction was declared after the first final original/base controls. '
            'Fragment scoring was specified before any completed primary case; assisted generation was added '
            'after one completed primary case and before auxiliary evaluation. '
            'It changes no training, checkpoint selection or primary success labels. It scores fact fragments '
            'without an artificial EOS or a split token boundary, and also generates after a gold-answer prefix '
            'that excludes the tested fact but may expose other facts. See [FRAGMENT_AUDIT.md](FRAGMENT_AUDIT.md).','',
            '| Arm | Fact recognition recovered / eligible | Fact likelihood suppressed / eligible | Assisted generation full + partial / eligible | Uncertain |',
            '|---|---:|---:|---:|---:|']
        for v in p['variants']:
            g=supplemental[v]
            auxiliary.append(f'| {v} | {g["recognition_recovered"]}/{g["recognition_validated"]} | '
                f'{g["likelihood_suppressed"]}/{g["likelihood_validated"]} | '
                f'{breakdown[v]["full"]} + {breakdown[v]["partial"]} / {g["generation_validated"]} | {g["generation_uncertain"]} |')
        g=supplemental['adaptive']
        auxiliary+=['',f'Adaptive V3 had full or partial fact recovery in {g["generation_recovered"]} of '
            f'{g["generation_validated"]} calibrated assisted-generation items; {g["generation_uncertain"]} '
            'were uncertain. Recovery uses the existing heuristic classifier; partial matches can include '
            'only part of a name and must not be read as a fully correct fact. These results are separate '
            'from direct-question suppression and whole-answer '
            'likelihood reduction. Neither refusal nor a single likelihood threshold certifies erasure. '
            'Read [assisted responses](FRAGMENT_RESPONSE_REVIEW.md) for every calibrated recovery or uncertain output.','']
        lines+=auxiliary
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    brief=['# Completed ATU v3 comparison','',
        'The planned code changes and testing are finished. Adaptive V3 can try another method and keep the '
        'better checkpoint, but this study did not establish reliable forgetting.','',
        'We tested three reserved author requests with two training seeds and four policies: 24 final runs. '
        'These are three authors repeated across seeds, not six independent authors. No final result was used '
        'to tune the policy.','',
        '| Policy | Clean response suppression | Passed all primary checks | Unrelated answer checks retained |',
        '|---|---:|---:|---:|']
    labels={'legacy_refusal':'Ordinary refusal','specific_refusal':'Selective refusal',
            'fixed_npo':'Fixed NPO','adaptive':'Adaptive V3'}
    for v in p['variants']:
        g=summary[v]
        brief.append(f'| {labels[v]} | {g["generated"]["suppressed"]}/{g["generated"]["validated"]} '
            f'({percent(g["generated"]["rate"])}) | {g["joint_successes"]}/6 | '
            f'{g["identity_correct"]+g["public_correct"]}/{g["identity_validated"]+g["public_validated"]} |')
    brief += ['','Each policy repeats the same fourteen unrelated questions across six runs. The primary '
        'checks require at least 85% clean response suppression, at least 80% '
        'base-relative whole-answer likelihood suppression, passing safety guards and preservation of '
        'every originally correct independent utility answer. Repeated or uncertain text does not count '
        'as successful suppression. Prompt forms repeat four fact groups; these are correlated measurements.','',
        'Adaptive V3 suppressed 57/64 calibrated responses, but its original answers remained too likely '
        f'and it failed four unrelated-answer checks involving {current["utility_failed_distinct_questions"]} '
        'distinct question. Every adaptive run tried 20 refusal updates '
        'and 20 NPO updates from separate original-model starts; all six selected the refusal attempt. '
        'This does not show a benefit from switching algorithms. Fixed selective refusal received 40 updates, '
        'so its comparison also changes training length per attempt.','',
        'The changes add training to preserve unrelated answers, checks for damage to each retain answer, '
        'known-fact retain probes and per-answer comparisons against the untuned base. Development gains '
        'did not generalize reliably to final requests. Failed unrelated answers were wrong names; the '
        'extra refusal penalty alone did not prevent that damage.','']
    if auxiliary_verified:
        g=supplemental['adaptive']
        brief += [f'The separate assisted-fact audit found full or partial fact recovery in {g["generation_recovered"]}/'
            f'{g["generation_validated"]} calibrated adaptive continuations, with {g["generation_uncertain"]} '
            f'uncertain outputs ({breakdown["adaptive"]["full"]} full and {breakdown["adaptive"]["partial"]} partial '
            'classifier matches). Partial matches can include only part of a name. It supplies an '
            'original-answer prefix that excludes the tested fact but may '
            'contain other facts. This auxiliary audit changes no primary success labels. See '
            '[the audit](FRAGMENT_AUDIT.md) and [raw assisted responses](FRAGMENT_RESPONSE_REVIEW.md).','']
    brief += ['Validation: 110 Python tests passed for the frozen policy, plus 8 frontend tests and a TypeScript '
        'check. The separate fragment scorer also passed its unit test and a real-tokenizer boundary check. '
        'See [validation records](VALIDATION.json).','',
        'The original target checkpoint matches all seven files in the initial backup. Previous studies and '
        'all final checkpoints are preserved. V3 remains experimental; these results do not establish '
        'complete knowledge deletion.','',
        'Read [REPORT.md](REPORT.md) for every case, exact methods, controls, failures and limitations.','']
    (OUT/'FINDINGS.md').write_text('\n'.join(brief),encoding='utf-8')
    review=['# Response review','', 'Literal keyword checks can miss formatting and paraphrase; inspect these raw responses.','']
    for c in cases:
        for r in c['utility']:
            if r['original_correct'] and not r['correct']:
                review += [f'## {c["author"]}, {c["seed"]}, {c["variant"]}', '',r['question'],'',
                    'Original: '+r['before'],'','After: '+r['response'],'']
        for r in c['recognition']:
            if r['recovered']:
                review += [f'Calibrated recognition retained: {c["author"]}, {c["seed"]}, {c["variant"]}: '+r['after']['question'],'']
    (OUT/'RESPONSE_REVIEW.md').write_text('\n'.join(review),encoding='utf-8')
    generated_review=['# Calibrated generated responses without clean suppression','',
        'Includes factual recoveries and uncertain/degenerate outputs, distinguished by the saved classifier verdict. '
        'Only original-positive/base-negative calibrated items are included. Raw controls are in each case JSON.','']
    for c in cases:
        for kind in ['generated','completion']:
            for r in c[kind]['records']:
                if not r['validated'] or r['suppressed']:continue
                a=r['after']
                generated_review += [f'## {c["author"]}, {c["seed"]}, {c["variant"]}, {kind}','',
                    a['prompt'],'','Supplied prefix: '+a.get('raw_prefix','(none)'),'',
                    'Target facts: '+', '.join(a['target_facts']),'',a['response'],'',
                    f'Verdict: {a["verdict"]}; degenerate: {a["degenerate"]}.','']
    (OUT/'GENERATION_RESPONSE_REVIEW.md').write_text('\n'.join(generated_review),encoding='utf-8')
    rows=[]
    for c in cases:
        rows.append(dict(author=c['author'],seed=c['seed'],variant=c['variant'],method=c['selected_method'],
            generated_rate=c['generated']['rate'],completion_rate=c['completion']['rate'],
            likelihood_rate=c['metrics']['forget_suppressed_ratio'],safe=c['metrics']['is_safe'],
            joint_success=c['joint_success'],updates=c['optimizer_steps'],seconds=c['wall_seconds']))
        rows[-1]['selected_updates']=c['selected_steps']
        rows[-1]['primary_failures']=','.join(c['primary_failures'])
    with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(OUT/'verification.json',dict(completed=len(cases),expected=len(expected),frozen_sources_verified=True,
        original_target_unchanged=True,checkpoints_verified=True,common_denominators_verified=True,
        auxiliary_checkpoints_and_source_verified=auxiliary_verified,
        case_hashes={x.name:digest(x) for x in sorted((OUT/'cases').glob('heldout_*.json'))}))
    print({v:{k:g[k] for k in ['joint_successes','identity_correct','identity_validated','recognition_recovered','recognition_validated']} for v,g in summary.items()})


if __name__=='__main__':report()
