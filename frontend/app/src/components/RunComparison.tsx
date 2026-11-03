import { useState } from 'react';
import { ArrowLeft, Download, GitCompareArrows, AlertCircle, ArrowDown } from 'lucide-react';
import type { LiveJobStatus } from '../types';
import { formatDuration, measuredPercent, methodLabel, runOutcome, priorityLabel } from '../services/jobs';
import { downloadJson } from '../services/research';
import { comparisonNotes } from '../services/comparison';
import '../review.css';

const isCount = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const count = (value: unknown) => isCount(value) ? String(value) : 'Not recorded';

export function RunComparison({ runs, onBack }: { runs: LiveJobStatus[]; onBack: () => void }) {
  const completed = runs.filter(job => job.status === 'COMPLETED' && job.result);
  const [leftId, setLeft] = useState(completed[0]?.job_id || '');
  const [rightId, setRight] = useState(completed[1]?.job_id || '');
  const left = completed.find(job => job.job_id === leftId) ?? completed[0];
  const right = completed.find(job => job.job_id === rightId && job.job_id !== left?.job_id) ?? completed.find(job => job.job_id !== left?.job_id);
  const notes = left && right ? comparisonNotes(left, right) : [];
  const values = (job: LiveJobStatus) => {
    const result = job.result!;
    const budget = result.provenance?.training_budget_seconds ?? job.settings?.training_budget_seconds;
    return [job.author_name, result.v3 ? 'ATU V3' : 'ATU V2', priorityLabel(result.provenance?.priority || job.settings?.priority),
      job.mode === 'fast' ? 'Quick · preliminary' : 'Full experiment',
      result.provenance?.selected_questions?.length ?? job.settings?.fact_indices?.length ?? 'Not reported',
      isCount(budget) ? budget > 0 ? budget + 's · training only' : 'Profile default' : 'Not reported',
      formatDuration(job.elapsed_seconds), methodLabel(result.v3?.best_method || (result.v3 ? undefined : 'atu_npo')),
      result.v3?.trials.length ?? 'Not reported', result.audit.validated_attacks > 0 ? count(result.audit.verified_suppressions) + ' / ' + count(result.audit.validated_attacks) : 'Unverified',
      result.audit.validated_attacks > 0 ? count(result.audit.residual_leaks) : 'Unverified', result.attacks.length ? count(result.audit.inconclusive_attacks) : 'No tests', measuredPercent(result.audit.retain_utility_rate),
      isCount(result.audit.retain_utility_examples) ? result.audit.retain_utility_examples + ' answers' + (isCount(result.audit.retain_generation_token_cap) ? ' · ' + result.audit.retain_generation_token_cap + ' token cap' : '') : 'Not reported',
      isCount(result.audit.facts_requested) && isCount(result.audit.facts_with_validated_checks) ? `${result.audit.facts_with_validated_checks} / ${result.audit.facts_requested} selected facts` : 'Not recorded',
      result.audit.retain_quality_check?.enabled ? measuredPercent(result.audit.retain_quality_check.relative_drop) : 'Not measured',
      result.audit.retain_quality_check?.enabled ? measuredPercent(result.audit.retain_quality_check.limit) : 'Not measured',
      runOutcome(job).label, result.checkpoint_hash || 'Not recorded'];
  };
  const leftValues = left ? values(left) : [], rightValues = right ? values(right) : [];
  return <div className="studio-page review-comparison"><button className="text-button" onClick={onBack}><ArrowLeft size={16} />Run history</button><div className="studio-heading"><div><span className="studio-eyebrow">SAVED EXPERIMENT EVIDENCE</span><h1>Compare saved runs</h1><p>Two measured outcomes, side by side. Reviewing saved results starts no new computation.</p></div><span className="review-comparison-icon"><GitCompareArrows size={28} /></span></div>
    <p><a className="button secondary small" href="./artifacts/feedback-validation/index.html">Matched V2–V3 validation report →</a></p>
    {completed.length < 2 ? <div className="studio-card studio-empty"><GitCompareArrows /><h2>Two completed runs are needed.</h2><p>Failed and stopped runs stay in history, but have no final scientific result to compare.</p></div> : <><div className="comparison-pickers experiment-options">{[{ name: 'Left run', value: left?.job_id || '', change: setLeft, other: right?.job_id }, { name: 'Right run', value: right?.job_id || '', change: setRight, other: left?.job_id }].map(side => <label key={side.name}>{side.name}<select className="studio-input" aria-label={side.name} value={side.value} onChange={event => side.change(event.target.value)}>{completed.map(job => <option key={job.job_id} value={job.job_id} disabled={job.job_id === side.other}>{job.author_name} · {job.result?.v3 ? 'V3' : 'V2'} · {job.job_id.slice(-8)}</option>)}</select></label>)}</div>
      {left && right && <><div className="review-comparison-summaries">{[left, right].map((job, index) => <article className="studio-card" key={job.job_id}><span className="studio-eyebrow">{index === 0 ? 'LEFT EXPERIMENT' : 'RIGHT EXPERIMENT'}</span><h2>{job.author_name}</h2><p>{methodLabel(job.result?.v3?.best_method || (job.result?.v3 ? undefined : 'atu_npo'))} · {formatDuration(job.elapsed_seconds)}</p><span className={'studio-badge ' + runOutcome(job).tone}>{runOutcome(job).label}</span></article>)}</div><div className={'studio-note ' + (notes.length ? 'amber' : '')}><AlertCircle size={18} /><div><strong>{notes.length ? 'Read these differences before comparing' : 'Recorded inputs and coverage match'}</strong>{notes.length ? <ul>{notes.map(note => <li key={note}>{note}</li>)}</ul> : <p>Differences describe these two runs; they do not establish that one method is consistently better.</p>}</div></div><div className="studio-card comparison-scroll" tabIndex={0} role="region" aria-label="Saved experiment comparison, scroll horizontally for both runs"><table className="comparison-table"><caption>Saved experiment measurements</caption><thead><tr><th scope="col">Measurement</th><th scope="col">Left run · {left.job_id.slice(-8)}</th><th scope="col">Right run · {right.job_id.slice(-8)}</th></tr></thead><tbody>{['Entity', 'Engine', 'Priority', 'Profile', 'Selected facts', 'Training budget', 'Total duration', 'Selected method', 'Attempts', 'Validated suppression', 'Residual leaks', 'Inconclusive tests', 'Retain answer overlap', 'Retain coverage', 'Fact audit coverage', 'Relative retain quality decline', 'Retain quality loss limit', 'Outcome', 'Checkpoint'].map((label, index) => <tr key={label}><th scope="row">{label}</th><td>{leftValues[index]}</td><td>{rightValues[index]}</td></tr>)}</tbody></table></div><div className="review-export-row"><p><ArrowDown size={15} />Total duration includes model loading and evaluation.</p><button className="button secondary" onClick={() => downloadJson({ type: 'SAVED_RUN_COMPARISON', notes, left, right }, 'saved-run-comparison.json')}><Download size={16} />Export comparison</button></div></>}
    </>}
  </div>;
}
