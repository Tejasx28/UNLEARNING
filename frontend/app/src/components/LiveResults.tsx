import { useState } from 'react';
import { ArrowLeft, ArrowRight, Download, Check, Copy, ShieldCheck, ShieldAlert, Search, Activity, Swords, Clock, AlertCircle, FileCheck2, CircleHelp, SlidersHorizontal } from 'lucide-react';
import type { LiveJobStatus, V3Attempt } from '../types';
import { downloadJson } from '../services/research';
import { formatDuration, measuredPercent, methodLabel, runOutcome, priorityLabel, outcomeDescription } from '../services/jobs';
import { RedTeamAttackCard, BeforeAfterComparison } from './Evidence';
import { PrivacyDiscovery } from './PrivacyDiscovery';
import { RetainQualityCard } from './RetainQualityCard';
import { discoveryCounts } from '../services/discovery';
import '../review.css';

function isCount(value: unknown): value is number { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
function count(value: unknown) { return isCount(value) ? String(value) : 'Not recorded'; }
function duration(value: unknown) { return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? formatDuration(value) : 'Not recorded'; }

export function LiveResults({ job, onBack, onNew, onFull, backLabel = 'Run history' }: { job: LiveJobStatus; onBack: () => void; onNew: () => void; onFull?: () => void; backLabel?: string }) {
  const [tab, setTab] = useState('Overview');
  const [filter, setFilter] = useState('All');
  const [limit, setLimit] = useState(8);
  const [pairId, setPairId] = useState('');
  const result = job.result;
  const outcome = runOutcome(job);
  const tabs = ['Overview', 'Privacy discovery', 'Attempts', 'Recovery tests', 'Run details'];
  if (!result) return <div className="studio-page"><button className="text-button" onClick={onBack}><ArrowLeft size={16} />Run history</button><div className="studio-empty"><AlertCircle /><h2>{job.status === 'CANCELLED' ? 'This experiment was stopped.' : 'This run did not produce a result.'}</h2><p>{job.error || (job.status === 'CANCELLED' ? 'The GPU worker exited. No completed unlearning result is claimed.' : 'Open the monitor for more details.')}</p><button className="button primary" onClick={onNew}>New experiment</button></div>{job.discovery && <><p className="studio-caption">Discovery finished before this run ended. Its original model evidence remains available below.</p><PrivacyDiscovery report={job.discovery} /></>}</div>;
  const counts = discoveryCounts(result.facts);
  const audit = result.audit;
  const hasValidated = isCount(audit.validated_attacks) && audit.validated_attacks > 0;
  const hasCoverage = isCount(audit.facts_requested) && isCount(audit.facts_with_validated_checks);
  const requestedFacts = result.provenance?.selected_questions?.length ?? job.settings?.fact_indices?.length;
  const trainingBudget = result.provenance?.training_budget_seconds ?? job.settings?.training_budget_seconds;
  const baselineControls = result.performance?.baseline_controls;
  const OutcomeIcon = outcome.tone === 'green' ? ShieldCheck : outcome.tone === 'red' ? ShieldAlert : AlertCircle;
  const discovery = job.discovery || { entity: result.entity, facts: result.facts, checkpoint_hash: result.provenance?.target_checkpoint_hash || '' };
  const pairs = result.attacks.filter(pair => pair.before && pair.before.prompt === pair.after.prompt);
  const comparison = pairs.find(pair => pair.after.probe_id === pairId) ?? pairs.find(pair => pair.calibration) ?? pairs[0];
  const filtered = result.attacks.filter(pair => filter === 'All'
    || filter === 'Recovered' && ['FULL_RECOVERY', 'PARTIAL_RECOVERY'].includes(pair.after.verdict)
    || filter === 'Suppressed' && pair.calibration === 'VERIFIED_SUPPRESSION'
    || filter === 'Uncertain' && (pair.calibration === 'INCONCLUSIVE' || pair.after.verdict === 'UNCERTAIN' || pair.after.is_degenerate));
  return <div className="studio-page live-results">
    <div className="page-breadcrumb"><button className="text-button" onClick={onBack}><ArrowLeft size={15} />{backLabel}</button><span> / </span><span>{job.job_id}</span></div>
    <div className="studio-heading review-heading"><div><span className="studio-eyebrow">EXPERIMENT REPORT</span><h1>{job.author_name}</h1><div className="review-run-meta"><span>{job.mode === 'fast' ? 'Quick check' : 'Full experiment'}</span><span>{duration(job.elapsed_seconds)}</span><span>{result.v3 ? 'ATU v3' : 'ATU v2'}</span>{requestedFacts != null && <span>{requestedFacts} selected {requestedFacts === 1 ? 'fact' : 'facts'}</span>}</div></div><button className="button secondary" onClick={() => downloadJson(job, job.job_id + '-results.json')}><Download size={16} />Export results</button></div>
    <div className={'outcome-banner review-outcome ' + outcome.tone}><OutcomeIcon size={25} /><div><span className="review-kicker">MEASURED OUTCOME</span><strong>{outcome.label}</strong><p>{outcomeDescription(job)}</p></div><span className="studio-badge">Execution complete</span></div>
    {result.scoring_recheck && <div className="studio-note amber" role="status"><AlertCircle size={18} /><div><strong>Saved responses rechecked with corrected scoring</strong><p>{result.scoring_recheck.scope} {result.scoring_recheck.missing_forward_fact_checks.length} selected facts lacked a valid forward question in the older probe set. {result.scoring_recheck.limitation}</p><small>Revision {result.scoring_recheck.revision} · Original report preserved · {result.scoring_recheck.changes.length} labels changed</small></div></div>}
    {(job.mode === 'fast' || result.evaluation_scope === 'preliminary_screening') && <div className="studio-note amber" role="status"><AlertCircle size={18} /><div><strong>This was a limited Quick screening</strong><p>Quick uses at most 8 training updates and one method attempt. Increasing its time budget alone does not raise those limits. Full experiment uses deeper training and evaluation; Automatic can try up to three attempts from the original model.</p>{onFull && <button className="text-button" onClick={onFull}>Configure Full experiment<ArrowRight size={14} /></button>}</div></div>}
    <div className="studio-metrics">
      <Metric icon={<ShieldCheck size={19} />} value={hasValidated ? count(audit.verified_suppressions) + ' / ' + count(audit.validated_attacks) : 'Unverified'} label="Validated suppression" detail="Suppressed / calibrated checks" />
      <Metric icon={<Swords size={19} />} value={hasValidated ? count(audit.residual_leaks) : 'Unverified'} label="Residual leaks" detail="Target information still recovered" />
      <Metric icon={<Activity size={19} />} value={measuredPercent(audit.retain_utility_rate)} label="Retain answer overlap" detail={isCount(audit.retain_utility_examples) ? audit.retain_utility_examples + ' unrelated answers' + (isCount(audit.retain_generation_token_cap) ? ' · ' + audit.retain_generation_token_cap + ' token cap' : '') : 'Evaluation coverage not recorded'} />
      <Metric icon={<Clock size={19} />} value={methodLabel(result.v3?.best_method || (result.v3 ? undefined : 'atu_npo'))} label="Selected method" detail={result.v3 ? result.v3.trials.length + (result.v3.trials.length === 1 ? ' attempt recorded' : ' attempts recorded') : 'V2 controller'} />
    </div>
    <RetainQualityCard check={audit.retain_quality_check} />
    <div className="studio-tabs" role="tablist" aria-label="Result sections">{tabs.map(value => <button role="tab" aria-selected={tab === value} tabIndex={tab === value ? 0 : -1} aria-controls="live-result-panel" id={'result-tab-' + value.replaceAll(' ', '-')} key={value} onClick={() => setTab(value)} onKeyDown={event => {
      const index = tabs.indexOf(value);
      const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
      if (next < 0) return;
      event.preventDefault(); setTab(tabs[next]); document.getElementById('result-tab-' + tabs[next].replaceAll(' ', '-'))?.focus();
    }}>{value}{value === 'Recovery tests' && <span>{result.attacks.length}</span>}</button>)}</div>
    <section id="live-result-panel" role="tabpanel" aria-labelledby={'result-tab-' + tab.replaceAll(' ', '-')}>
      {tab === 'Overview' && <><div className="review-coverage" aria-label="Evidence coverage"><div><FileCheck2 size={18} /><span><strong>{hasCoverage ? `${audit.facts_with_validated_checks} / ${audit.facts_requested} facts` : 'Fact coverage not recorded'}</strong><small>Validated target / base controls</small></span></div><div><CircleHelp size={18} /><span><strong>{count(audit.inconclusive_attacks)} inconclusive checks</strong><small>Not counted as verified suppression</small></span></div><div><SlidersHorizontal size={18} /><span><strong>Utility and forgetting assessed separately</strong><small>Guard checks protect unrelated knowledge</small></span></div></div><button className="discovery-overview-link studio-card" onClick={() => setTab('Privacy discovery')}><span className="review-link-icon"><Search size={22} /></span><span><strong>Explore the original exposure</strong><small>{counts.exposed + counts.partial} / {counts.tested} candidate facts exposed before unlearning · Inspect the measured discovery evidence</small></span><ArrowRight size={19} /></button><div className="studio-section-heading"><div><span className="studio-eyebrow">MODEL RESPONSE EVIDENCE</span><h2>The same question, before and after.</h2><p>Paired responses from this run. Use the selector to inspect another question.</p></div>{pairs.length > 0 && <select aria-label="Compare a live question" className="studio-input" value={comparison?.after.probe_id} onChange={event => setPairId(event.target.value)}>{pairs.map((pair, index) => <option key={pair.after.probe_id} value={pair.after.probe_id}>Question {index + 1} · {pair.after.category.replaceAll('_', ' ')}</option>)}</select>}</div>
        {comparison ? <div className="evidence-surface"><BeforeAfterComparison pair={comparison} checkpointLabel={result.v3 ? 'ATU v3 checkpoint' : 'ATU v2 checkpoint'} /></div> : <div className="studio-empty"><Search /><h3>No paired responses were exported.</h3><p>Inspect the available recovery tests or export the full run.</p></div>}
        <div className="studio-note"><AlertCircle size={18} /><p>Finishing a job does not establish complete forgetting. These checks measure a limited set of questions; refusal alone is insufficient evidence of deletion.</p></div>
      </>}
      {tab === 'Privacy discovery' && <PrivacyDiscovery report={discovery} />}
      {tab === 'Attempts' && <><div className="studio-section-heading"><div><span className="studio-eyebrow">TRAINING & SELECTION</span><h2>How ATU chose the result</h2><p>Every exported attempt. Lower answer likelihood can still leave a fact recoverable. The final recovery checks determine what remains exposed.</p></div></div>{result.v3?.selection_rationale && <div className="studio-note review-selection"><SlidersHorizontal size={18} /><div><strong>Selection explanation</strong><p>{result.v3.selection_rationale}</p></div></div>}{result.v3?.trials.length ? <div className="attempt-list">{result.v3.trials.map(trial => <AttemptCard key={trial.trial_index} trial={trial} />)}</div> : <div className="studio-empty"><Activity /><h3>No V3 attempts exported for this run.</h3><p>Any available controller trace is included in your results download.</p></div>}</>}
      {tab === 'Recovery tests' && <><div className="studio-section-heading"><div><span className="studio-eyebrow">FINAL CHECKPOINT AUDIT</span><h2>Challenge the checkpoint</h2><p>{result.attacks.length} exported tests. Raw recovery and calibrated suppression are separate measurements.</p></div></div><div className="studio-tabs compact" role="group" aria-label="Filter live recovery tests">{['All', 'Recovered', 'Suppressed', 'Uncertain'].map(value => <button key={value} aria-pressed={filter === value} className={filter === value ? 'active' : ''} onClick={() => { setFilter(value); setLimit(8); }}>{value}</button>)}</div><p className="review-filter-count" aria-live="polite">Showing {Math.min(limit, filtered.length)} of {filtered.length} {filter === 'All' ? 'exported' : filter.toLowerCase()} tests</p>{filtered.length ? <div className="attack-list evidence-surface">{filtered.slice(0, limit).map(pair => <RedTeamAttackCard key={pair.after.probe_id} pair={pair} />)}</div> : <div className="studio-empty"><Swords /><h3>No tests in this filter.</h3><p>Choose another filter to inspect the available evidence.</p></div>}{filtered.length > limit && <button className="button secondary load-more" onClick={() => setLimit(value => value + 8)}>Show more tests<ArrowRight size={15} /></button>}</>}
      {tab === 'Run details' && <div className="studio-card run-details"><h2>Run record</h2><dl><dt>Requested method</dt><dd>{result.provenance?.method === 'auto' || job.settings?.method === 'auto' ? 'Automatic · adaptive selection' : methodLabel(String(result.provenance?.method || job.settings?.method || 'Not recorded'))}</dd><dt>Selection explanation</dt><dd>{result.v3?.selection_rationale || 'Not recorded'}</dd><dt>Strategy</dt><dd>{priorityLabel(result.provenance?.priority || job.settings?.priority)}</dd><dt>Training budget</dt><dd>{typeof trainingBudget === 'number' && Number.isFinite(trainingBudget) ? trainingBudget > 0 ? trainingBudget + ' seconds · training only' : 'Profile default' : 'Not reported'}</dd><dt>Selected facts</dt><dd>{requestedFacts ?? 'Not reported'}</dd><dt>Evaluation scope</dt><dd>{result.evaluation_scope === 'preliminary_screening' ? 'Preliminary screening' : result.evaluation_scope === 'full_experiment' ? 'Full experiment' : 'Original run settings'}</dd><dt>Baseline controls reused</dt><dd>{baselineControls ? Object.values(baselineControls).filter(control => control.cache_hit).length + ' / ' + Object.keys(baselineControls).length : 'Not recorded'}</dd><dt>Run ID</dt><dd>{job.job_id}<CopyValue value={job.job_id} /></dd><dt>Checkpoint</dt><dd><code>{result.checkpoint_path || 'Not reported'}</code>{result.checkpoint_path && <CopyValue value={result.checkpoint_path} />}</dd><dt>Checkpoint hash</dt><dd><code>{result.checkpoint_hash || 'Not reported'}</code>{result.checkpoint_hash && <CopyValue value={result.checkpoint_hash} />}</dd><dt>Scientific status</dt><dd>{result.unlearning_status ?? result.v3?.status ?? 'Not reported'}</dd><dt>Total elapsed time</dt><dd>{formatDuration(job.elapsed_seconds)}</dd><dt>Pipeline computation</dt><dd>{formatDuration(result.duration_seconds)}</dd><dt>Discovery findings</dt><dd>{result.facts.length}</dd><dt>Recovery tests</dt><dd>{result.attacks.length}</dd></dl><button className="button secondary" onClick={() => downloadJson(job, job.job_id + '-results.json')}><Download size={16} />Download complete record</button></div>}
    </section>
  </div>;
}

export function Metric({ icon, value, label, detail }: { icon: React.ReactNode; value: string; label: string; detail: string }) {
  return <article className="metric-card"><div className="metric-icon">{icon}</div><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function AttemptCard({ trial }: { trial: V3Attempt }) {
  const details = trial.metrics.details;
  const record = (value: unknown): Record<string, unknown> | null => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null;
  const rejected = record(details?.rejected_metrics);
  const rejectedDetails = record(rejected?.details);
  const rejectedQuality = record(rejectedDetails?.retain_quality_check);
  const hasRejectedQuality = rejectedQuality?.enabled === true && rejectedQuality.metric === 'mean_rougeL_against_reference';
  const rawDecision = details?.feedback_decision;
  const decision = rawDecision && typeof rawDecision === 'object' && !Array.isArray(rawDecision)
    ? rawDecision as Record<string, unknown> : null;
  const action = typeof decision?.action === 'string' ? decision.action : '';
  const decisionLabels: Record<string, string> = { ADJUST_SETTINGS: 'Adjust settings', SWITCH_METHOD: 'Try another method',
    STOP_CONVERGED: 'Stop: development checks passed', STOP_TRIAL_LIMIT: 'Stop: attempt limit',
    STOP_TIME_BUDGET: 'Stop: time budget', STOP_STEP_BUDGET: 'Stop: update limit' };
  const changes = decision?.settings_changed && typeof decision.settings_changed === 'object'
    ? Object.entries(decision.settings_changed as Record<string, unknown>).flatMap(([key, value]) => {
      if (!value || typeof value !== 'object') return [];
      const change = value as Record<string, unknown>;
      return typeof change.before === 'number' && Number.isFinite(change.before)
        && typeof change.after === 'number' && Number.isFinite(change.after)
        ? [{ key, before: change.before, after: change.after }] : [];
    }) : [];
  const kept = details?.kept_checkpoint_changed;
  const steps = details?.optimizer_steps;
  const updateNote = steps === 0 ? 'No optimizer updates completed. This attempt did not train the model.'
    : kept === false ? 'No changed checkpoint was kept. Updates may have been rolled back by protection checks.'
    : kept === true ? 'Changed model weights were kept for evaluation.'
    : details?.rolled_back === true ? 'Protection checks rolled back updates. The export does not report whether earlier changes were kept.'
    : 'Checkpoint update details were not recorded in this version.';
  const safe = typeof trial.metrics.is_safe === 'boolean' ? trial.metrics.is_safe : undefined;
  const rolledBack = trial.status.startsWith('ROLLED_BACK') || (details?.rolled_back === true && kept === false);
  const executionFailed = trial.status.startsWith('FAILED');
  const guardTone = executionFailed ? 'red' : rolledBack || kept === false ? 'amber' : safe === true ? 'green' : safe === false ? 'red' : '';
  const guardLabel = executionFailed ? 'Attempt failed' : rolledBack ? 'Update rolled back' : kept === false ? 'No changed checkpoint kept' : safe === true ? 'Kept checkpoint passed guards' : safe === false ? 'Kept checkpoint failed guards' : 'Guard status not recorded';
  return <article className="studio-card attempt-card">
    <div className="attempt-number" aria-label={'Attempt ' + trial.trial_index}>{String(trial.trial_index).padStart(2, '0')}</div>
    <div className="attempt-main"><div className="attempt-heading"><h3>{methodLabel(trial.method)}</h3><span className={'studio-badge ' + guardTone}>{guardLabel}</span></div>
      <p className="studio-caption"><strong>Execution:</strong> {trial.status.replaceAll('_', ' ')}</p>
      <p>{trial.adaptation_applied || trial.status.replaceAll('_', ' ')}</p>
      <div className={'attempt-update-note ' + (steps === 0 || kept === false ? 'attention' : '')}><Activity size={15} /><span>{updateNote}</span></div>
      <p className="studio-caption">Forgetting and quality scores describe the checkpoint kept after protection checks{rolledBack ? '. Update counts include training that was later discarded' : ''}.</p>
      <div className="attempt-readings"><span>Optimizer updates <strong>{count(steps)}</strong></span><span>Training time <strong>{duration(details?.training_budget_used_seconds ?? details?.method_execution_seconds)}</strong></span><span>Likelihood suppression <strong>{measuredPercent(trial.metrics.forget_suppressed_ratio)}</strong></span><span>Development leakage <strong>{measuredPercent(trial.metrics.probe_leak_rate)}</strong></span><span>Retain log-probability drop <strong>{typeof trial.metrics.retain_log_prob_drop === 'number' && Number.isFinite(trial.metrics.retain_log_prob_drop) ? trial.metrics.retain_log_prob_drop.toFixed(4) : 'Not measured'}</strong></span></div>
      <div className="attempt-readings"><span>Retain answer quality decline <strong>{details?.retain_quality_check?.enabled ? measuredPercent(details.retain_quality_check.relative_drop) : 'Not measured'}</strong></span><span>Answer quality limit <strong>{details?.retain_quality_check?.enabled ? measuredPercent(details.retain_quality_check.limit) : 'Not measured'}</strong></span></div>
      {rejected && <details className="attempt-feedback"><summary>Inspect the rejected candidate</summary><p>This candidate was rejected. Its measurements are separate from the kept checkpoint shown above.</p>{typeof rejected.verdict === 'string' && <p><strong>Recorded rejection:</strong> {rejected.verdict.replaceAll('_', ' ')}</p>}{hasRejectedQuality ? <div className="attempt-readings"><span>Original answer overlap <strong>{measuredPercent(rejectedQuality.before)}</strong></span><span>Rejected answer overlap <strong>{measuredPercent(rejectedQuality.after)}</strong></span><span>Rejected quality decline <strong>{measuredPercent(rejectedQuality.relative_drop)}</strong></span><span>Quality loss limit <strong>{measuredPercent(rejectedQuality.limit)}</strong></span></div> : <p className="studio-caption">Rejected-candidate answer-quality measurements were not recorded.</p>}</details>}
      {action && <details className="attempt-feedback"><summary>Next decision: {decisionLabels[action] || action.replaceAll('_', ' ')}</summary>
        {typeof decision?.reason === 'string' && <p>{decision.reason}</p>}
        {typeof decision?.next_method === 'string' && <p>Next method: {methodLabel(decision.next_method)}</p>}
        {changes.length > 0 && <div className="attempt-readings">{changes.map(change => <span key={change.key}>{({ lr: 'Learning rate', beta: 'NPO beta', retain_weight: 'Retain weight', leak_boost: 'Leaking-fact priority', epochs: 'Epochs' } as Record<string, string>)[change.key] || change.key}<strong>{Number(change.before.toPrecision(4))} → {Number(change.after.toPrecision(4))}</strong></span>)}</div>}
        <p className="studio-caption">Decision uses development checks. Final test responses do not select the next attempt.</p>
      </details>}
      <span className="studio-caption">Kept checkpoint verdict: {trial.metrics.verdict.replaceAll('_', ' ')}</span>
    </div>
  </article>;
}

function CopyValue({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  return <button className="icon-button" aria-label={failed ? 'Copy unavailable. Select the adjacent text to copy it.' : copied ? 'Copied' : 'Copy ' + value} title={failed ? 'Copy unavailable; select the text to copy it.' : copied ? 'Copied' : 'Copy'} onClick={async () => { try { await navigator.clipboard.writeText(value); setFailed(false); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { setFailed(true); } }}>{copied ? <Check size={14} /> : failed ? <AlertCircle size={14} /> : <Copy size={14} />}</button>;
}
