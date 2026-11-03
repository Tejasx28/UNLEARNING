import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';
import { initialWorkflow, workflowReducer } from '../app/src/workflow.ts';
import { attacksFor, recordedCatalog, selectableFact, entityFacts, validateDraft, discoverCustom, fetchCatalog, loadBundle, validateCatalog, mergeCatalog } from '../app/src/services/research.ts';
const sandbox = { window: {} };
runInNewContext(await readFile(new URL('../replay_data.js', import.meta.url), 'utf8'), sandbox);
const bundle = sandbox.window.AURA_REPLAY;
const entities = recordedCatalog(bundle);
const catalog = validateCatalog(JSON.parse(await readFile(new URL('../artifacts/tofu_catalog.json', import.meta.url), 'utf8')));
test('workflow locks future stages and invalidates downstream replay when selection changes', () => {
  let state = initialWorkflow();
  assert.equal(workflowReducer(state, { type: 'NAVIGATE', stage: 'verify' }), state);
  assert.equal(workflowReducer(state, { type: 'ADVANCE', stage: 'unlearn' }), state);
  state = workflowReducer(state, { type: 'ADVANCE', stage: 'select' });
  assert.equal(workflowReducer(state, { type: 'ADVANCE', stage: 'unlearn' }), state);
  state = workflowReducer(state, { type: 'SELECT', id: 'real-fact-id' });
  for (const stage of ['unlearn', 'attack', 'verify']) state = workflowReducer(state, { type: 'ADVANCE', stage });
  state = workflowReducer(state, { type: 'SELECT', id: 'real-fact-id' });
  assert.equal(state.reached, 1); assert.equal(state.roundIndex, -1); assert.equal(state.attackCount, 0);
  assert.equal(workflowReducer(state, { type: 'ENTITY', id: 'nikolai' }).selected.length, 0);
});
test('all genuine entities have evidence; controls and unexposed facts are protected', () => {
  assert.equal(entities.length, 4);
  for (const entity of entities) {
    const facts = entityFacts(bundle, entity); assert.ok(facts.length);
    for (const fact of facts) if (entity.role !== 'FORGET_TARGET' || !['CONFIRMED_LEAK', 'PARTIAL_LEAK'].includes(fact.verdict)) assert.equal(selectableFact(fact, entity), false);
  }
  assert.equal(attacksFor(bundle, 'amina').length, 0);
});
test('paired responses preserve identical prompts and explicitly published labels', () => {
  for (const entity of entities) for (const pair of attacksFor(bundle, entity.id)) {
    assert.equal(pair.before.prompt, pair.after.prompt); assert.equal(pair.base.prompt, pair.after.prompt);
    assert.equal(pair.calibration, bundle.publishedLabels[pair.after.probe_id]);
  }
  const father = entityFacts(bundle, entities.find(e => e.id === 'basil')).find(f => f.attribute_key === 'father_trade');
  assert.equal(attacksFor(bundle, 'basil', [father])[0].after.probe_id, 'RT-BASIL-005');
  assert.equal(bundle.publishedLabels['RT-BASIL-005'], 'VERIFIED_SUPPRESSION');
  assert.equal(bundle.publishedLabels['RT-NIKOLAI-005'], 'RESIDUAL_LEAKAGE');
  assert.equal(bundle.publishedLabels['RT-BASIL-001'], undefined);
});
test('custom drafts accept arbitrary names, validate facts, and never simulate inference', async () => {
  const draft = { name: 'Evelyn Desmet', facts: [{ id: 1, key: 'Birthplace', value: 'Brussels' }] };
  assert.equal(validateDraft(draft), null);
  assert.match(validateDraft({ ...draft, name: '' }), /entity name/);
  assert.match(validateDraft({ ...draft, facts: [...draft.facts, { id: 2, key: 'birthplace', value: 'Other' }] }), /different attribute/);
  assert.match(validateDraft({ ...draft, facts: [] }), /attribute and a value/);
  let requests = 0; const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { requests++; throw new Error('No endpoint'); };
  try {
    await assert.rejects(discoverCustom(draft), /No model inference or unlearning was performed/); assert.equal(requests, 0);
    const fallback = await fetchCatalog(bundle); assert.equal(fallback.connected, false); assert.equal(fallback.entities.length, 4);
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ bad: 'schema' }) });
    assert.equal((await fetchCatalog(bundle)).connected, false);
  } finally { globalThis.fetch = originalFetch; }
});
test('missing evidence fails explicitly; saved record scope stays intact', () => {
  assert.throws(() => loadBundle({ schemaVersion: 0 }), /missing or unsupported/);
  assert.equal(bundle.data.trace.decision_trace.length, 6);
  assert.equal(bundle.data.pipeline.unlearning_summary.status, 'SKIPPED_ACTIVE_TRAINING');
  assert.ok(bundle.data.trace.decision_trace.at(-1).stop_reason.startsWith('RETAIN_UTILITY_RISK'));
  assert.equal(bundle.data.evaluation.checkpoint_hash, bundle.publishedAudit.checkpoint);
});
test('full TOFU catalog includes every original QA once, without inventing the unnamed author', async () => {
  const bytes = await readFile(new URL('../artifacts/tofu_full.json', import.meta.url), 'utf8');
  const original = bytes.trim().startsWith('[') ? JSON.parse(bytes) : bytes.trim().split(/\r?\n/).map(line => JSON.parse(line));
  assert.deepEqual([...catalog.authors].sort((a, b) => a.row_start - b.row_start).flatMap(a => a.qa), original);
  assert.equal(catalog.authors.filter(a => a.name_status === 'IN_DATASET').length, 199);
  assert.equal(catalog.authors.find(a => a.name_status === 'NOT_PROVIDED').name, 'Unnamed author (Karachi)');
  assert.throws(() => validateCatalog({ ...catalog, authors: catalog.authors.slice(0, 199) }), /missing or unsupported/);
  assert.throws(() => validateCatalog({ ...catalog, authors: [catalog.authors[0], ...catalog.authors.slice(0, 199)] }), /missing or unsupported/);
});
test('dataset authors remain untested, while original demo identities and protection survive the merge', () => {
  const full = mergeCatalog(bundle, catalog);
  assert.equal(full.length, 201); assert.equal(full.filter(e => e.dataset).length, 200);
  assert.equal(full.filter(e => e.role === 'DATASET_AUTHOR').length, 197);
  for (const saved of entities) assert.equal(full.find(e => e.name === saved.name).id, saved.id);
  const evelyn = full.find(e => e.name === 'Evelyn Desmet');
  assert.equal(evelyn.dataset.qa.length, 20); assert.equal(entityFacts(bundle, evelyn).length, 0);
  assert.equal(attacksFor(bundle, evelyn.id).length, 0);
  assert.equal(selectableFact(entityFacts(bundle, entities[0])[0], evelyn), false);
  assert.equal(full.find(e => e.id === 'amina').dataset, undefined);
  assert.equal(workflowReducer(initialWorkflow(), { type: 'ENTITY', id: evelyn.id }).selected.length, 0);
});
test('the full local catalog survives a four-entity server and an offline preview', async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async url => ({ ok: true, json: async () => url === '/api/entities' ? entities : catalog });
    const live = await fetchCatalog(bundle);
    assert.equal(live.connected, true); assert.equal(live.entities.length, 201); assert.equal(live.catalogError, null);
    globalThis.fetch = async url => { if (url === '/api/entities') throw new Error('Offline'); return { ok: true, json: async () => catalog }; };
    const offline = await fetchCatalog(bundle);
    assert.equal(offline.connected, false); assert.equal(offline.entities.length, 201);
    globalThis.fetch = async url => ({ ok: true, json: async () => url === '/api/entities' ? entities : {} });
    const missing = await fetchCatalog(bundle);
    assert.equal(missing.entities.length, 4); assert.match(missing.catalogError, /catalog unavailable/);
  } finally { globalThis.fetch = originalFetch; }
});
