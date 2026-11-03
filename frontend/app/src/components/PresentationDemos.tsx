import { useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, Clock, Download, GitCompareArrows, Play, RefreshCw, ShieldCheck } from 'lucide-react';
import type { LiveJobStatus } from '../types';

import { downloadJson } from '../services/research';
import { formatDuration, measuredPercent, methodLabel, priorityLabel, runOutcome } from '../services/jobs';

import { parseCollection, optimizerUpdates, previewPair } from '../services/demos';
import type { DemoCollection } from '../services/demos';

export function PresentationDemos({ onPresent, onOpen }: { onPresent: (job: LiveJobStatus) => void; onOpen: (job: LiveJobStatus) => void }) {
  const [collection, setCollection] = useState<DemoCollection | null>(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    const load = async () => {
      try {
        const response = await fetch('./artifacts/presentation_demos.json', { cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]) });
        if (!response.ok) throw new Error('The saved demo collection is unavailable.');
        const data = parseCollection(await response.json());
        if (!alive) return;
        setCollection(data); setError('');
        if (data.cases.some(item => !['COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status))) timer = setTimeout(load, 15000);
      } catch (failure) {
        if (alive) setError((failure as Error).message);
      }
    };
    void load();
    return () => { alive = false; controller.abort(); clearTimeout(timer); };
  }, [revision]);
  const cases = collection?.cases ?? [];
  const completed = cases.filter(item => item.status === 'COMPLETED' && item.job?.result);
  const facts = completed.reduce((sum, item) => sum + (item.job?.result?.audit.facts_requested ?? 0), 0);
  return <div className="studio-page presentation-demos demo-studio">
    <div className="studio-heading demo-heading"><div><span className="studio-eyebrow">SAVED EXPERIMENTS · PRESENTATION COLLECTION</span><h1>Present the evidence.</h1><p>Three Full experiments, organised for a clear walkthrough.</p></div><div className="demo-heading-actions"><button className="button secondary small" disabled={!collection} onClick={() => collection && downloadJson(collection, 'atu-presentation-demos.json')}><Download size={15} />Export collection</button><button className="icon-button" aria-label="Refresh demo collection" title="Refresh demo collection" onClick={() => setRevision(n => n + 1)}><RefreshCw size={16} /></button></div></div>
    <section className="demo-launcher evidence-hero" aria-labelledby="demo-launcher-title"><div className="demo-launcher-copy"><span className="demo-launcher-icon"><Play size={21} /></span><div><span className="studio-eyebrow">THE PRESENTATION EDITION</span><h2 id="demo-launcher-title">A clear story. Every claim traceable.</h2><p>Follow real model responses from original exposure to the final recovery audit. Each case opens its complete measured evidence.</p></div></div><div className="demo-launcher-actions"><button className="button primary" disabled={!completed.length} onClick={() => completed[0]?.job && onPresent(completed[0].job)}><Play size={15} />Start the walkthrough<ArrowRight size={15} /></button><div className="demo-hero-counts"><span><b>{completed.length}<small>/ 3</small></b>Full cases ready</span><span><b>{facts}</b>selected fact entries</span></div></div></section>
    <div className="demo-presentation-guide" aria-label="Suggested presentation sequence"><span>THE WALKTHROUGH</span><ol><li><b>01</b>Original exposure</li><li><b>02</b>Unlearning attempts</li><li><b>03</b>Recovery checks</li></ol><span className="demo-no-training"><ShieldCheck size={13} />Opening demos starts no training</span></div>
    {error && <div className="demo-collection-notice" role="alert"><p>{error} {collection ? 'Showing the last loaded collection. Refresh to retrieve the latest evidence.' : 'Your saved runs are available in Run history.'}</p><button className="text-button" onClick={() => setRevision(n => n + 1)}>Try again</button></div>}
    {!collection && !error && <p role="status">Opening the saved experiment collection…</p>}
    <div className="demo-cases-heading"><div><h2>Choose a demonstration</h2><p>Each case includes its actual responses and measured outcome.</p></div><a className="demo-comparison-link" href="./artifacts/feedback-validation/index.html"><GitCompareArrows size={16} /><span>View matched V2 / V3 study</span><ArrowRight size={14} /></a></div>
    <div className="demo-collection-grid">{cases.map((item, index) => {
      const job = item.job; const result = job?.result; const audit = result?.audit;
      const ready = job?.status === 'COMPLETED' && Boolean(result);
      const outcome = job ? runOutcome(job) : { label: 'Queued in collection', tone: 'neutral' };
      const updates = job ? optimizerUpdates(job) : null;
      const pair = job ? previewPair(job) : undefined;
      return <article className={"demo-case demo-case-" + outcome.tone} key={item.id} aria-labelledby={`demo-title-${index}`}>
        <div className="demo-case-top"><span className="demo-case-number">CASE 0{index + 1}</span><span className={'studio-badge ' + outcome.tone}>{ready && outcome.tone === 'green' && <CheckCircle2 size={12} />}{outcome.label}</span></div>
        <h2 id={`demo-title-${index}`}>{job?.author_name ?? item.subtitle ?? item.title}</h2><h3 className="demo-case-subtitle">{item.title}</h3><p className="demo-case-purpose">{item.purpose}</p>{result?.provenance?.selected_questions?.length ? <details className="demo-fact-focus"><summary>{result.provenance.selected_questions.length} selected {result.provenance.selected_questions.length === 1 ? 'fact' : 'facts'}<ArrowRight size={13} /></summary><ol>{result.provenance.selected_questions.map((question, questionIndex) => <li key={questionIndex}>{question}</li>)}</ol></details> : null}
        <div className="demo-case-score"><div><strong>{audit && audit.validated_attacks > 0 ? `${audit.verified_suppressions}/${audit.validated_attacks}` : '—'}</strong><span>calibrated checks suppressed</span></div><ShieldCheck size={23} aria-hidden="true" /></div>
        <div className="demo-case-measures"><div><strong>{audit?.residual_leaks ?? '—'}</strong><span>residual recoveries</span></div><div><strong>{audit?.inconclusive_attacks ?? '—'}</strong><span>inconclusive checks</span></div><div><strong>{measuredPercent(audit?.retain_utility_rate)}</strong><span>retain answer overlap</span></div><div><strong>{audit ? `${audit.facts_with_validated_checks}/${audit.facts_requested}` : '—'}</strong><span>selected facts checked</span></div></div>
        <div className="demo-case-execution"><span><Clock size={13} />{job ? formatDuration(job.elapsed_seconds) : 'Pending'}</span><span>{methodLabel(result?.v3?.best_method)} · {updates === null ? 'Updates not recorded' : `${updates} updates`}</span></div>
        {pair && <details className="demo-pair"><summary>Preview actual responses<ArrowRight size={14} /></summary><p className="demo-pair-question">{pair.after.prompt}</p><span>Original target</span><blockquote>{pair.before?.response_text}</blockquote><span>After unlearning</span><blockquote>{pair.after.response_text}</blockquote><small>Target suppression can produce an incorrect replacement answer. Inspect the full report for controls.</small></details>}
        {job && !ready && <p className="demo-case-pending" role="status">{job.error || job.current_step}</p>}
        <div className="demo-case-buttons"><button className="button primary" disabled={!ready} onClick={() => job && onPresent(job)} aria-label={`Present evidence for ${job?.author_name ?? item.title}`}><Play size={14} />Present evidence</button><button className="button secondary" disabled={!ready} onClick={() => job && onOpen(job)}>Inspect report<ArrowRight size={14} /></button></div>
        <details className="demo-case-provenance"><summary>Settings and provenance</summary><dl><dt>Run ID</dt><dd>{item.job_id ?? 'Not launched'}</dd><dt>Evaluation</dt><dd>Full · separate held-out evaluation and calibrated controls</dd><dt>Retain sample</dt><dd>{audit?.retain_utility_examples ?? '—'} unrelated answers</dd><dt>Method request</dt><dd>{job?.settings?.method === 'auto' ? `Automatic · ${priorityLabel(job.settings.priority)}` : methodLabel(job?.settings?.method)}</dd></dl>{result?.provenance?.selected_questions?.map(question => <p key={question}>{question}</p>)}</details>
      </article>;
    })}</div>
    <section className="demo-collection-boundary"><ShieldCheck size={19} /><div><strong>Clear evidence, with its scope intact.</strong><p>These presentation cases were selected using prior observations, rather than a random benchmark. Suppression concerns the tested prompts. Retain overlap measures each run’s recorded sample of unrelated answers, and does not establish preservation of every fact. The separate matched V2 / V3 study includes partial outcomes and residual leakage.</p>{collection?.archive_url?.startsWith('./artifacts/') && !collection.archive_url.includes('..', 2) && <a className="demo-archive-download" href={collection.archive_url} download="atu-previous-presentation-demos.json"><Download size={13} />Previous presentation collection · JSON</a>}</div></section>
  </div>;
}
