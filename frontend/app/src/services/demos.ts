import type { LiveJobStatus, PairedAttack } from '../types';
import { validateJob } from './pipeline.ts';

export interface DemoCase {
  id: string; title: string; subtitle?: string; purpose: string;
  status: string; job_id: string | null; job: LiveJobStatus | null;
}
export interface DemoCollection {
  schemaVersion: number; collection_id: string; title: string; description: string;
  updated_at: string; archive_url?: string; cases: DemoCase[];
}

export function parseCollection(value: unknown): DemoCollection {
  const data = value as DemoCollection | null;
  if (!data || data.schemaVersion !== 1 || typeof data.collection_id !== 'string'
      || typeof data.title !== 'string' || typeof data.description !== 'string'
      || !Array.isArray(data.cases) || data.cases.length !== 3) {
    throw new Error('The demo collection is incomplete or unsupported.');
  }
  const ids = new Set<string>();
  for (const item of data.cases) {
    if (!item || typeof item.id !== 'string' || !item.id || ids.has(item.id)
        || typeof item.title !== 'string' || typeof item.purpose !== 'string'
        || !['PENDING', 'RUNNING', 'CANCELLING', 'COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status)) {
      throw new Error('A demo is missing its description or has an invalid status.');
    }
    ids.add(item.id);
    if (item.job) {
      const job = validateJob(item.job);
      if (job.job_id !== item.job_id || job.mode !== 'full' || job.status !== item.status) {
        throw new Error('A demo snapshot does not match its Full experiment.');
      }
    } else if (item.status === 'COMPLETED') throw new Error('A completed demo is missing its evidence.');
  }
  return data;
}

/** A missing count is unknown, including when only some attempts exported it. */
export function optimizerUpdates(job: LiveJobStatus): number | null {
  const attempts = job.result?.v3?.trials;
  if (!attempts?.length) return null;
  const values = attempts.map(attempt => attempt.metrics?.details?.optimizer_steps);
  return values.every(value => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0)
    ? values.reduce<number>((sum, value) => sum + (value as number), 0) : null;
}

/** Only identical prompts can support a before/after preview. Keep leaks visible first. */
export function previewPair(job: LiveJobStatus): PairedAttack | undefined {
  const pairs = job.result?.attacks.filter(pair => pair.before && pair.after
    && pair.before.prompt === pair.after.prompt) ?? [];
  return pairs.find(pair => pair.calibration === 'RESIDUAL_LEAKAGE')
    ?? pairs.find(pair => pair.calibration === 'VERIFIED_SUPPRESSION') ?? pairs[0];
}
