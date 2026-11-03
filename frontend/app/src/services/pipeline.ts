import type { ExecutionMode, LiveHyperparameters, LiveJobStatus } from '../types';
import { isRetainQualityCheck } from './retainQuality.ts';

export class PipelineError extends Error {
  jobId?: string;
  httpStatus?: number;
  constructor(message: string, jobId?: string, httpStatus?: number) { super(message); this.jobId = jobId; this.httpStatus = httpStatus; }
}

export function validateJob(value: unknown): LiveJobStatus {
  const job = value as LiveJobStatus;
  if (!job || typeof job.job_id !== 'string' || typeof job.author_id !== 'string'
    || typeof job.author_name !== 'string' || !['RUNNING', 'CANCELLING', 'COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status)
    || !['fast', 'full'].includes(job.mode) || !Number.isFinite(job.progress)
    || !Number.isFinite(job.elapsed_seconds) || typeof job.current_step !== 'string'
    || typeof job.stage !== 'string' || !Array.isArray(job.logs) || !job.logs.every(line => typeof line === 'string')) {
    throw new PipelineError('The server returned an unsupported run status. Reconnect to try again.');
  }
  const result = job.result;
  if ((job.status === 'COMPLETED' || result != null) && (!result || !result.entity || typeof result.entity.name !== 'string'
    || !Array.isArray(result.facts) || !Array.isArray(result.attacks) || !Array.isArray(result.trace)
    || !result.audit || typeof result.checkpoint_hash !== 'string'
    || (result.v3 && !Array.isArray(result.v3.trials)))) {
    throw new PipelineError('The completed run is missing its results. Reconnect to retrieve them.');
  }
  if (job.status === 'COMPLETED' && result && (!result.facts.every(fact => fact && typeof fact.fact_id === 'string' && typeof fact.attribute_key === 'string' && typeof fact.target_value === 'string' && typeof fact.verdict === 'string' && Array.isArray(fact.leaking_styles) && Array.isArray(fact.sample_responses) && fact.sample_responses.every(sample => sample && typeof sample.style === 'string' && typeof sample.prompt === 'string' && typeof sample.response === 'string') && fact.canonical_qa && typeof fact.canonical_qa.question === 'string')
      || !result.trace.every(round => round && typeof round === 'object')
      || !result.attacks.every(pair => pair && pair.after && typeof pair.after.prompt === 'string'
        && typeof pair.after.probe_id === 'string' && typeof pair.after.response_text === 'string' && typeof pair.after.category === 'string' && typeof pair.after.verdict === 'string' && Array.isArray(pair.after.target_facts) && Array.isArray(pair.after.recovered_facts)
        && (!pair.before || typeof pair.before.prompt === 'string' && typeof pair.before.response_text === 'string')
        && (!pair.base || typeof pair.base.prompt === 'string' && typeof pair.base.response_text === 'string'))
      || result.v3?.trials.some(trial => !trial || !trial.metrics || typeof trial.metrics !== 'object'))) {
    throw new PipelineError('The saved run contains incomplete evidence. Export the original record for inspection.');
  }
  if (result?.audit?.retain_quality_check != null && !isRetainQualityCheck(result.audit.retain_quality_check)) {
    throw new PipelineError('The retain answer-quality measurement is incomplete or invalid. Export the run for inspection.');
  }
  return job;
}

export async function triggerLiveUnlearning(
  authorId: string,
  mode: ExecutionMode = 'fast',
  hyperparameters?: LiveHyperparameters
): Promise<{ jobId: string; authorName: string; authorId?: string }> {
  const payload: Record<string, unknown> = { author_id: authorId, mode, engine_version: hyperparameters?.engine_version ?? 'v3' };
  for (const key of ['method', 'priority', 'training_budget_seconds', 'fact_indices', 'custom_entity'] as const) {
    if (hyperparameters?.[key] !== undefined) payload[key] = hyperparameters[key];
  }
  if (payload.custom_entity) delete payload.author_id;
  if (hyperparameters?.retain_max_drop !== undefined) {
    payload.retain_max_drop = hyperparameters.retain_max_drop;
  }
  if (hyperparameters?.retain_quality_max_drop !== undefined) {
    payload.retain_quality_max_drop = hyperparameters.retain_quality_max_drop;
  }
  if (hyperparameters?.retain_weight !== undefined) {
    payload.retain_weight = hyperparameters.retain_weight;
  }

  const response = await fetch('/api/run_pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(15000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: 'Failed to launch live unlearning.' }));
    throw new PipelineError(err.error || `HTTP error ${response.status}`, err.job_id, response.status);
  }

  const data = await response.json();
  if (typeof data.job_id !== 'string' || typeof data.author_name !== 'string') {
    throw new PipelineError('The server did not return a run ID. Please check the connection.');
  }
  return { jobId: data.job_id, authorName: data.author_name, authorId: data.author_id };
}

export async function fetchPipelineStatus(jobId: string, signal?: AbortSignal): Promise<LiveJobStatus> {
  const response = await fetch(`/api/pipeline_status?job_id=${encodeURIComponent(jobId)}`, {
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    throw new PipelineError(response.status === 404
      ? 'This run is no longer available on the server. Saved results remain in your history.'
      : 'The server connection was interrupted. Monitoring will reconnect automatically.', undefined, response.status);
  }
  return validateJob(await response.json());
}

export async function cancelPipeline(jobId: string): Promise<LiveJobStatus> {
  const response = await fetch('/api/cancel_pipeline', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ job_id: jobId }), signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new PipelineError('The stop request could not be confirmed. Monitoring continues; retry Stop.', undefined, response.status);
  return validateJob(await response.json());
}
export async function fetchJobHistory(): Promise<LiveJobStatus[]> {
  const response = await fetch('/api/jobs', { signal: AbortSignal.timeout(10000) });
  if (!response.ok) return [];
  const body = await response.json();
  if (!Array.isArray(body.jobs)) return [];
  return body.jobs.flatMap((value: unknown) => { try { return [validateJob(value)]; } catch { return []; } });
}
