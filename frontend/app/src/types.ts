export type Stage = 'discover' | 'select' | 'unlearn' | 'attack' | 'verify';
export type Role = 'FORGET_TARGET' | 'RETAIN_CONTROL' | 'NEGATIVE_CONTROL' | 'DATASET_AUTHOR';
export interface DatasetAuthor { id: string; name: string; name_status: 'IN_DATASET' | 'NOT_PROVIDED' | 'CUSTOM_INPUT'; row_start: number; qa: { question: string; answer: string }[] }
export interface TofuCatalog { schemaVersion: number; source: { dataset: string; split: string; revision: string; url: string; sha256: string; rows: number; authors: number; named_authors: number; name_method: string }; authors: DatasetAuthor[] }
export interface Entity { id: string; name: string; role: Role; badge: string; facts_count: number; description: string; dataset?: DatasetAuthor }
export interface Evidence { style: string; prompt: string; response: string; recovered: string | boolean; verdict?: string; is_degenerate?: boolean; explanation?: string }
export interface Fact {
  fact_id: string; entity_name: string; attribute_key: string; target_value: string;
  verdict: 'CONFIRMED_LEAK' | 'PARTIAL_LEAK' | 'NOT_EXPOSED' | 'UNCERTAIN';
  exposure_score: number; probes_tested: number; probes_leaked: number;
  leaking_styles: string[]; sample_responses: Evidence[];
  canonical_qa: { question: string; answer: string };
  metadata: { is_control_retain?: boolean; is_synthetic_control?: boolean };
}
export interface DevProbe { probe_id: string; category: string; prompt: string; gen_text: string; leaked: boolean; recovered_facts: string[] }
export interface Round {
  round: number; action: string; active_targets: number; suppressed_targets: number;
  stubborn_targets: number; leaking_targets?: number; unlearning_targets?: number;
  mean_forget_lp: number; retain_lp: number; retain_drift: number; retain_safe?: boolean;
  should_stop?: boolean; stop_reason?: string; decision: string; probe_details?: DevProbe[];
  dev_probes_leaking?: number; total_dev_probes?: number;
}
export interface TargetState { question: string; answer: string; state: string; weight: number; initial_log_prob: number; current_log_prob: number; floor_threshold: number; probe_leak: boolean; leaking_probes: string[] }
export interface Attack {
  probe_id: string; category: string; prompt: string; target_facts: string[];
  response_text: string; verdict: string; defense_type: string; recovered_facts: string[];
  is_degenerate: boolean; explanation: string; jailbreak_wrapper: string;
}
export interface AttackReport { checkpoint_hash: string; target_entity: string; total_attacks: number; results: Attack[]; verdict_counts: Record<string, number> }
export type Calibration = 'VERIFIED_SUPPRESSION' | 'RESIDUAL_LEAKAGE' | 'INCONCLUSIVE';
export interface PairedAttack { after: Attack; before?: Attack; base?: Attack; calibration?: Calibration; source_question?: string; source_fact_id?: string }
export interface RetainQualityCheck {
  enabled: boolean; metric: string; before: number | null; after: number | null;
  relative_drop: number | null; limit: number | null; sample_count: number; token_cap: number;
  passed: boolean | null; cohort_sha256?: string; reason?: string;
}
export interface Audit { total_attacks: number; validated_attacks: number; inconclusive_attacks: number; verified_suppressions: number; residual_leaks: number; retain_utility_rate: number; retain_utility_examples?: number; retain_generation_token_cap?: number; retain_quality_check?: RetainQualityCheck | null; is_control_retain: boolean; facts_requested?: number; facts_with_validated_checks?: number }
export interface Bundle {
  schemaVersion: number;
  sources: Record<string, { source: string; local: string; sha256: string }>;
  publishedLabels: Record<string, Calibration>;
  publishedAudit: { validated: string; suppression: string; residual: string; inconclusive: string; retain: string; degeneracy: string; checkpoint: string; totalSuite: number };
  data: {
    discovery: { facts_evidence: Fact[]; summary: Record<string, number>; checkpoint_hash: string; timestamp: string };
    trace: { config: Record<string, number>; decision_trace: Round[]; final_target_states: Record<string, TargetState> };
    evaluation: { checkpoint_hash: string; retain_rougeL: number; sample_retain_pred: string; rounds_completed: number; stop_reason: string; [key: string]: unknown };
    targetEvaluation: { retain_rougeL: number; sample_retain_pred: string; [key: string]: unknown };
    pipeline: { timestamp: string; overall_verdict: string; unlearning_summary: { status: string; stop_reason: string; rounds_completed: number }; redteam_summary: { total_validated_attacks: number; total_verified_suppressions: number; total_residual_leaks: number; retain_utility_rate: number; per_author: Record<string, Audit> } };
    calibratedReport: string;
    [key: string]: unknown;
  };
}
export interface Draft { name: string; facts: { id: number; key: string; value: string; question?: string }[] }
export type StrategyPriority = 'fast' | 'balanced' | 'preserve_utility' | 'strict_privacy';
export type UnlearningMethod = 'auto' | 'atu_npo' | 'rmu' | 'graddiff' | 'dpo_refusal' | 'ga';
export interface CustomEntityInput { name: string; facts: { attribute: string; value: string; question?: string }[] }
export type ExecutionMode = 'fast' | 'full';
export interface V3Attempt {
  trial_index: number; method: string; status: string; adaptation_applied?: string;
  metrics: { verdict: string; forget_suppressed_ratio: number; retain_log_prob_drop: number; probe_leak_rate: number; is_safe: boolean; details?: { optimizer_steps?: number; kept_parameter_changes?: number; training_budget_used_seconds?: number; method_preparation_seconds?: number; rolled_back?: boolean; retain_quality_check?: RetainQualityCheck; [key: string]: unknown } };
}
export interface LiveHyperparameters {
  engine_version?: 'v2' | 'v3';
  method?: UnlearningMethod;
  priority?: StrategyPriority;
  training_budget_seconds?: number;
  fact_indices?: number[];
  custom_entity?: CustomEntityInput;
  retain_max_drop?: number;
  retain_quality_max_drop?: number;
  retain_weight?: number;
}
export interface LiveJobStatus {
  job_id: string;
  author_id: string;
  author_name: string;
  mode: ExecutionMode;
  status: 'RUNNING' | 'CANCELLING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  created_at?: string;
  start_time?: number;
  stage_elapsed_seconds?: number;
  stage_durations_seconds?: Record<string, number>;
  settings?: LiveHyperparameters;
  source_kind?: 'catalog' | 'custom';
  estimate?: { remaining_low_seconds: number; remaining_high_seconds: number; over_estimate: boolean; source: string; sample_count: number } | null;
  stage: string;
  progress: number;
  current_step: string;
  logs: string[];
  elapsed_seconds: number;
  error?: string | null;
  persistence_error?: string;
  discovery?: DiscoveryPayload | null;
  result?: {
    scoring_recheck?: { revision: string; scope: string; limitation: string; original_audit: Audit; changes: unknown[]; missing_forward_fact_checks: string[] };
    provenance?: { engine_version?: string; priority?: string; training_budget_seconds?: number | null; selected_fact_indices?: number[]; selected_questions?: string[]; target_checkpoint_hash?: string; source_kind?: string; seed?: number; [key: string]: unknown };
    unlearning_status?: string;
    evaluation_scope?: 'preliminary_screening' | 'full_experiment';
    performance?: { stage_seconds: Record<string, number>; baseline_controls: Record<string, { cache_hit: boolean; key: string | null; measured_at: string }> };
    v3?: { status: string; best_method: string; selection_rationale: string; trials: V3Attempt[] } | null;
    entity: Entity;
    facts: Fact[];
    trace: Round[];
    attacks: PairedAttack[];
    audit: Audit;
    checkpoint_hash: string;
    checkpoint_path: string;
    duration_seconds: number;
  };
}

export interface DiscoveryPayload {
  entity: Entity;
  facts: Fact[];
  checkpoint_hash: string;
  timestamp?: string;
  provenance?: Record<string, unknown>;
}
declare global { interface Window { AURA_REPLAY?: Bundle } }

