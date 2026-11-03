import type { ExecutionMode, LiveJobStatus } from '../types';
import { validateJob } from './pipeline.ts';

export interface ActiveJob {
  jobId: string;
  authorId: string;
  authorName: string;
  mode: ExecutionMode;
  startedAt: number;
}

const activeKey = 'atu-studio-active-job';

export function readActiveJob(): ActiveJob | null {
  try {
    const value = JSON.parse(localStorage.getItem(activeKey) || 'null');
    return value && typeof value.jobId === 'string' && value.jobId.length > 0 && typeof value.authorId === 'string'
      && typeof value.authorName === 'string' && ['fast', 'full'].includes(value.mode)
      && Number.isFinite(value.startedAt) ? value : null;
  } catch { return null; }
}

export function rememberActiveJob(job: ActiveJob | null) {
  try {
    if (job) localStorage.setItem(activeKey, JSON.stringify(job));
    else localStorage.removeItem(activeKey);
  } catch { /* Monitoring still works when browser storage is unavailable. */ }
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('atu-studio', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('runs', { keyPath: 'job_id' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('Browser run storage is busy.'));
  });
}

/** Browser storage may contain old or interrupted writes. Invalid entries cannot become evidence. */
export function validSavedRuns(values: unknown): LiveJobStatus[] {
  if (!Array.isArray(values)) return [];
  return values.flatMap(value => {
    try {
      const job = validateJob(value);
      return ['RUNNING', 'CANCELLING'].includes(job.status) ? [] : [job];
    } catch { return []; }
  });
}

export async function loadSavedRuns(): Promise<LiveJobStatus[]> {
  const db = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction('runs', 'readonly');
      const request = transaction.objectStore('runs').getAll();
      request.onsuccess = () => resolve(validSavedRuns(request.result));
      request.onerror = () => reject(request.error);
    });
  } finally { db.close(); }
}

export async function saveRun(job: LiveJobStatus): Promise<void> {
  const db = await openDatabase();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction('runs', 'readwrite');
      transaction.objectStore('runs').put(job);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally { db.close(); }
}

export function mergeRun(runs: LiveJobStatus[], job: LiveJobStatus) {
  return [job, ...runs.filter(run => run.job_id !== job.job_id)];
}

export function methodLabel(method?: string) {
  return ({ atu_npo: 'ATU-NPO', npo: 'NPO', rmu: 'RMU', graddiff: 'GradDiff',
    dpo_refusal: 'DPO refusal', ga: 'Gradient ascent' } as Record<string, string>)[method || ''] || method || 'Not reported';
}

export function measuredPercent(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
    ? (value * 100).toFixed(1) + '%' : 'Not measured';
}

export function runOutcome(job: LiveJobStatus) {
  if (job.status === 'CANCELLED') return { label: 'Stopped by you', tone: 'neutral' };
  if (job.status === 'CANCELLING') return { label: 'Stopping', tone: 'amber' };
  if (job.status === 'FAILED') return { label: 'Execution failed', tone: 'red' };
  if (job.status === 'RUNNING') return { label: 'In progress', tone: 'blue' };
  const trials = job.result?.v3?.trials || [];
  const steps = trials.map(trial => trial.metrics.details?.optimizer_steps);
  if (steps.length && steps.every(value => typeof value === 'number') && steps.reduce<number>((sum, value) => sum + (value || 0), 0) === 0) return { label: 'No training updates completed', tone: 'amber' };
  const audit = job.result?.audit;
  if (job.result?.unlearning_status === 'RETAIN_QUALITY_RISK' || (audit?.retain_quality_check?.enabled && audit.retain_quality_check.passed === false)) return { label: 'Retain answer quality check failed', tone: 'red' };
  if ((audit?.residual_leaks ?? 0) > 0 && (audit?.verified_suppressions ?? 0) > 0) return { label: `Partial suppression · ${audit?.verified_suppressions}/${audit?.validated_attacks} checks`, tone: 'amber' };
  if ((audit?.residual_leaks ?? 0) > 0) return { label: 'Residual leakage detected', tone: 'red' };
  if (job.result?.scoring_recheck) return { label: 'Saved responses rechecked · audit incomplete', tone: 'amber' };
  if (typeof audit?.facts_requested === 'number' && typeof audit?.facts_with_validated_checks === 'number'
      && audit.facts_with_validated_checks < audit.facts_requested) return { label: `Audit incomplete · ${audit.facts_with_validated_checks}/${audit.facts_requested} facts checked`, tone: 'amber' };
  if (job.result?.evaluation_scope === 'preliminary_screening') return { label: 'Preliminary check — review results', tone: 'amber' };
  const status = job.result?.unlearning_status ?? job.result?.v3?.status;
  const qualityLimit = job.result?.provenance?.retain_quality_max_drop ?? job.settings?.retain_quality_max_drop;
  if (status === 'SUCCESS' && typeof qualityLimit === 'number' && audit?.retain_quality_check?.passed !== true) return { label: 'Retain answer quality not verified', tone: 'amber' };
  if (status === 'SUCCESS' && (audit?.validated_attacks ?? 0) > 0) {
    const counts = [audit?.validated_attacks, audit?.verified_suppressions, audit?.residual_leaks];
    if (!counts.every(value => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0)
        || audit!.verified_suppressions + audit!.residual_leaks !== audit!.validated_attacks) {
      return { label: 'Verification measurements incomplete', tone: 'amber' };
    }
    return { label: 'Configured checks passed', tone: 'green' };
  }
  if (status === 'SUCCESS') return { label: 'Verification incomplete', tone: 'amber' };
  if (status === 'UNVERIFIED') return { label: 'Verification incomplete', tone: 'amber' };
  return { label: 'Review required', tone: 'amber' };
}

export function outcomeDescription(job: LiveJobStatus) {
  const outcome = runOutcome(job);
  const audit = job.result?.audit;
  if (outcome.label === 'No training updates completed') return 'The run ended before any optimizer update completed. It did not perform a useful training attempt; inspect the budget and attempt details.';
  if ((audit?.validated_attacks ?? 0) === 0) return 'No recovery tests passed the original target/base control checks. Forgetting is unverified for this run.';
  const prefix = job.mode === 'fast' ? 'Preliminary screening. ' : '';
  const counts = `${audit?.verified_suppressions ?? 0} of ${audit?.validated_attacks ?? 0} validated recovery checks were suppressed; ${audit?.residual_leaks ?? 0} still recovered information.`;
  const coverage = typeof audit?.facts_requested === 'number' && typeof audit?.facts_with_validated_checks === 'number'
    ? ` ${audit.facts_with_validated_checks}/${audit.facts_requested} selected facts had validated target/base checks.` : '';
  return prefix + counts + ((audit?.inconclusive_attacks ?? 0) ? ` ${audit?.inconclusive_attacks} other checks were inconclusive.` : '') + coverage + ' Retain protection and forgetting are separate checks.';
}

export function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  const minutes = Math.floor(seconds / 60);
  return minutes ? minutes + 'm ' + Math.floor(seconds % 60) + 's' : Math.floor(seconds) + 's';
}

export function sortRuns(runs: LiveJobStatus[]) {
  return [...runs].sort((a, b) => ((b.start_time ?? Date.parse(b.created_at || '') / 1000) || Number(b.job_id.match(/job_(\d+)/)?.[1]) / 1000 || 0) - ((a.start_time ?? Date.parse(a.created_at || '') / 1000) || Number(a.job_id.match(/job_(\d+)/)?.[1]) / 1000 || 0));
}

export function priorityLabel(value?: string | null) {
  return ({ fast: 'Fast', balanced: 'Balanced', preserve_utility: 'Preserve other knowledge', strict_privacy: 'Privacy priority' } as Record<string, string>)[value || ''] || 'Not reported';
}
