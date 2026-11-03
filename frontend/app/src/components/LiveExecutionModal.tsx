import { useEffect, useRef, useState } from 'react';
import { X, CheckCircle2, AlertTriangle, Terminal, ArrowRight, Loader2, Clock, Search, BrainCircuit, Swords, ShieldCheck, ShieldAlert, Download, RotateCcw } from 'lucide-react';
import type { LiveJobStatus } from '../types';
import type { ActiveJob } from '../services/jobs';
import { formatDuration, runOutcome, outcomeDescription } from '../services/jobs';
import { downloadJson } from '../services/research';
import { useDialog } from '../hooks/useDialog';
import { PrivacyDiscovery } from './PrivacyDiscovery';

export function LiveExecutionModal({ active, job, error, onClose, onComplete, onReconnect, onDismiss, onStop }: {
  active: ActiveJob; job: LiveJobStatus | null; error: string | null;
  onClose: () => void; onComplete: (job: LiveJobStatus) => void;
  onReconnect: () => void; onDismiss: () => void; onStop: () => Promise<void>;
}) {
  const dialog = useDialog(onClose);
  const terminal = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  const finished = job?.status === 'COMPLETED';
  const failed = job?.status === 'FAILED';
  const cancelled = job?.status === 'CANCELLED';
  const cancelling = job?.status === 'CANCELLING';
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState('');
  const estimate = job?.estimate;
  const stop = async () => { if (stopping || cancelling) return; setStopping(true); setStopError(''); try { await onStop(); } catch (failure) { setStopError((failure as Error).message); } finally { setStopping(false); } };
  const unavailable = Boolean(error?.includes('no longer available'));
  const progress = Math.max(0, Math.min(100, job?.progress ?? 0));
  const stages = [{ key: 'init', name: 'Prepare', icon: Clock }, { key: 'discover', name: 'Discover', icon: Search }, { key: 'unlearn', name: 'Unlearn', icon: BrainCircuit }, { key: 'attack', name: 'Challenge', icon: Swords }, { key: 'verify', name: 'Verify', icon: ShieldCheck }];
  const stageIndex = finished ? stages.length : stages.findIndex(stage => stage.key === job?.stage);
  useEffect(() => { if (follow && terminal.current) terminal.current.scrollTop = terminal.current.scrollHeight; }, [job?.logs, follow]);
  return <div className="studio-modal-backdrop" onClick={onClose}><div className="studio-monitor" ref={dialog} role="dialog" aria-modal="true" aria-labelledby="monitor-title" tabIndex={-1} onClick={event => event.stopPropagation()}>
    <div className="monitor-header"><div><span className="studio-eyebrow">LIVE EXPERIMENT</span><h2 id="monitor-title">{active.authorName}</h2><p>{active.mode === 'fast' ? 'Quick check' : 'Full experiment'} · {active.jobId}</p></div><button className="icon-button" aria-label="Hide run monitor" title="Hide monitor; the run continues" onClick={onClose}><X size={20} /></button></div>
    <div className="monitor-progress"><div><span className={'studio-badge ' + (failed ? 'red' : cancelled || cancelling ? 'amber' : finished ? 'blue' : unavailable ? 'amber' : 'green')}>{failed || unavailable || cancelled ? <AlertTriangle size={14} /> : finished ? <CheckCircle2 size={14} /> : <Loader2 size={14} className="spin" />}{cancelled ? 'Stopped' : cancelling ? 'Stopping' : failed ? 'Execution failed' : finished ? 'Execution complete' : unavailable ? 'Run unavailable' : error ? 'Reconnecting' : job ? 'Running' : 'Connecting'}</span><span className="monitor-time"><Clock size={14} />{formatDuration(job?.elapsed_seconds ?? 0)}</span></div><p aria-live="polite">{job?.current_step || 'Waiting for the first status update…'}</p><div className="monitor-track" role="progressbar" aria-label="Experiment progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><div style={{ width: progress + '%' }} /></div><span className="studio-caption">{Math.round(progress)}% · Stage progress is separate from elapsed time.</span></div>
    <div className="monitor-timing"><strong>{cancelled ? 'Worker stopped; no result is claimed.' : cancelling ? 'Releasing the GPU worker…' : finished || failed ? 'Total duration: ' + formatDuration(job?.elapsed_seconds ?? 0) : estimate ? estimate.over_estimate ? 'Taking longer than the initial estimate.' : 'Estimated remaining: ' + formatDuration(estimate.remaining_low_seconds) + '–' + formatDuration(estimate.remaining_high_seconds) : 'Gathering timing information…'}</strong>{estimate && <small>{estimate.source === 'similar_completed_runs' ? 'Based on ' + estimate.sample_count + ' similar completed runs.' : 'Planning range. The first run and model loading can take longer.'}</small>}<dl>{Object.entries(job?.stage_durations_seconds || {}).map(([stage, seconds]) => <div key={stage}><dt>{stage}</dt><dd>{formatDuration(seconds)}</dd></div>)}{!finished && !failed && !cancelled && job && <div><dt>{job.stage} · current</dt><dd>{formatDuration(job.stage_elapsed_seconds ?? 0)}</dd></div>}</dl></div>
    {stopError && <div className="studio-note red" role="alert">{stopError}</div>}
    {job?.persistence_error && <div className="studio-note amber" role="status">Local history could not be saved. This run continues in memory; export its evidence to keep a copy.</div>}
    {job?.stage === 'init' && !failed && !cancelled && !cancelling && <p className="runtime-preparation-note">Preparing the runtime comes before GPU model loading. The first launch may take longer; the step above updates as each library becomes ready.</p>}
    <ol className="monitor-stages">{stages.map((stage, index) => <li key={stage.key} className={index < stageIndex ? 'done' : index === stageIndex && !failed && !cancelled ? 'current' : ''}><span>{index < stageIndex ? <CheckCircle2 size={18} /> : <stage.icon size={18} />}</span>{stage.name}</li>)}</ol>
    {error && <div className="studio-note amber" role="alert"><AlertTriangle size={18} /><div><strong>{unavailable ? 'Run record unavailable' : 'Monitoring connection interrupted'}</strong><p>{error} {unavailable ? 'Dismiss the monitor to return to the workspace.' : 'A connection error does not cancel the GPU job.'}</p><button className="text-button" onClick={onReconnect}><RotateCcw size={14} />Reconnect now</button></div></div>}
    {failed && <div className="studio-note red" role="alert"><AlertTriangle size={18} /><p>{job.error || 'The backend could not finish this run.'}</p></div>}
    {finished && <div className={'studio-note ' + runOutcome(job).tone}>{runOutcome(job).tone === 'red' || runOutcome(job).tone === 'amber' ? <ShieldAlert size={19} /> : <ShieldCheck size={19} />}<div><strong>{runOutcome(job).label}</strong><p>{outcomeDescription(job)}</p></div></div>}
    {job?.discovery && <details className="monitor-discovery"><summary>Privacy Leakage Discovery · {job.discovery.facts.length} {job.discovery.facts.length === 1 ? 'fact' : 'facts'} tested · View evidence</summary><PrivacyDiscovery report={job.discovery} /></details>}
    <div className="monitor-log"><div className="monitor-log-header"><Terminal size={15} /><strong>Execution log</strong><button aria-pressed={follow} onClick={() => setFollow(!follow)}>{follow ? 'Auto-scroll on' : 'Auto-scroll off'}</button><button aria-label="Download execution log" onClick={() => downloadJson({ job_id: active.jobId, logs: job?.logs ?? [] }, active.jobId + '-log.json')}><Download size={14} /></button></div><div className="monitor-log-body" ref={terminal} onScroll={() => { const el = terminal.current; if (el && el.scrollHeight - el.scrollTop - el.clientHeight > 50 && follow) setFollow(false); }}>{job?.logs.length ? job.logs.map((line, index) => <div key={index}><span>›</span>{line}</div>) : <p>No log messages received yet.</p>}</div></div>
    <div className="monitor-footer"><span>{cancelled ? 'Stopped; no completed unlearning result is claimed.' : finished ? 'Results are ready to inspect.' : failed ? 'The original target is separate from this attempt.' : 'You can hide this window. Monitoring continues in the workspace.'}</span>{finished ? <button className="button primary" onClick={() => onComplete(job)}>Open results<ArrowRight size={16} /></button> : failed || cancelled || error?.includes('no longer available') ? <button className="button secondary" onClick={onDismiss}>Dismiss monitor</button> : <div className="inline-actions"><button className="button secondary stop-experiment" disabled={stopping || cancelling || !job} onClick={() => { void stop(); }}>{stopping || cancelling ? 'Stopping…' : 'Stop experiment'}</button><button className="button secondary" onClick={onClose}>Continue in background</button></div>}</div>
  </div></div>;
}
