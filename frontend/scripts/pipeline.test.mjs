import assert from 'node:assert/strict';
import { test } from 'node:test';
import { triggerLiveUnlearning, fetchPipelineStatus, PipelineError, validateJob, cancelPipeline, fetchJobHistory } from '../app/src/services/pipeline.ts';
import { parseCollection, optimizerUpdates, previewPair } from '../app/src/services/demos.ts';
import { parseWorkspaceHash, workspaceHash } from '../app/src/services/navigation.ts';
import { comparisonNotes } from '../app/src/services/comparison.ts';
import { discoveryCounts, matchesDiscoveryFilter } from '../app/src/services/discovery.ts';
import { measuredPercent, runOutcome, outcomeDescription, mergeRun, readActiveJob, rememberActiveJob, validSavedRuns } from '../app/src/services/jobs.ts';

const job = { job_id: 'ui-test', author_id: 'author', author_name: 'UI TEST', mode: 'fast', status: 'RUNNING', stage: 'discover', progress: 12, elapsed_seconds: 5, current_step: 'Testing', logs: [] };
const result = { entity: { id: 'author', name: 'UI TEST' }, facts: [], attacks: [], trace: [], audit: {}, checkpoint_hash: 'ui-test', checkpoint_path: 'ui-test', duration_seconds: 5 };

const qualityCheck = { enabled: true, metric: 'mean_rougeL_against_reference', before: .8, after: .792, relative_drop: .01, limit: .02, sample_count: 25, token_cap: 96, passed: true, cohort_sha256: 'fixed-cohort' };

test('retain answer quality loss limit reaches the server separately from likelihood safety', async () => {
  const original = globalThis.fetch; let payload;
  try {
    globalThis.fetch = async (_url, options) => { payload = JSON.parse(options.body); return { ok: true, json: async () => ({ job_id: 'quality-test', author_name: 'UI TEST' }) }; };
    await triggerLiveUnlearning('author', 'full', { retain_max_drop: .03, retain_quality_max_drop: .01 });
    assert.equal(payload.retain_max_drop, .03);
    assert.equal(payload.retain_quality_max_drop, .01);
  } finally { globalThis.fetch = original; }
});

test('optional quality measurements preserve legacy records and reject malformed new scores', () => {
  const complete = { ...job, status: 'COMPLETED', result };
  assert.equal(validateJob(complete).result.audit.retain_quality_check, undefined);
  const measured = { ...complete, result: { ...result, audit: { retain_quality_check: qualityCheck } } };
  assert.deepEqual(validateJob(measured).result.audit.retain_quality_check, qualityCheck);
  assert.throws(() => validateJob({ ...measured, result: { ...measured.result, audit: { retain_quality_check: { ...qualityCheck, relative_drop: Infinity } } } }), /quality measurement/);
  assert.throws(() => validateJob({ ...measured, result: { ...measured.result, audit: { retain_quality_check: { ...qualityCheck, passed: 'yes' } } } }), /quality measurement/);
  assert.throws(() => validateJob({ ...measured, result: { ...measured.result, audit: { retain_quality_check: { ...qualityCheck, before: null } } } }), /quality measurement/);
  assert.throws(() => validateJob({ ...measured, result: { ...measured.result, audit: { retain_quality_check: { ...qualityCheck, relative_drop: .05 } } } }), /quality measurement/);
  const disabled = { ...qualityCheck, enabled: false, before: null, after: null, relative_drop: null, limit: null, passed: null };
  assert.deepEqual(validateJob({ ...measured, result: { ...measured.result, audit: { retain_quality_check: disabled } } }).result.audit.retain_quality_check, disabled);
});

test('failed or missing requested quality measurement cannot produce a green success', () => {
  const success = { ...job, status: 'COMPLETED', settings: { retain_quality_max_drop: .02 }, result: {
    ...result, unlearning_status: 'SUCCESS', audit: { validated_attacks: 6, verified_suppressions: 6, residual_leaks: 0, retain_quality_check: qualityCheck },
  } };
  assert.equal(runOutcome(success).tone, 'green');
  const failed = { ...success, result: { ...success.result, audit: { ...success.result.audit, retain_quality_check: { ...qualityCheck, after: .76, relative_drop: .05, passed: false } } } };
  assert.equal(runOutcome(failed).tone, 'red');
  assert.match(runOutcome(failed).label, /quality check failed/);
  const missing = { ...success, result: { ...success.result, audit: { ...success.result.audit, retain_quality_check: undefined } } };
  assert.equal(runOutcome(missing).tone, 'amber');
  assert.match(runOutcome(missing).label, /quality not verified/);
});

test('launch sends V3 and requested retain settings once', async () => {
  const original = globalThis.fetch;
  const calls = [];
  try {
    globalThis.fetch = async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ job_id: 'ui-test', author_name: 'UI TEST' }) }; };
    assert.equal((await triggerLiveUnlearning('author', 'full', { retain_max_drop: .03, retain_weight: 2 })).jobId, 'ui-test');
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, '/api/run_pipeline');
    assert.deepEqual(JSON.parse(calls[0].options.body), { author_id: 'author', mode: 'full', engine_version: 'v3', retain_max_drop: .03, retain_weight: 2 });
  } finally { globalThis.fetch = original; }
});

test('an existing GPU job can be reconnected after a conflict without relaunching', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () => { calls++; return { ok: false, status: 409, json: async () => ({ error: 'GPU busy', job_id: 'existing-job' }) }; };
    await assert.rejects(triggerLiveUnlearning('author'), error => error instanceof PipelineError && error.jobId === 'existing-job');
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});

test('polling escapes job IDs and supports cancelling an in-flight request', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController();
  let request;
  try {
    globalThis.fetch = async (url, options) => { request = { url, options }; return { ok: true, json: async () => job }; };
    await fetchPipelineStatus('one & two', controller.signal);
    assert.equal(request.url, '/api/pipeline_status?job_id=one%20%26%20two');
    controller.abort(); assert.equal(request.options.signal.aborted, true);
  } finally { globalThis.fetch = original; }
});

test('completed jobs need actual live result arrays; empty arrays stay empty', () => {
  assert.throws(() => validateJob({ ...job, status: 'COMPLETED' }), /missing its results/);
  const completed = validateJob({ ...job, status: 'COMPLETED', result });
  assert.equal(completed.result.facts.length, 0);
  assert.equal(completed.result.attacks.length, 0);
  assert.throws(() => validateJob({ ...job, logs: null }), /unsupported run status/);
});

test('job completion never implies scientific success and absent metrics are not zero', () => {
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result }).label, 'Review required');
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'UNVERIFIED' } }).tone, 'amber');
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'SUCCESS' } }).tone, 'amber');
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'SUCCESS', audit: { validated_attacks: 4, residual_leaks: 0 } } }).tone, 'amber');
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'SUCCESS', audit: { validated_attacks: 4, residual_leaks: 1 } } }).tone, 'red');
  assert.equal(runOutcome({ ...job, status: 'COMPLETED', result: { ...result, evaluation_scope: 'preliminary_screening', unlearning_status: 'SUCCESS', audit: { validated_attacks: 4, residual_leaks: 0 } } }).tone, 'amber');
  assert.equal(measuredPercent(null), 'Not measured');
  assert.equal(measuredPercent(undefined), 'Not measured');
  assert.equal(measuredPercent(NaN), 'Not measured');
  assert.equal(measuredPercent(0), '0.0%');
  assert.equal(measuredPercent(1), '100.0%');
});

test('resumed jobs validate storage and replacing a run does not duplicate history', () => {
  const previous = globalThis.localStorage;
  const storage = new Map();
  globalThis.localStorage = { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
  try {
    rememberActiveJob({ jobId: 'active', authorId: 'author', authorName: 'UI TEST', mode: 'fast', startedAt: 1 });
    assert.equal(readActiveJob().jobId, 'active');
    assert.equal(mergeRun([job], { ...job, status: 'FAILED' }).length, 1);
    rememberActiveJob(null); assert.equal(readActiveJob(), null);
    storage.set('atu-studio-active-job', '{broken'); assert.equal(readActiveJob(), null);
  } finally { globalThis.localStorage = previous; }
});

test('selected facts, custom values, strategy and budget reach the genuine job endpoint', async () => {
  const previous = globalThis.fetch; let payload;
  try {
    globalThis.fetch = async (url, options) => { assert.equal(url, '/api/run_pipeline'); payload = JSON.parse(options.body); return { ok: true, json: async () => ({ job_id: 'custom-job', author_id: 'custom-safe', author_name: 'Custom entity' }) }; };
    const custom = { name: 'Custom entity', facts: [{ attribute: 'birthplace', value: 'Brussels' }] };
    const launched = await triggerLiveUnlearning('', 'fast', { custom_entity: custom, fact_indices: [0], priority: 'preserve_utility', training_budget_seconds: 30 });
    assert.equal(launched.authorId, 'custom-safe'); assert.equal(payload.author_id, undefined);
    assert.deepEqual(payload.custom_entity, custom); assert.deepEqual(payload.fact_indices, [0]);
    assert.equal(payload.priority, 'preserve_utility'); assert.equal(payload.training_budget_seconds, 30);
  } finally { globalThis.fetch = previous; }
});

test('stop requests are explicit and cancelled runs never look scientifically successful', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => { assert.equal(url, '/api/cancel_pipeline'); assert.deepEqual(JSON.parse(options.body), { job_id: 'ui-test' }); return { ok: true, json: async () => ({ ...job, status: 'CANCELLING' }) }; };
    assert.equal((await cancelPipeline('ui-test')).status, 'CANCELLING');
    assert.equal(runOutcome(validateJob({ ...job, status: 'CANCELLED' })).label, 'Stopped by you');
    assert.equal(runOutcome({ ...job, status: 'CANCELLING' }).tone, 'amber');
  } finally { globalThis.fetch = previous; }
});

test('backend history rejects malformed results while retaining cancelled records', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ jobs: [{ ...job, status: 'CANCELLED' }, { invalid: true }, { ...job, status: 'COMPLETED' }] }) });
    const runs = await fetchJobHistory(); assert.equal(runs.length, 1); assert.equal(runs[0].status, 'CANCELLED');
  } finally { globalThis.fetch = previous; }
});

test('comparisons expose mismatched budgets, facts, controls and coverage', () => {
  const base = { ...job, mode: 'full', status: 'COMPLETED', result: { ...result, evaluation_scope: 'full_experiment', provenance: { scoring_revision: 'same-scorer', probe_protocol_revision: 'same-protocol', seed: 42, retain_max_drop: .03, retain_weight: 1, target_checkpoint_hash: 'original', training_budget_seconds: 600, selected_questions: ['Q'] }, audit: { retain_utility_examples: 3, retain_generation_token_cap: 48 } } };
  assert.equal(comparisonNotes(base, { ...base, job_id: 'other' }).length, 0);
  const changed = { ...base, author_id: 'other', result: { ...base.result, provenance: { ...base.result.provenance, training_budget_seconds: 30, selected_questions: ['Different'] }, audit: { retain_utility_examples: 25, retain_generation_token_cap: 96 } } };
  const notes = comparisonNotes(base, changed).join(' ');
  assert.match(notes, /Different entities/); assert.match(notes, /Different selected facts/); assert.match(notes, /Different training budgets/); assert.match(notes, /Retain-answer coverage/);
});

test('privacy discovery counts measured verdicts and keeps uncertain findings separate', () => {
  const facts = ['CONFIRMED_LEAK', 'PARTIAL_LEAK', 'NOT_EXPOSED', 'UNCERTAIN'].map(verdict => ({ verdict }));
  assert.deepEqual(discoveryCounts(facts), { tested: 4, exposed: 1, partial: 1, notExposed: 1, uncertain: 1 });
  assert.equal(facts.filter(fact => matchesDiscoveryFilter(fact, 'Exposed')).length, 2);
  assert.deepEqual(facts.filter(fact => matchesDiscoveryFilter(fact, 'Uncertain')), [facts[3]]);
  assert.deepEqual(facts.filter(fact => matchesDiscoveryFilter(fact, 'Not exposed')), [facts[2]]);
  assert.equal(discoveryCounts([]).tested, 0);
});

test('matching recovery questions do not hide different safety limits, seeds or protocols', () => {
  const base = { ...job, mode: 'full', status: 'COMPLETED', settings: { retain_max_drop: .03, retain_weight: 1 }, result: {
    ...result, evaluation_scope: 'full_experiment', provenance: {
      scoring_revision: 'same-scorer', probe_protocol_revision: 'protocol-1', seed: 42,
      target_checkpoint_hash: 'original', training_budget_seconds: 600, selected_questions: ['Q'],
    }, audit: { retain_utility_examples: 25, retain_generation_token_cap: 96 },
  } };
  assert.equal(comparisonNotes(base, { ...base, job_id: 'second' }).length, 0);
  const differentSafety = { ...base, settings: { ...base.settings, retain_max_drop: .3 } };
  assert.match(comparisonNotes(base, differentSafety).join(' '), /Retain safety settings differ/);
  const differentProtocol = { ...base, result: { ...base.result, provenance: { ...base.result.provenance, probe_protocol_revision: 'protocol-2', seed: 7 } } };
  const notes = comparisonNotes(base, differentProtocol).join(' ');
  assert.match(notes, /Recovery protocol versions differ/);
  assert.match(notes, /Random seeds differ/);
  const missing = { ...base, settings: undefined, result: { ...base.result, provenance: { ...base.result.provenance, seed: undefined } } };
  assert.match(comparisonNotes(base, missing).join(' '), /not fully reported/);
});

test('quality comparisons expose different tolerances and retain cohorts', () => {
  const base = { ...job, mode: 'full', status: 'COMPLETED', settings: { retain_max_drop: .03, retain_weight: 1, retain_quality_max_drop: .02 }, result: {
    ...result, evaluation_scope: 'full_experiment', provenance: { scoring_revision: 'same', probe_protocol_revision: 'same', seed: 42, target_checkpoint_hash: 'original', training_budget_seconds: 600, selected_questions: ['Q'] },
    audit: { retain_utility_examples: 25, retain_generation_token_cap: 96, retain_quality_check: qualityCheck },
  } };
  assert.equal(comparisonNotes(base, { ...base, job_id: 'matching' }).length, 0);
  const differentLimit = { ...base, settings: { ...base.settings, retain_quality_max_drop: .05 } };
  assert.match(comparisonNotes(base, differentLimit).join(' '), /quality limits differ/);
  const differentCohort = { ...base, result: { ...base.result, audit: { ...base.result.audit, retain_quality_check: { ...qualityCheck, cohort_sha256: 'different-cohort' } } } };
  assert.match(comparisonNotes(base, differentCohort).join(' '), /quality samples or generation settings differ/);
  const legacy = { ...base, settings: { ...base.settings, retain_quality_max_drop: undefined }, result: { ...base.result, audit: { ...base.result.audit, retain_quality_check: undefined } } };
  assert.match(comparisonNotes(base, legacy).join(' '), /not recorded in both runs/);
});


test('manual method reaches the server and is never replaced in the request', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => { const payload = JSON.parse(options.body); assert.equal(payload.method, 'rmu'); assert.equal(payload.priority, 'fast'); assert.equal(payload.training_budget_seconds, 30); return { ok: true, json: async () => ({ job_id: 'rmu-job', author_name: 'Entity' }) }; };
    assert.equal((await triggerLiveUnlearning('author', 'fast', { method: 'rmu', priority: 'fast', training_budget_seconds: 30 })).jobId, 'rmu-job');
  } finally { globalThis.fetch = previous; }
});

test('zero training and partial suppression have different explanations', () => {
  const complete = { ...job, status: 'COMPLETED', result: { ...result, audit: { validated_attacks: 5, verified_suppressions: 4, residual_leaks: 1, inconclusive_attacks: 1 }, v3: { trials: [{ metrics: { details: { optimizer_steps: 16 } } }] } } };
  assert.equal(runOutcome(complete).label, 'Partial suppression · 4/5 checks');
  assert.match(outcomeDescription(complete), /4 of 5/);
  const zero = { ...complete, result: { ...complete.result, v3: { trials: [{ metrics: { details: { optimizer_steps: 0 } } }] } } };
  assert.equal(runOutcome(zero).label, 'No training updates completed');
  assert.match(outcomeDescription(zero), /before any optimizer update/);
  const rechecked = { ...complete, result: { ...complete.result, audit: { validated_attacks: 4, verified_suppressions: 4, residual_leaks: 0 }, scoring_recheck: { revision: 'new' } } };
  assert.equal(runOutcome(rechecked).tone, 'amber');
  assert.match(runOutcome(rechecked).label, /audit incomplete/);
});

test('incomplete fact coverage cannot turn a successful engine result green', () => {
  const partial = { ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'SUCCESS', audit: {
    validated_attacks: 1, verified_suppressions: 1, residual_leaks: 0,
    facts_requested: 2, facts_with_validated_checks: 1,
  } } };
  assert.equal(runOutcome(partial).tone, 'amber');
  assert.match(runOutcome(partial).label, /1\/2 facts checked/);
  assert.match(outcomeDescription(partial), /1\/2 selected facts/);
  assert.equal(runOutcome({ ...partial, result: { ...partial.result, audit: { ...partial.result.audit, facts_with_validated_checks: 2 } } }).tone, 'green');
  assert.match(runOutcome({ ...partial, result: { ...partial.result, audit: { ...partial.result.audit, residual_leaks: 1 } } }).label, /Partial suppression/);
});

test('unknown training updates stay unknown and recorded zero stays zero', () => {
  const withSteps = values => ({ ...job, result: { ...result, v3: { trials: values.map(optimizer_steps => ({ metrics: { details: { optimizer_steps } } })) } } });
  assert.equal(optimizerUpdates({ ...job, result }), null);
  assert.equal(optimizerUpdates(withSteps([4, undefined])), null);
  assert.equal(optimizerUpdates(withSteps([0])), 0);
  assert.equal(optimizerUpdates(withSteps([3, 4])), 7);
  assert.equal(optimizerUpdates(withSteps([-1])), null);
});

test('demo previews use the identical question and surface residual leakage first', () => {
  const pair = (id, beforePrompt, calibration) => ({ before: { prompt: beforePrompt }, after: { prompt: 'Same question', probe_id: id }, calibration });
  const candidate = { ...job, result: { ...result, attacks: [pair('mismatch', 'Another question', 'RESIDUAL_LEAKAGE'), pair('suppressed', 'Same question', 'VERIFIED_SUPPRESSION'), pair('leak', 'Same question', 'RESIDUAL_LEAKAGE')] } };
  assert.equal(previewPair(candidate).after.probe_id, 'leak');
  assert.equal(previewPair({ ...candidate, result: { ...result, attacks: [candidate.result.attacks[0]] } }), undefined);
});

test('demo collections reject broken descriptions, duplicate IDs and mismatched snapshots', () => {
  const entry = id => ({ id, title: 'Measured case', purpose: 'Inspect evidence', status: 'PENDING', job_id: null, job: null });
  const collection = { schemaVersion: 1, collection_id: 'test', title: 'Test collection', description: 'Test', cases: [entry('a'), entry('b'), entry('c')] };
  assert.equal(parseCollection(collection), collection);
  assert.throws(() => parseCollection({ ...collection, cases: [null, entry('b'), entry('c')] }), /description/);
  assert.throws(() => parseCollection({ ...collection, cases: [entry('a'), entry('a'), entry('c')] }), /description/);
  assert.throws(() => parseCollection({ ...collection, cases: [{ ...entry('a'), status: 'COMPLETED' }, entry('b'), entry('c')] }), /missing its evidence/);
  assert.throws(() => parseCollection({ ...collection, cases: [{ ...entry('a'), status: 'RUNNING', job_id: job.job_id, job }, entry('b'), entry('c')] }), /Full experiment/);
});

test('invalid or unfinished browser-cache records do not enter saved evidence', () => {
  const completed = { ...job, status: 'COMPLETED', result };
  assert.deepEqual(validSavedRuns([null, {}, job, completed, { ...completed, result: { ...result, attacks: [null] } }]), [completed]);
  assert.deepEqual(validSavedRuns({}), []);
});

test('browser navigation keeps routes and saved-run identities across reload and Back', () => {
  for (const route of ['launch', 'lab', 'demo', 'history', 'compare', 'showcase']) {
    assert.deepEqual(parseWorkspaceHash(workspaceHash(route)), { route });
  }
  const id = 'job with / spaces';
  assert.deepEqual(parseWorkspaceHash(workspaceHash('result', id)), { route: 'result', detail: id });
  assert.deepEqual(parseWorkspaceHash(workspaceHash('lab', 'tofu-author')), { route: 'lab', detail: 'tofu-author' });
  assert.deepEqual(parseWorkspaceHash('#run'), { route: 'history' });
  assert.deepEqual(parseWorkspaceHash('#run/%broken'), { route: 'launch' });
});

test('a success flag cannot fill missing or contradictory recovery counts', () => {
  const complete = audit => ({ ...job, status: 'COMPLETED', result: { ...result, unlearning_status: 'SUCCESS', audit } });
  assert.equal(runOutcome(complete({ validated_attacks: 2, residual_leaks: 0 })).tone, 'amber');
  assert.equal(runOutcome(complete({ validated_attacks: 2, residual_leaks: 0, verified_suppressions: 1 })).tone, 'amber');
  assert.equal(runOutcome(complete({ validated_attacks: 2, residual_leaks: 0, verified_suppressions: 2 })).tone, 'green');
});
