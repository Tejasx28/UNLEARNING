import type { RetainQualityCheck } from '../types';

/** Missing legacy measurements remain missing; they are never converted to zero. */
export function isRetainQualityCheck(value: unknown): value is RetainQualityCheck {
  if (!value || typeof value !== 'object') return false;
  const check = value as RetainQualityCheck;
  const bounded = (number: unknown, max: number) => number === null || typeof number === 'number' && Number.isFinite(number) && number >= 0 && number <= max;
  return typeof check.enabled === 'boolean' && typeof check.metric === 'string'
    && (!check.enabled || check.metric === 'mean_rougeL_against_reference')
    && [check.before, check.after, check.relative_drop].every(number => bounded(number, 1))
    && bounded(check.limit, .3) && (check.passed === null || typeof check.passed === 'boolean')
    && Number.isInteger(check.sample_count) && check.sample_count >= 0
    && Number.isInteger(check.token_cap) && check.token_cap > 0
    && (!check.enabled || check.passed !== true || (typeof check.before === 'number' && check.before > 0
      && typeof check.after === 'number' && typeof check.relative_drop === 'number'
      && typeof check.limit === 'number' && check.relative_drop <= check.limit + 1e-12 && check.sample_count > 0));
}
