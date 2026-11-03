"""Publish measured feedback validation as a local, read-only demo report."""
import hashlib
from html import escape
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/feedback_validation_20261027'
OUTPUT = ROOT / 'frontend/artifacts/feedback-validation'
NAMES = {'tofu-maria-lucia-sousa': 'Maria Lucia Sousa', 'tofu-giorgi-meladze': 'Giorgi Meladze'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def percent(value):
    return 'Not measured' if value is None else f'{value * 100:.2f}%'


def duration(value):
    if value is None:
        return 'Not recorded'
    return f'{int(value // 60)}m {int(value % 60):02d}s'


def number(value):
    return 'Not recorded' if value is None else f'{value:.4f}'


def kept_attempt_metrics(metrics):
    """Display stored kept-state development measurements without re-scoring."""
    detail = metrics.get('details') or {}
    cells = (
        ('Complete-answer likelihood suppressed', percent(metrics.get('forget_suppressed_ratio')),
         'Share meeting the configured likelihood floor: canonical global floor for V2, eligible per-answer base floors for V3.'),
        ('Forget avg log probability', number(metrics.get('forget_avg_log_prob')),
         'Mean log probability of complete reference answers; a lower value alone does not establish suppressed recovery.'),
        ('Forget answer ROUGE-L', number(metrics.get('forget_rougeL')),
         'Generated answers compared with forget references; low overlap can also mean incorrect answers.'),
        ('Retain avg likelihood decline', number(metrics.get('retain_log_prob_drop')),
         'Decline from the original mean retain-answer log probability; separate from generated answer quality.'),
        ('Largest individual retain decline', number(detail.get('max_individual_retain_drop')),
         'Largest per-example retain log-probability decline on the likelihood validation sample.'),
        ('Fluency score', number(metrics.get('fluency_score')),
         'Stored generation fluency diagnostic; it does not measure factual correctness.'),
    )
    return ('<p class="metric-scope"><b>Kept checkpoint · development measurements</b><br>'
            'Used to assess this attempt; these are separate from the independent held-out checks below.</p>'
            '<dl class="attempt-metrics">' + ''.join(
                f'<div title="{escape(hint)}"><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>'
                for label, value, hint in cells) + '</dl>')


def rejection_evidence(detail, protocol, author):
    """Keep rejected candidate measurements separate from the published state."""
    evidence = []
    interval = detail.get('rejected_utility_check')
    if isinstance(interval, dict):
        evidence.append('<p><b>Rejected update interval:</b> average retain likelihood decline '
            f'{escape(number(interval.get("retain_log_prob_drop")))} '
            f'(limit {escape(number(interval.get("limit")))}); maximum individual decline '
            f'{escape(number(interval.get("max_individual_retain_drop")))} '
            f'(limit {escape(number(interval.get("individual_limit")))}). '
            'These values describe the update interval rejected by the likelihood guard.</p>')
    candidate = detail.get('rejected_metrics')
    if isinstance(candidate, dict):
        quality = (candidate.get('details') or {}).get('retain_quality_check') or {}
        quality_text = ''
        if quality.get('enabled') is True:
            passed = ('Passed' if quality.get('passed') is True else 'Failed'
                      if quality.get('passed') is False else 'Not recorded')
            quality_text = (f'<li>Retain answer-quality decline: {escape(percent(quality.get("relative_drop")))} '
                            f'(limit {escape(percent(quality.get("limit")))}): {passed}.</li>')
        individual = (candidate.get('details') or {}).get('max_individual_retain_drop')
        minimum_fluency = protocol['requests'][author]['min_fluency_score']
        evidence.append('<p><b>Rejected candidate — not the kept checkpoint:</b> '
            f'{escape(str(candidate.get("verdict", "Verdict not recorded")))}</p><ul>{quality_text}'
            f'<li>Average retain likelihood decline: {escape(number(candidate.get("retain_log_prob_drop")))} '
            f'(limit {escape(number(protocol["limits"]["retain_likelihood_drop"]))}).</li>'
            f'<li>Maximum individual retain likelihood decline: {escape(number(individual))} '
            f'(limit {escape(number(protocol["limits"]["retain_individual_likelihood_drop"]))}).</li>'
            f'<li>Fluency score: {escape(number(candidate.get("fluency_score")))} '
            f'(minimum {escape(number(minimum_fluency))}).</li></ul>')
    if not evidence:
        return ''
    return ('<details><summary>Inspect rejected candidate / rollback measurements</summary>'
            + ''.join(evidence)
            + '<p>Rejected measurements are shown for diagnosis. The comparison table and recovery evidence use the kept checkpoint.</p></details>')


def measured_row(result):
    """Derive displayed measurements from the verified case, not its summary."""
    metrics = result['final_metrics']
    counts = result['calibrated']['counts']
    quality = metrics['details']['retain_quality_check']
    trials = result['trials']
    before, after, relative = quality.get('before'), quality.get('after'), quality.get('relative_drop')
    limit = quality.get('limit')
    if (quality.get('enabled') is not True
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                   for value in (before, after, relative, limit))
            or not 0 < before <= 1 or not 0 <= after <= 1
            or not math.isclose(max(0., (before-after)/before), relative, rel_tol=1e-9, abs_tol=1e-12)
            or quality.get('passed') is not (relative <= limit + 1e-12)):
        raise ValueError('Retain-quality decline or pass flag does not match the measured scores.')
    for key in ('total', 'validated', 'suppressed', 'residual', 'inconclusive',
                'facts_requested', 'facts_with_validated_checks'):
        if type(counts.get(key)) is not int or counts[key] < 0:
            raise ValueError('Invalid audit count: ' + key)
    if (counts['validated'] != counts['suppressed'] + counts['residual']
            or counts['total'] != counts['validated'] + counts['inconclusive']
            or counts['facts_with_validated_checks'] > counts['facts_requested']
            or counts['total'] != len(result['calibrated']['records'])):
        raise ValueError('Audit counts do not match their evidence coverage.')
    return {'author': result['author_id'], 'version': result['version'],
        'execution_status': result['execution_status'], 'scientific_status': result['scientific_status'],
        'method': result['selected_method'], 'attempts': len(trials),
        'suppressed': counts['suppressed'], 'validated': counts['validated'],
        'residual': counts['residual'], 'inconclusive': counts['inconclusive'],
        'fact_coverage': f"{counts['facts_with_validated_checks']}/{counts['facts_requested']}",
        'retain_quality_before': quality['before'], 'retain_quality_after': quality['after'],
        'retain_quality_relative_drop': quality['relative_drop'], 'quality_limit_passed': quality['passed'],
        'retain_quality_sample_count': quality['sample_count'], 'native_verdict': metrics['verdict'],
        'retain_likelihood_drop': metrics['retain_log_prob_drop'],
        'max_individual_retain_drop': metrics['details'].get('max_individual_retain_drop'),
        'fluency': metrics['fluency_score'], 'forget_rougeL': metrics['forget_rougeL'],
        'forget_avg_log_prob': metrics['forget_avg_log_prob'], 'optimizer_steps': result['optimizer_steps'],
        'training_seconds_used': sum(trial['metrics']['details'].get('training_budget_used_seconds', 0.) for trial in trials),
        'wall_seconds': result['wall_seconds']}


def validate_summary_row(summary_row, actual):
    for key, value in actual.items():
        recorded = summary_row.get(key)
        if isinstance(value, bool):
            matches = recorded is value
        elif type(value) is int:
            matches = type(recorded) is int and recorded == value
        elif isinstance(value, float) and isinstance(recorded, (int, float)) and not isinstance(recorded, bool):
            matches = math.isfinite(value) and math.isfinite(recorded) and math.isclose(value, recorded, rel_tol=1e-9, abs_tol=1e-12)
        else:
            matches = recorded == value
        if not matches:
            raise ValueError(f'Comparison summary differs from verified case evidence: {actual["author"]} {actual["version"]} {key}')


def main():
    summary = read(SOURCE / 'comparison.json')
    if summary.get('completed') != 4 or len(summary.get('rows', [])) != 4:
        raise RuntimeError('All four real cases must finish before publishing the demo report.')
    expected = {(author, version) for author in NAMES for version in ('v2', 'v3')}
    pairs = [(row.get('author'), row.get('version')) for row in summary['rows']]
    if len(set(pairs)) != 4 or set(pairs) != expected:
        raise ValueError('The comparison must contain each expected target/version pair exactly once.')
    protocol = read(SOURCE / 'frozen_protocol.json')
    protocol_hash = hashlib.sha256(json.dumps(protocol, sort_keys=True, ensure_ascii=False,
        separators=(',', ':')).encode('utf-8')).hexdigest()
    original = read(SOURCE / 'original_target_verification.json')
    target_hash = protocol['target_adapter_sha256']
    if (original.get('preserved') is not True or original.get('before') != target_hash
            or original.get('after') != target_hash):
        raise ValueError('Original target preservation does not match the frozen protocol.')
    checked = []
    for summary_row in summary['rows']:
        filename = f'{summary_row["author"]}_{summary_row["version"]}.json'
        envelope = read(SOURCE / 'cases' / filename)
        result = envelope['payload']
        payload_hash = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False,
            separators=(',', ':')).encode('utf-8')).hexdigest()
        if envelope['protocol_sha256'] != protocol_hash or envelope['payload_sha256'] != payload_hash:
            raise ValueError('Study evidence failed its integrity check.')
        if result.get('execution_status') != 'COMPLETED':
            raise ValueError('A version/target case did not complete execution.')
        actual = measured_row(result)
        quality = result['final_metrics']['details']['retain_quality_check']
        if (quality['limit'] != protocol['limits']['retain_quality_relative_drop']
                or quality['sample_count'] != len(protocol['retain_cohort']['validation'])
                or quality['token_cap'] != protocol['generation']['max_new_tokens']):
            raise ValueError('Retain-quality limit or sample scope differs from the frozen study.')
        validate_summary_row(summary_row, actual)
        checked.append((actual, result, filename))
    # Do not copy or publish any partial report until every source is verified.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename in ('comparison.csv', 'comparison.json', 'frozen_protocol.json', 'REPORT.md', 'original_target_verification.json'):
        shutil.copy2(SOURCE / filename, OUTPUT / filename)
    table, evidence = [], []
    for row, result, filename in checked:
        name, version = row['author'], row['version']
        shutil.copy2(SOURCE / 'cases' / filename, OUTPUT / filename)
        counts = result['calibrated']['counts']
        tone = 'pass' if row['scientific_status'] == 'SUCCESS' else 'partial' if row['scientific_status'] == 'PARTIAL_SUCCESS' else 'fail'
        score = f"{row['suppressed']}/{row['validated']}" if row['validated'] else 'Unverified'
        outcome_label = row['scientific_status'].replace('_', ' ').title()
        if row['validated'] and row['suppressed'] == 0:
            outcome_label = 'No verified suppression'
        recovered = result.get('recovery')
        approximate = result.get('wall_seconds_is_estimated') is True
        case_time = ('Approximately ' if approximate else '') + duration(row['wall_seconds'])
        recovery_note = ''
        if recovered:
            timing = recovered['timing']
            recovery_note = ('<p class="note"><b>Interrupted execution recovered:</b> completed training and '
                'development measurements were reused from the saved checkpoint and provenance. No training was repeated; '
                'held-out final evaluation was completed afterward. Case time is an estimated sum of the first active segment '
                f'({escape(duration(timing.get("first_segment_seconds_estimate")))}) and measured recovery processing '
                f'({escape(duration(timing.get("recovery_active_seconds")))}). Interruption downtime is excluded. '
                'Recovery-only baseline/reload overhead is included; CPU integrity preflight is excluded. '
                'This value does not support a precise timing comparison.</p>')
        table.append(f'<tr><th>{escape(NAMES[name])}<small>{escape(version.upper())}</small></th>'
            f'<td><span class="badge {tone}" title="Raw status: {escape(row["scientific_status"])}">{escape(outcome_label)}</span></td>'
            f'<td class="score">{score}</td><td>{row["residual"]}</td><td>{row["inconclusive"]}</td>'
            f'<td>{escape(percent(row["retain_quality_relative_drop"]))}</td>'
            f'<td>{row["optimizer_steps"]}</td><td>{duration(row["training_seconds_used"])}</td>'
            f'<td>{escape(case_time)}</td></tr>')
        attempts = []
        for trial in result['trials']:
            detail = trial['metrics']['details']
            decision = detail.get('feedback_decision') or {}
            changes = decision.get('settings_changed') or {}
            settings = ''.join(f'<li>{escape(key)}: {escape(str(change["before"]))} → {escape(str(change["after"]))}</li>'
                               for key, change in changes.items())
            next_settings = f'<p><b>Settings for the next attempt:</b></p><ul>{settings}</ul>' if settings else ''
            diagnostic = detail.get('update_diagnostic')
            update_note = (f'<p><b>Kept-weight diagnostic:</b> {escape(diagnostic.replace("_", " ").title())}</p>'
                           if isinstance(diagnostic, str) else '')
            kept_quality = detail.get('retain_quality_check') or {}
            kept_note = (f'<p><b>Kept checkpoint:</b> development recovery {percent(trial["metrics"]["probe_leak_rate"])}; '
                         f'retain answer-quality decline {percent(kept_quality.get("relative_drop"))}.</p>')
            if detail.get('rolled_back') and diagnostic == 'UPDATES_ROLLED_BACK_OR_NO_EFFECT':
                kept_note += ('<p>No parameter change remained after rollback. A zero retained-quality decline describes '
                              'this kept state, not the rejected candidate.</p>')
            elif detail.get('rolled_back'):
                kept_note += '<p>The kept state was restored or backtracked after a rejected update.</p>'
            adaptation = trial.get('adaptation_applied')
            adaptation_note = f'<p><b>Attempt configuration:</b> {escape(adaptation)}</p>' if adaptation else ''
            attempts.append(f'<div class="attempt"><b>Attempt {trial["trial_index"]}: {escape(trial["method"])}</b>'
                f'<p><b>Execution status:</b> {escape(trial["status"])}</p>{adaptation_note}'
                f'<p>{detail.get("optimizer_steps", "Not recorded")} optimizer updates.</p>{kept_note}'
                f'{kept_attempt_metrics(trial["metrics"])}'
                f'<p><b>Next decision:</b> {escape(decision.get("action", "Decision not recorded"))}'
                f' · {escape(decision.get("reason", ""))}</p>{next_settings}{update_note}'
                f'{rejection_evidence(detail, protocol, name)}</div>')
        pairs = []
        for record in result['calibrated']['records']:
            before, after, base = record['before'], record['after'], record['base']
            pairs.append(f'<details class="response"><summary>{escape(record["calibration"].replace("_", " ").title())}'
                f' · {escape(after["prompt"])}</summary><div class="pair"><div><label>Original target</label><p>{escape(before["response"])}</p></div>'
                f'<div><label>After unlearning</label><p>{escape(after["response"])}</p></div></div>'
                f'<p class="base"><b>Untuned base control:</b> {escape(base["response"])}</p></details>')
        quality = result['final_metrics']['details'].get('retain_quality_check') or {}
        evidence.append(f'<section class="case"><div class="case-head"><div><span class="eyebrow">{version.upper()} · ACTUAL EXECUTION</span>'
            f'<h2>{escape(NAMES[name])}</h2></div><a href="{filename}" download>Download raw evidence ↗</a></div>'
            f'{recovery_note}<p class="quality">Original retain overlap <b>{percent(quality.get("before"))}</b> → final <b>{percent(quality.get("after"))}</b>'
            f' · relative decline <b>{percent(quality.get("relative_drop"))}</b> · limit <b>2%</b>'
            f' · {counts["facts_with_validated_checks"]}/{counts["facts_requested"]} selected facts have calibrated checks.</p>'
            f'<details><summary>Inspect the attempts and feedback decisions</summary>{"".join(attempts)}</details>'
            f'<h3>Independent recovery evidence</h3>{"".join(pairs)}</section>')
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATU · Matched feedback validation</title><style>
:root{font-family:Segoe UI,Arial,sans-serif;color:#19392f;background:#f3f6f1;font-synthesis:none}*{box-sizing:border-box}body{margin:0}a{color:#17765a;text-decoration:none}a:hover{text-decoration:underline}header{display:flex;justify-content:space-between;gap:20px;padding:22px 5%;background:white;border-bottom:1px solid #dce5dc}header strong{letter-spacing:.5px}nav{display:flex;gap:24px;font-size:13px}main{max-width:1240px;padding:36px 28px 55px;margin:auto}.hero{background:#153e31;color:#f3faef;border-radius:16px;padding:40px 44px}.eyebrow{font-size:10px;font-weight:650;letter-spacing:1.6px}.hero .eyebrow{color:#bbd8c5}h1{font-size:42px;line-height:1.14;font-weight:550;letter-spacing:-1.4px;margin:18px 0}p{font-size:13px;line-height:1.85}.hero p{color:#cbded0;max-width:800px}.facts{display:flex;flex-wrap:wrap;gap:24px;border-top:1px solid #517362;margin-top:26px;padding-top:20px}.facts b{display:block;font-size:25px;font-weight:550}.facts span{font-size:11px;color:#cbded0}.toolbar{display:flex;gap:12px;margin:25px 0}.toolbar a{background:white;border:1px solid #d9e4d9;border-radius:8px;padding:11px 17px;font-size:12px}.comparison{overflow-x:auto;background:white;border:1px solid #dce5dc;border-radius:12px;margin-bottom:20px}table{border-collapse:collapse;width:100%;text-align:left;font-size:12px;white-space:nowrap}thead{background:#ebf1e9;color:#5c7267;font-size:10px;text-transform:uppercase;letter-spacing:.6px}th,td{padding:19px 17px;border-bottom:1px solid #e7ece5}tbody tr:last-child>*{border-bottom:0}th{font-weight:550}th small{display:block;margin-top:6px;font-size:10px;color:#6e8074;letter-spacing:1px}.score{font-size:24px;color:#17765a;font-variant-numeric:tabular-nums}.badge{font-size:10px;padding:7px 9px;border-radius:5px;display:inline-block}.pass{background:#e4f1e6;color:#1c684c}.partial{background:#fbf0cf;color:#7d6022}.fail{background:#fbe6e1;color:#a13b29}.note{font-size:12px;color:#64776b;line-height:1.85}.case{background:white;border:1px solid #dce5dc;border-radius:12px;padding:29px;margin-top:26px}.case-head{display:flex;justify-content:space-between;align-items:center;gap:15px}.case-head a{font-size:11px}h2{font-size:26px;letter-spacing:-.7px;font-weight:550;margin:10px 0 15px}h3{font-size:14px;font-weight:550;margin-top:26px}.quality{padding:14px 17px;background:#f0f5ed;border-radius:7px;color:#4b6656}summary{cursor:pointer;font-size:12px;line-height:1.8;color:#226d54;padding:13px 0}.response{border-top:1px solid #e6ece3}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.pair>div{background:#f6f8f3;border:1px solid #e5ebe0;border-radius:8px;padding:17px}.pair p{margin-bottom:0;overflow-wrap:anywhere}label{font-size:9px;letter-spacing:1px;text-transform:uppercase;color:#66816f}.base{font-size:11px;color:#6b7e70}.attempt{border-left:2px solid #bdd8c2;padding:13px 20px;margin:10px 0;background:#f7f9f5}.attempt b{font-size:13px}.attempt p,.attempt li{font-size:11px;line-height:1.8}footer{padding:25px 0;font-size:11px;color:#667b6b}footer p{font-size:11px}@media(max-width:700px){header{padding:18px 22px}nav{gap:12px}main{padding:22px 17px}.hero{padding:28px 24px}h1{font-size:33px}.case{padding:22px}.case-head{display:block}.pair{grid-template-columns:1fr}.facts{gap:22px}.toolbar{flex-wrap:wrap}}
.attempt .metric-scope{margin:15px 0 8px;color:#5a7162}.attempt-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 16px}.attempt-metrics>div{padding:10px 12px;background:#fff;border:1px solid #e3eae0;border-radius:6px}.attempt-metrics dt{font-size:10px;line-height:1.5;color:#617669}.attempt-metrics dd{font-size:17px;font-variant-numeric:tabular-nums;margin:5px 0 0;color:#244f3c}@media(max-width:700px){.attempt-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.attempt-metrics>div{padding:9px}}
</style></head><body><header><strong>ATU Research Studio</strong><nav><a href="/">Dashboard</a><a href="/#presentation-demos">Presentation demos</a></nav></header><main>
<section class="hero"><span class="eyebrow">FROZEN PROTOCOL · REAL GPU EVIDENCE</span><h1>V2 and V3.<br>The same requests, measured.</h1><p>Canonical ATU V2 with shared validation guards, compared with the current V3 feedback policy. Complete results remain visible. Final recovery questions never choose methods or settings.</p><div class="facts"><div><b>4</b><span>completed version–target cases</span></div><div><b>2%</b><span>relative retain-quality loss limit</span></div><div><b>5 facts</b><span>selected per target</span></div><div><b>One seed</b><span>selected stress cases</span></div></div></section>
<div class="toolbar"><a href="comparison.csv" download>Download comparison CSV ↓</a><a href="frozen_protocol.json" download>Settings and source hashes ↓</a><a href="REPORT.md" download>Research notes ↓</a></div>
<section class="comparison"><table><thead><tr><th>Target / version</th><th>Measured outcome</th><th>Suppressed / calibrated</th><th>Residual</th><th>Uncertain</th><th>Retain quality decline</th><th>Updates</th><th>Training loop time</th><th>Case time</th></tr></thead><tbody>{{TABLE_ROWS}}</tbody></table></section>
<p class="note">Both policies receive identical selected facts, 100 retain training answers, 25 fixed validation answers, 10 development prompts and 6 held-out recovery prompts. Requested allowance: 600 training-loop seconds, checked at safe boundaries; an in-flight controller or evaluation operation may finish after that time. The optimizer-update maximum is 48. Loading, preparation and final tests add wall time. Greedy generations use 48 tokens. Actual resource use can differ. Multiple prompts can test the same fact.</p>
{{CASE_EVIDENCE}}
<footer><b>What this demonstrates</b><p>Measured recovery and bounded adaptation under explicit retain constraints. Retain quality is mean ROUGE-L against reference answers; the reported decline is relative to the original model score on this fixed sample. It is not accuracy or all retained knowledge. That cohort constrains selection and is not an independent retain-generalization benchmark. V2 uses its canonical global floor in the common validation wrapper; V3 uses per-answer base floors and automatic attempts. These are complete policies, not an isolated test of method switching. Two selected authors and one seed do not establish universal superiority or knowledge deletion. A replacement answer may be incorrect even when the target fact is suppressed.</p></footer></main></body></html>'''
    html = html.replace('th,td{padding:19px 17px', 'th,td{padding:19px 14px')
    html = html.replace('A replacement answer may be incorrect even when the target fact is suppressed.',
        'A replacement answer may be incorrect or incoherent even when target fragments are suppressed. '
        'The fluency diagnostic uses two generic prompts; it does not certify the quality of target answers. '
        'Inspect the actual paired responses before interpreting suppression as useful behavior.')
    (OUTPUT / 'index.html').write_text(html.replace('{{TABLE_ROWS}}', ''.join(table)).replace('{{CASE_EVIDENCE}}', ''.join(evidence)), encoding='utf-8')
    print(str(OUTPUT / 'index.html'))


if __name__ == '__main__':
    main()
