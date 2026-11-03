import type { Bundle, Entity, Fact, AttackReport, PairedAttack, Draft, TofuCatalog } from '../types';

export function loadBundle(value = window.AURA_REPLAY): Bundle {
  if (value?.schemaVersion !== 1 || !value.data?.discovery?.facts_evidence?.length || !value.data.trace?.decision_trace?.length) {
    throw new Error('The recorded evidence bundle is missing or unsupported. Rebuild the frontend to restore the packaged artifacts.');
  }
  return value;
}

export function recordedCatalog(bundle: Bundle): Entity[] {
  const grouped = new Map<string, Fact[]>();
  for (const fact of bundle.data.discovery.facts_evidence) grouped.set(fact.entity_name, [...(grouped.get(fact.entity_name) ?? []), fact]);
  return [...grouped].map(([name, facts]) => {
    const control = facts.some(f => f.metadata?.is_control_retain);
    const negative = facts.some(f => f.metadata?.is_synthetic_control);
    const role = control ? 'RETAIN_CONTROL' : negative ? 'NEGATIVE_CONTROL' : 'FORGET_TARGET';
    const id = name.toLowerCase().split(' ')[0];
    return { id, name, role, facts_count: facts.length, badge: control ? 'Retain control' : negative ? 'Unexposed control' : 'Recorded forget target', description: 'Entity present in the saved discovery report.' };
  });
}

export function validateCatalog(value: unknown): TofuCatalog {
  const catalog = value as TofuCatalog;
  if (catalog?.schemaVersion !== 1 || catalog.source?.dataset !== 'locuslab/TOFU' || catalog.source?.split !== 'full' || catalog.source?.rows !== 4000 || !Array.isArray(catalog.authors) || catalog.authors.length !== 200 || !catalog.authors.every(a => typeof a.id === 'string' && typeof a.name === 'string' && ['IN_DATASET', 'NOT_PROVIDED'].includes(a.name_status) && Number.isInteger(a.row_start) && Array.isArray(a.qa) && a.qa.length === 20 && a.qa.every(q => typeof q.question === 'string' && typeof q.answer === 'string')) || new Set(catalog.authors.map(a => a.name)).size !== 200 || new Set(catalog.authors.map(a => a.id)).size !== 200) throw new Error('The full TOFU author catalog is missing or unsupported.');
  return catalog;
}

export function mergeCatalog(bundle: Bundle, catalog: TofuCatalog | null): Entity[] {
  const recorded = recordedCatalog(bundle);
  if (!catalog) return recorded;
  const entities: Entity[] = catalog.authors.map(author => {
    const saved = recorded.find(e => e.name === author.name);
    return saved ? { ...saved, dataset: author } : { id: author.id, name: author.name, role: 'DATASET_AUTHOR', badge: 'Dataset author · untested', facts_count: 0, description: 'Original TOFU questions available. No saved model test for this author.', dataset: author };
  });
  entities.push(...recorded.filter(e => !catalog.authors.some(a => a.name === e.name)));
  return entities.sort((a, b) => a.name.localeCompare(b.name, 'en'));
}

export async function fetchCatalog(bundle: Bundle): Promise<{ entities: Entity[]; connected: boolean; catalog: TofuCatalog | null; catalogError: string | null }> {
  const [apiResult, datasetResult] = await Promise.allSettled([(async () => {
    const response = await fetch('/api/entities', { signal: AbortSignal.timeout(3000) });
    if (!response.ok) throw new Error('Catalog unavailable');
    const data: unknown = await response.json();
    if (!Array.isArray(data) || !data.length || !data.every(e => typeof e.name === 'string' && typeof e.id === 'string' && ['FORGET_TARGET', 'RETAIN_CONTROL', 'NEGATIVE_CONTROL'].includes(e.role))) throw new Error('Unsupported catalog');
    return true;
  })(), (async () => {
    const response = await fetch('./artifacts/tofu_catalog.json', { signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error('TOFU catalog unavailable');
    return validateCatalog(await response.json());
  })()]);
  const catalog = datasetResult.status === 'fulfilled' ? datasetResult.value : null;
  return { entities: mergeCatalog(bundle, catalog), connected: apiResult.status === 'fulfilled', catalog, catalogError: catalog ? null : 'Full TOFU catalog unavailable. Only the four packaged demo entities are shown. Rebuild the frontend to restore the author list.' };
}

export const entityFacts = (bundle: Bundle, entity: Entity) => bundle.data.discovery.facts_evidence.filter(f => f.entity_name === entity.name);
export const selectableFact = (fact: Fact, entity: Entity) => entity.role === 'FORGET_TARGET' && !fact.metadata?.is_control_retain && ['CONFIRMED_LEAK', 'PARTIAL_LEAK'].includes(fact.verdict);

export function attacksFor(bundle: Bundle, entityId: string, selected: Fact[] = []): PairedAttack[] {
  const id = entityId === 'jaime' ? 'retain' : entityId;
  const after = bundle.data[`atu_v2_${id}`] as AttackReport | undefined;
  const before = bundle.data[`target_model_${id}`] as AttackReport | undefined;
  const base = bundle.data[`base_model_${id}`] as AttackReport | undefined;
  const records = (after?.results ?? []).map(attack => {
    const target = before?.results.find(a => a.probe_id === attack.probe_id && a.prompt === attack.prompt);
    const baseAttack = base?.results.find(a => a.probe_id === attack.probe_id && a.prompt === attack.prompt);
    return { after: attack, before: target, base: baseAttack, calibration: bundle.publishedLabels[attack.probe_id] };
  });
  // Focus ordering uses exported target-fact metadata, never response reclassification.
  const focused = (record: PairedAttack) => selected.some(f => record.after.target_facts.includes(f.target_value));
  return records.sort((a, b) => Number(focused(b)) - Number(focused(a)) || Number(Boolean(b.calibration)) - Number(Boolean(a.calibration)));
}

export function validateDraft(draft: Draft): string | null {
  if (!draft.name.trim()) return 'Enter an entity name.';
  if (!draft.facts.length || draft.facts.some(f => !f.key.trim() || !f.value.trim())) return 'Give every candidate fact an attribute and a value.';
  const keys = draft.facts.map(f => f.key.trim().toLowerCase());
  if (new Set(keys).size !== keys.length) return 'Use a different attribute for each candidate fact.';
  return null;
}

export class LiveUnavailableError extends Error {
  constructor() { super('This legacy discovery helper does not launch GPU jobs. Use Start custom experiment in the live workspace. No model inference or unlearning was performed.'); }
}
export async function discoverCustom(draft: Draft): Promise<never> {
  const error = validateDraft(draft);
  if (error) throw new Error(error);
  // Keep legacy replay helpers separate from genuine queued execution.
  throw new LiveUnavailableError();
}

export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const label = (key: string) => ({ father_trade: "Father’s profession", mother_field: "Mother’s profession", birthplace: 'Birthplace', birthdate: 'Date of birth', genre: 'Literary genre', award: 'Award', book1: 'First book', book2: 'Second book', book_1: 'First book', book_2: 'Second book', direct_qa: 'Direct question', direct: 'Direct question', direct_paraphrase: 'Paraphrase', completion_cloze: 'Completion', contextual_prompt: 'Contextual prompt', partial_fact: 'Partial fact', fill_in_blank: 'Fill in the blank', indirect: 'Indirect question', FULL_RECOVERY: 'Full recovery', PARTIAL_RECOVERY: 'Partial recovery', NO_RECOVERY: 'No recovery', VERIFIED_SUPPRESSION: 'Verified suppression', RESIDUAL_LEAKAGE: 'Residual leakage', INCONCLUSIVE: 'Inconclusive' }[key] ?? key.replaceAll('_', ' ').replace(/^./, s => s.toUpperCase()));
