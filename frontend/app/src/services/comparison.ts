import type { LiveJobStatus } from '../types';

export function comparisonNotes(left: LiveJobStatus, right: LiveJobStatus) {
  const a = left.result, b = right.result, notes: string[] = [];
  if (!a || !b) return ['Both runs need completed results.'];
  if (a.provenance?.scoring_revision !== b.provenance?.scoring_revision || !a.provenance?.scoring_revision || !b.provenance?.scoring_revision) notes.push('Scoring versions differ or are not recorded; recovery counts may not be directly comparable.');
  if (left.author_id !== right.author_id) notes.push('Different entities: this is a descriptive comparison.');
  if (!a.provenance?.target_checkpoint_hash || !b.provenance?.target_checkpoint_hash) notes.push('The original checkpoint identity was not recorded in both runs.');
  else if (a.provenance.target_checkpoint_hash !== b.provenance.target_checkpoint_hash) notes.push('Different original model checkpoints.');
  if (!a.provenance?.selected_questions || !b.provenance?.selected_questions) notes.push('Exact selected facts were not recorded in both runs.');
  else if (JSON.stringify(a.provenance.selected_questions) !== JSON.stringify(b.provenance.selected_questions)) notes.push('Different selected facts.');
  if (left.mode !== right.mode || a.evaluation_scope !== b.evaluation_scope) notes.push('Different evaluation profiles or coverage.');
  if (!a.provenance?.probe_protocol_revision || !b.provenance?.probe_protocol_revision
      || a.provenance.probe_protocol_revision !== b.provenance.probe_protocol_revision) notes.push('Recovery protocol versions differ or are not recorded.');
  if (a.provenance?.seed == null || b.provenance?.seed == null || a.provenance.seed !== b.provenance.seed) notes.push('Random seeds differ or are not recorded.');
  const safety = (job: LiveJobStatus, key: 'retain_max_drop' | 'retain_weight') => job.result?.provenance?.[key] ?? job.settings?.[key];
  if (['retain_max_drop', 'retain_weight'].some(key => {
    const setting = key as 'retain_max_drop' | 'retain_weight';
    const x = safety(left, setting), y = safety(right, setting);
    return typeof x !== 'number' || !Number.isFinite(x) || typeof y !== 'number' || !Number.isFinite(y) || x !== y;
  })) notes.push('Retain safety settings differ or are not fully reported.');
  const qualityLimit = (job: LiveJobStatus) => job.result?.provenance?.retain_quality_max_drop ?? job.settings?.retain_quality_max_drop;
  const qualityA = qualityLimit(left), qualityB = qualityLimit(right);
  if ((qualityA != null || qualityB != null) && (typeof qualityA !== 'number' || typeof qualityB !== 'number' || !Number.isFinite(qualityA) || !Number.isFinite(qualityB) || qualityA !== qualityB)) notes.push('Retain answer quality limits differ or are not recorded in both runs.');
  const checkA = a.audit.retain_quality_check, checkB = b.audit.retain_quality_check;
  if (checkA?.enabled || checkB?.enabled) {
    if (!checkA?.enabled || !checkB?.enabled || !checkA.cohort_sha256 || !checkB.cohort_sha256 || checkA.cohort_sha256 !== checkB.cohort_sha256
        || checkA.sample_count !== checkB.sample_count || checkA.token_cap !== checkB.token_cap) notes.push('Retain answer quality samples or generation settings differ or are not fully recorded.');
  }
  const budgetA = a.provenance?.training_budget_seconds, budgetB = b.provenance?.training_budget_seconds;
  if (budgetA == null || budgetB == null) notes.push('Training budgets are not fully reported.');
  else if (budgetA !== budgetB) notes.push('Different training budgets.');
  const cohort = (job: LiveJobStatus) => job.result?.attacks.map(pair => [pair.after.prompt, pair.after.target_facts, pair.before?.verdict, pair.base?.verdict]);
  if (JSON.stringify(cohort(left)) !== JSON.stringify(cohort(right))) notes.push('Recovery questions or control results differ. Compare raw counts carefully.');
  if (a.audit.retain_utility_examples == null || b.audit.retain_utility_examples == null
      || a.audit.retain_utility_examples !== b.audit.retain_utility_examples
      || a.audit.retain_generation_token_cap !== b.audit.retain_generation_token_cap) notes.push('Retain-answer coverage differs or is not fully reported.');
  return notes;
}
