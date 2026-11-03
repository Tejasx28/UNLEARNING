import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Search, ChevronDown, Check, Plus, Trash2, ArrowRight, Download, ShieldCheck, UserRound, AlertCircle, ChevronRight, Play, Cpu } from 'lucide-react';
import type { Draft, Entity, TofuCatalog, LiveHyperparameters } from '../types';
import { ExperimentControls, defaultConfig, launchOptions } from './ExperimentControls';
import type { ExperimentConfig } from './ExperimentControls';
import { downloadJson, validateDraft } from '../services/research';

export function EntitySelector({ entities, entity, onChange, loading = false }: { entities: Entity[]; entity: Entity; onChange: (entity: Entity) => void; loading?: boolean }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [scope, setScope] = useState<'all' | 'saved' | 'controls'>('all');
  const [placement, setPlacement] = useState({ above: false, height: 460 });
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const options = useRef<HTMLDivElement>(null);
  const normalized = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const authors = entities.filter(e => e.role !== 'NEGATIVE_CONTROL');
  const saved = entities.filter(e => e.role !== 'DATASET_AUTHOR');
  const controls = entities.filter(e => e.role === 'RETAIN_CONTROL' || e.role === 'NEGATIVE_CONTROL');
  const filtered = (scope === 'all' ? authors : scope === 'saved' ? saved : controls).filter(e => normalized(e.name).includes(normalized(query.trim())));
  useLayoutEffect(() => {
    if (!open) return;
    const position = () => {
      const rect = root.current?.getBoundingClientRect();
      if (!rect) return;
      const below = window.innerHeight - rect.bottom;
      const above = below < 340 && rect.top > below;
      setPlacement({ above, height: Math.min(460, Math.max(150, (above ? rect.top : below) - 20)) });
    };
    position();
    window.addEventListener('resize', position);
    window.addEventListener('scroll', position, true);
    return () => { window.removeEventListener('resize', position); window.removeEventListener('scroll', position, true); };
  }, [open]);
  useEffect(() => {
    const list = options.current;
    const option = list?.children[active] as HTMLElement | undefined;
    if (!list || !option) return;
    const bounds = list.getBoundingClientRect();
    const item = option.getBoundingClientRect();
    if (item.top < bounds.top) list.scrollTop -= bounds.top - item.top;
    else if (item.bottom > bounds.bottom) list.scrollTop += item.bottom - bounds.bottom;
  }, [active, query, scope, open]);
  useEffect(() => {
    if (open) search.current?.focus();
    const close = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, [open]);
  const choose = (value: Entity) => { onChange(value); setOpen(false); setQuery(''); setActive(0); root.current?.querySelector('button')?.focus(); };
  return <div className="entity-select" ref={root}>
    <button className={`entity-trigger ${open ? 'open' : ''}`} aria-label="Choose dataset entity" aria-haspopup="listbox" aria-expanded={open} onClick={() => { if (!open) { setQuery(''); setActive(0); setScope(entity.role === 'NEGATIVE_CONTROL' ? 'controls' : 'all'); } setOpen(!open); }}>
      <span className="avatar">{entity.name.slice(0, 1)}</span><span><strong>{entity.name}</strong><small>{entity.role === 'FORGET_TARGET' ? 'TOFU · saved forget target' : entity.role === 'RETAIN_CONTROL' ? 'TOFU · retain control' : entity.role === 'DATASET_AUTHOR' ? 'TOFU · model testing pending' : 'Synthetic · negative control'}</small></span><ChevronDown size={18} />
    </button>
    <div className="catalog-summary">{loading ? 'Loading author list…' : `Browse or search ${authors.length} TOFU authors`}</div>
    {open && <div className={`entity-menu ${placement.above ? 'above' : ''}`} style={{ maxHeight: placement.height }}>
      <div className="search-field"><Search size={17} /><input ref={search} value={query} placeholder="Search by name or surname…" aria-label="Search dataset entities" role="combobox" aria-autocomplete="list" aria-expanded="true" aria-controls="entity-options" aria-activedescendant={filtered[active] ? `entity-${filtered[active].id}` : undefined} onChange={e => { setQuery(e.target.value); setActive(0); }} onKeyDown={e => {
        if (e.key === 'Escape') { setOpen(false); root.current?.querySelector('button')?.focus(); }
        if (e.key === 'ArrowDown') { e.preventDefault(); setActive(i => Math.max(0, Math.min(i + 1, filtered.length - 1))); }
        if (e.key === 'ArrowUp') { e.preventDefault(); setActive(i => Math.max(i - 1, 0)); }
        if (e.key === 'Enter' && filtered[active]) { e.preventDefault(); choose(filtered[active]); }
      }} /></div>
      <div className="catalog-filters" aria-label="Author list filters">{([['all', 'All authors', authors.length], ['saved', 'Saved demos', saved.length], ['controls', 'Controls', controls.length]] as const).map(([key, title, count]) => <button key={key} aria-pressed={scope === key} className={scope === key ? 'active' : ''} onClick={() => { setScope(key); setActive(0); search.current?.focus(); }}>{title}<span>{count}</span></button>)}</div>
      <div ref={options} className="entity-options" role="listbox" aria-label="Dataset entities" id="entity-options">
        {filtered.map((e, index) => <button id={`entity-${e.id}`} key={e.id} role="option" tabIndex={-1} aria-selected={e.id === entity.id} className={`entity-option ${active === index ? 'active' : ''}`} onClick={() => choose(e)}>
          {e.role === 'RETAIN_CONTROL' ? <ShieldCheck size={18} /> : <UserRound size={18} />}<span><strong>{e.name}</strong><small>{e.role === 'DATASET_AUTHOR' ? '20 dataset questions · no saved model test' : e.role === 'FORGET_TARGET' ? `${e.facts_count} tested facts · saved forget demo` : e.role === 'RETAIN_CONTROL' ? `${e.facts_count} tested facts · protected retain control` : `${e.facts_count} tested facts · synthetic control`}</small></span>{e.id === entity.id && <Check size={16} />}
        </button>)}
        {!filtered.length && <div className="empty-mini">No matching author in this filter. Try another name or switch to All authors.</div>}
      </div>
      <div className="menu-foot" aria-live="polite">{loading ? 'Loading the full TOFU catalog…' : `${filtered.length} shown · ${authors.length} TOFU authors · 1 synthetic control`}</div>
    </div>}
  </div>;
}

export function DatasetAuthorPanel({ entity, catalog, onReplay, onLaunchLive, launching = false, connected = false, experimentConfig, onConfigChange }: {
  entity: Entity; catalog: TofuCatalog; onReplay: () => void;
  onLaunchLive?: (authorId: string, mode: 'fast' | 'full', hyperparameters?: LiveHyperparameters) => void;
  launching?: boolean; connected?: boolean;
  experimentConfig?: ExperimentConfig; onConfigChange?: (config: ExperimentConfig) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [localConfig, setLocalConfig] = useState<ExperimentConfig>({ ...defaultConfig });
  const config = experimentConfig ?? localConfig;
  const setConfig = onConfigChange ?? setLocalConfig;
  const [selected, setSelected] = useState<number[]>([0, 1, 2, 3, 4].filter(index => index < entity.dataset!.qa.length));
  const [query, setQuery] = useState('');
  const author = entity.dataset!;
  const selectionLimit = config.mode === 'fast' ? 5 : 20;
  const selectionHelpId = 'fact-selection-help-' + author.id;
  const questions = author.qa.map((qa, index) => ({ ...qa, index })).filter(qa => (qa.question + ' ' + qa.answer).toLowerCase().includes(query.trim().toLowerCase()));
  return <section className="run-setup">
    <div className="studio-card author-profile"><span className="studio-eyebrow">SELECTED AUTHOR</span><div className="author-profile-heading"><span className="studio-avatar large">{author.name[0]}</span><div><h2>{author.name}</h2><p>{author.qa.length} original TOFU questions · {author.name_status === 'NOT_PROVIDED' ? 'Dataset name unavailable' : 'Fictional author profile'}</p></div><span className="studio-badge">Reference data</span></div></div>
    <div className="studio-card run-configuration"><div className="studio-section-heading"><div><h2>Configure your experiment</h2><p>Discovery, adaptive unlearning, and a separate recovery audit.</p></div><span className="studio-badge green">ATU v3</span></div>
      <ExperimentControls value={config} onChange={next => { setConfig(next); if (next.mode === 'fast') setSelected(current => current.slice(0, 5)); }} />
      <div className="fact-selection-toolbar"><strong aria-live="polite">{selected.length} / {Math.min(selectionLimit, author.qa.length)} {config.mode === 'fast' ? 'Quick' : 'Full'} facts selected</strong><button type="button" className="text-button" onClick={() => { setExpanded(true); setSelected(author.qa.slice(0, selectionLimit).map((_, index) => index)); }}>Select {config.mode === 'fast' ? 'first 5' : 'all'}</button><button type="button" className="text-button" onClick={() => setSelected([])}>Clear selection</button></div><p className="studio-caption" id={selectionHelpId} role="status">{!selected.length ? 'Select at least one fact below to enable Start experiment.' : config.mode === 'fast' && selected.length >= selectionLimit ? 'Quick allows 5 facts. Uncheck one to choose another, or select Full experiment.' : 'Only checked facts enter this run’s training and recovery tests.'}</p>
      <div className="run-launch-row"><button className="button primary" aria-describedby={selectionHelpId} disabled={launching || !connected || !onLaunchLive || !selected.length} onClick={() => onLaunchLive?.(author.id, config.mode, { ...launchOptions(config), fact_indices: selected })}><Play size={16} />{launching ? 'Run in progress' : 'Start experiment'}<ArrowRight size={16} /></button><span><Cpu size={15} />{connected ? 'Runs locally on your GPU' : 'Connect the local backend to run'}</span></div><p className="studio-caption">Exact original control checks are reused when available. Review the selected facts before starting.</p>
    </div>
    <div className="studio-card reference-card"><div className="studio-section-heading"><div><h2>Reference questions</h2><p>These {author.qa.length} questions and answers are provided by TOFU. The live run checks what your model actually remembers.</p></div><button className="icon-button" aria-label="Export reference questions" title="Export reference questions" onClick={() => downloadJson({ entity: author.name, status: 'UNTESTED_DATASET_INPUT', source: catalog.source, row_start: author.row_start, candidate_qa: author.qa }, author.id + '-questions.json')}><Download size={17} /></button></div>
      {author.name_status === 'NOT_PROVIDED' && <div className="studio-note"><AlertCircle size={17} /><p>This profile has no personal name in the dataset. Karachi is its birthplace.</p></div>}
      <div className="studio-search"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search questions or reference answers…" aria-label="Search reference questions" /></div>
      <div className="reference-questions">{questions.slice(0, expanded || query ? questions.length : 5).map(qa => <div className="selectable-reference" key={qa.index}><label className="fact-select"><input type="checkbox" aria-label={'Include fact ' + (qa.index + 1)} aria-describedby={selectionHelpId} checked={selected.includes(qa.index)} disabled={!selected.includes(qa.index) && selected.length >= selectionLimit} onChange={event => setSelected(current => event.target.checked ? [...current, qa.index].sort((a, b) => a-b) : current.filter(index => index !== qa.index))} /><span>Include</span></label><details><summary><span>{String(qa.index + 1).padStart(2, '0')}</span><strong>{qa.question}</strong><ChevronRight size={16} /></summary><div><span className="studio-eyebrow">DATASET ANSWER</span><p>{qa.answer}</p></div></details></div>)}{!questions.length && <div className="studio-empty small"><Search size={22} /><h3>No matching questions.</h3><button className="text-button" onClick={() => setQuery('')}>Clear search</button></div>}</div>
      {!query && <button className="text-button reference-more" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer questions' : 'Show all ' + author.qa.length + ' questions'}<ChevronDown size={15} /></button>}
      <div className="reference-source"><a href={catalog.source.url} target="_blank" rel="noreferrer">Original TOFU dataset</a><span>Revision {catalog.source.revision.slice(0, 8)} · original text preserved</span><button className="text-button" onClick={onReplay}>View a recorded example<ArrowRight size={13} /></button></div>
    </div>
  </section>;
}

export function CustomEntityBuilder({ onReplay, onLaunchLive, launching = false, connected = false, experimentConfig, onConfigChange }: { onReplay: () => void; onLaunchLive?: (id: string, mode: 'fast' | 'full', options?: LiveHyperparameters) => void; launching?: boolean; connected?: boolean; experimentConfig?: ExperimentConfig; onConfigChange?: (config: ExperimentConfig) => void }) {
  const [draft, setDraft] = useState<Draft>({ name: '', facts: [{ id: 1, key: '', value: '', question: '' }] });
  const [localConfig, setLocalConfig] = useState<ExperimentConfig>({ ...defaultConfig });
  const config = experimentConfig ?? localConfig;
  const setConfig = onConfigChange ?? setLocalConfig;
  const [selected, setSelected] = useState<number[]>([1]);
  const nextId = useRef(2);
  const [error, setError] = useState('');
  const limit = config.mode === 'fast' ? 5 : 20;
  const change = (id: number, field: 'key' | 'value' | 'question', value: string) => { setDraft(current => ({ ...current, facts: current.facts.map(fact => fact.id === id ? { ...fact, [field]: value } : fact) })); setError(''); };
  const input = () => ({ name: draft.name.trim(), facts: draft.facts.map(fact => ({ attribute: fact.key.trim(), value: fact.value.trim(), ...(fact.question?.trim() ? { question: fact.question.trim() } : {}) })) });
  return <form className="custom-builder studio-card" onSubmit={event => { event.preventDefault(); const invalid = validateDraft(draft); if (invalid || !selected.length) { setError(invalid || 'Select at least one candidate fact.'); return; } setError(''); onLaunchLive?.('', config.mode, { ...launchOptions(config), custom_entity: input(), fact_indices: draft.facts.flatMap((fact, index) => selected.includes(fact.id) ? [index] : []) }); }}>
    <div className="studio-section-heading"><div><h2>Custom entity</h2><p>Submit candidate facts for genuine discovery and unlearning on your local model.</p></div><span className="studio-badge">Live · V3</span></div>
    <label className="input-label" htmlFor="custom-name">Entity name</label><input className="studio-input" id="custom-name" maxLength={160} required value={draft.name} onChange={event => setDraft(current => ({ ...current, name: event.target.value }))} placeholder="Entity or author name" autoComplete="off" />
    <div className="form-section-title"><span>Candidate facts · {selected.length} / {limit} selected</span><span>Inputs are not evidence of model memory</span></div>
    <div className="custom-facts">{draft.facts.map((fact, index) => <div className="custom-fact" key={fact.id}><div><label className="fact-select"><input type="checkbox" aria-label={'Include custom fact ' + (index + 1)} checked={selected.includes(fact.id)} disabled={!selected.includes(fact.id) && selected.length >= limit} onChange={event => setSelected(current => event.target.checked ? [...current, fact.id] : current.filter(id => id !== fact.id))} />Fact {index + 1}</label><button type="button" className="icon-button" aria-label={'Remove fact ' + (index + 1)} disabled={draft.facts.length === 1} onClick={() => { setDraft(current => ({ ...current, facts: current.facts.filter(row => row.id !== fact.id) })); setSelected(current => current.filter(id => id !== fact.id)); }}><Trash2 size={16} /></button></div><div className="experiment-options"><label>Attribute<input className="studio-input" aria-label={'Fact ' + (index + 1) + ' attribute'} maxLength={100} required value={fact.key} onChange={event => change(fact.id, 'key', event.target.value)} placeholder="Birthplace" /></label><label>Value<input className="studio-input" aria-label={'Fact ' + (index + 1) + ' value'} maxLength={2000} required value={fact.value} onChange={event => change(fact.id, 'value', event.target.value)} placeholder="Brussels" /></label></div><label>Question · optional<input className="studio-input" aria-label={'Fact ' + (index + 1) + ' question'} maxLength={1000} value={fact.question || ''} onChange={event => change(fact.id, 'question', event.target.value)} placeholder={draft.name && fact.key ? 'What is the ' + fact.key + ' of ' + draft.name + '?' : 'Automatically generated from the attribute and entity name'} /></label></div>)}</div>
    <button type="button" className="button secondary small" disabled={draft.facts.length >= 20} onClick={() => { const id = nextId.current++; setDraft(current => ({ ...current, facts: [...current.facts, { id, key: '', value: '', question: '' }] })); if (selected.length < limit) setSelected(current => [...current, id]); }}><Plus size={15} />Add fact</button>
    <ExperimentControls value={config} onChange={next => { setConfig(next); if (next.mode === 'fast') setSelected(current => current.slice(0, 5)); }} />
    <div className="studio-note"><AlertCircle size={17} /><p>Discovery tests whether the model knows these values. Missing exposure or failed controls produce an inconclusive result. This does not teach the model your candidate facts.</p></div>
    {error && <div className="studio-note red" role="alert">{error}</div>}
    {(!selected.length || selected.length >= limit) && <p className="studio-caption" role="status">{!selected.length ? 'Select at least one candidate fact to enable Start custom experiment.' : `This profile allows ${limit} selected facts. Uncheck one before choosing another.`}</p>}
    <div className="inline-actions"><button type="submit" className="button primary" disabled={launching || !connected || !onLaunchLive || !selected.length}><Play size={16} />{launching ? 'Run in progress' : 'Start custom experiment'}<ArrowRight size={16} /></button><button type="button" className="button secondary" onClick={() => { const invalid = validateDraft(draft); if (invalid) { setError(invalid); return; } downloadJson({ ...input(), status: 'UNTESTED_DRAFT' }, 'custom-candidate-facts.json'); }}><Download size={15} />Export inputs</button><button type="button" className="text-button" onClick={onReplay}>Recorded example</button></div>
    {!connected && <p className="studio-caption">Connect the local backend to run a custom experiment.</p>}
  </form>;
}
