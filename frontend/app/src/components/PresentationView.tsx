import { useEffect, useId, useMemo, useState } from 'react';
import { ArrowDown, ArrowLeft, ArrowRight, Check, ChevronRight, CircleHelp, Fingerprint, Layers3, LockKeyhole, Search, ShieldCheck, ShieldAlert, Sparkles, X } from 'lucide-react';
import type { LiveJobStatus, PairedAttack } from '../types';
import { formatDuration, measuredPercent, methodLabel, outcomeDescription, runOutcome } from '../services/jobs';
import { useDialog } from '../hooks/useDialog';
import { optimizerUpdates } from '../services/demos';
import '../presentation.css';

const slideNames = ['The request', 'Discover exposure', 'Compare responses', 'Measure the outcome', 'Evidence & boundaries'];

function verdictLabel(value?: string) {
  return ({ FULL_RECOVERY: 'Target fact recovered', PARTIAL_RECOVERY: 'Part of the target recovered', NO_RECOVERY: 'Target fact not recovered', UNCERTAIN: 'Uncertain response', DEGENERATE: 'Generation quality issue' } as Record<string, string>)[value || ''] || 'Classification not recorded';
}

function responseText(value?: string) { return value?.trim() || 'No response was exported for this check.'; }
function recordedCount(value: unknown) { return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null; }

function PairStatus({ pair }: { pair?: PairedAttack }) {
  const label = pair?.calibration === 'VERIFIED_SUPPRESSION' ? 'Suppression validated by controls'
    : pair?.calibration === 'RESIDUAL_LEAKAGE' ? 'Residual information recovered'
      : 'Control validation incomplete';
  return <span className={'presentation-tag ' + (pair?.calibration === 'RESIDUAL_LEAKAGE' ? 'presentation-tag-red' : pair?.calibration === 'VERIFIED_SUPPRESSION' ? 'presentation-tag-mint' : 'presentation-tag-amber')}>
    {pair?.calibration === 'VERIFIED_SUPPRESSION' ? <Check size={14} /> : <CircleHelp size={14} />}{label}
  </span>;
}

/** Read-only, five-part walkthrough of one saved experiment. No inference or training is launched. */
export function PresentationView({ job, onClose, onInspect }: { job: LiveJobStatus; onClose: () => void; onInspect?: () => void }) {
  const [slide, setSlide] = useState(0);
  const [pairId, setPairId] = useState('');
  const dialog = useDialog(onClose);
  const headingId = useId();
  const result = job.result;
  const facts = result?.facts || job.discovery?.facts || [];
  const audit = result?.audit;
  const trials = result?.v3?.trials || [];
  const recordedOutcome = runOutcome(job);
  const questions = result?.provenance?.selected_questions || [];
  const selectedCount = audit?.facts_requested ?? (questions.length || job.settings?.fact_indices?.length || facts.length);
  const paired = useMemo(() => (result?.attacks || []).filter(pair => pair.after && pair.before && pair.before.prompt === pair.after.prompt), [result]);
  // Show a remaining leak first when one exists; the demonstration must not hide failures.
  const pair = paired.find(item => item.after.probe_id === pairId)
    || paired.find(item => item.calibration === 'RESIDUAL_LEAKAGE')
    || paired.find(item => item.calibration === 'VERIFIED_SUPPRESSION') || paired[0];
  const discoveryFact = facts.find(fact => fact.sample_responses?.some(evidence => ['FULL_RECOVERY', 'PARTIAL_RECOVERY'].includes(evidence.verdict || '')))
    || facts.find(fact => fact.sample_responses?.length) || facts[0];
  const discoveryEvidence = discoveryFact?.sample_responses?.find(evidence => ['FULL_RECOVERY', 'PARTIAL_RECOVERY'].includes(evidence.verdict || '')) || discoveryFact?.sample_responses?.[0];
  const exposed = facts.filter(fact => ['CONFIRMED_LEAK', 'PARTIAL_LEAK'].includes(fact.verdict)).length;
  const steps = optimizerUpdates(job);
  const stepsRecorded = steps !== null;
  const validated = recordedCount(audit?.validated_attacks);
  const suppressed = recordedCount(audit?.verified_suppressions);
  const residual = recordedCount(audit?.residual_leaks);
  const inconclusive = recordedCount(audit?.inconclusive_attacks);
  const totalChecks = recordedCount(audit?.total_attacks) ?? (Array.isArray(result?.attacks) ? result.attacks.length : null);
  const hasSuppressionRatio = validated !== null && validated > 0 && suppressed !== null;
  const hasRecoveryCounts = validated !== null && suppressed !== null && residual !== null && inconclusive !== null;
  const outcome = recordedOutcome.tone === 'green' && !hasRecoveryCounts ? { label: 'Verification measurements incomplete', tone: 'amber' } : recordedOutcome;
  const description = hasRecoveryCounts ? outcomeDescription(job) : 'Aggregate recovery measurements were not fully exported. Inspect the available responses and controls; this record cannot establish a complete outcome.';
  const fraction = hasSuppressionRatio ? Math.max(0, Math.min(1, suppressed / validated)) : 0;
  const inspectReport = onInspect || onClose;
  const method = result?.v3?.best_method || (result?.provenance?.method !== 'auto' ? String(result?.provenance?.method || job.settings?.method || '') : '');
  const historical = Boolean(result?.scoring_recheck);
  const preliminary = job.mode === 'fast' || result?.evaluation_scope === 'preliminary_screening';

  useEffect(() => { dialog.current?.querySelector<HTMLElement>('.presentation-main')?.scrollTo({ top: 0 }); }, [slide, dialog]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes((event.target as HTMLElement)?.tagName)) return;
      if (event.key === 'ArrowRight') { event.preventDefault(); setSlide(value => Math.min(slideNames.length - 1, value + 1)); }
      if (event.key === 'ArrowLeft') { event.preventDefault(); setSlide(value => Math.max(0, value - 1)); }
      if (event.key === 'Home') { event.preventDefault(); setSlide(0); }
      if (event.key === 'End') { event.preventDefault(); setSlide(slideNames.length - 1); }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, []);

  return <div className="presentation-stage" role="dialog" aria-modal="true" aria-labelledby={headingId} ref={dialog} tabIndex={-1}>
    <header className="presentation-header">
      <div className="presentation-brand"><span className="presentation-brand-mark"><Layers3 size={22} /></span><span>ATU <em>Research Studio</em></span><span className="presentation-header-divider" /><span className="presentation-header-label">Evidence presentation</span></div>
      <button className="presentation-close" onClick={onClose} aria-label="Close presentation"><span>Exit presentation</span><X size={19} /></button>
    </header>
    <div className="presentation-body">
      <aside className="presentation-rail" aria-label="Presentation chapters">
        <span className="presentation-overline">THE EXPERIMENT</span>
        <strong>{job.author_name}</strong>
        <span className="presentation-rail-subtitle">{preliminary ? 'Quick screening' : 'Full experiment'}<br />Saved execution evidence</span>
        <nav>{slideNames.map((name, index) => <button key={name} aria-current={slide === index ? 'step' : undefined} onClick={() => setSlide(index)}><span>{String(index + 1).padStart(2, '0')}</span><span>{name}</span>{slide === index && <ChevronRight size={14} />}</button>)}</nav>
        <div className="presentation-rail-note"><LockKeyhole size={15} /><span>Read-only walkthrough<br />No GPU execution required</span></div>
      </aside>
      <main className="presentation-main" key={slide}>
        <span className="presentation-overline">{String(slide + 1).padStart(2, '0')} / {String(slideNames.length).padStart(2, '0')} <span className="presentation-overline-line" /> {slideNames[slide]}</span>

        {slide === 0 && <>
          <div className="presentation-hero-grid">
            <div><span className="presentation-tag"><Sparkles size={14} />Selective machine unlearning</span><h1 id={headingId}>Make a model<br /><span>forget with evidence.</span></h1><p className="presentation-lead">Discover a fact in model memory. Attempt to remove it. Test what remains—and what was preserved.</p><div className="presentation-request"><span className="presentation-overline">THIS SAVED REQUEST</span><strong>{job.author_name}</strong><p>{selectedCount ? `${selectedCount} selected ${selectedCount === 1 ? 'fact' : 'facts'}` : 'Selected fact count not exported'} · {methodLabel(method)} · {formatDuration(job.elapsed_seconds)}</p></div></div>
            <div className="presentation-flow" aria-label="Discover, unlearn, challenge and verify workflow"><div className="presentation-orbit" /><div className="presentation-core"><Layers3 size={36} /><strong>ATU</strong><span>Adaptive Targeted Unlearning</span></div>{[{ title: 'Discover', detail: 'Inspect original exposure', icon: <Search size={18} /> }, { title: 'Unlearn', detail: 'Update a separate checkpoint', icon: <Fingerprint size={18} /> }, { title: 'Challenge', detail: 'Try recovering the fact', icon: <ShieldAlert size={18} /> }, { title: 'Verify', detail: 'Compare with controls', icon: <ShieldCheck size={18} /> }].map((step, index) => <div className={'presentation-flow-node presentation-node-' + index} key={step.title}><span>{step.icon}</span><div><strong>{step.title}</strong><small>{step.detail}</small></div></div>)}</div>
          </div>
          <div className="presentation-scope-strip"><span><b>DATASET</b>{job.source_kind === 'custom' || result?.provenance?.source_kind === 'custom' ? 'Custom candidate facts' : 'TOFU · fictional author knowledge'}</span><span><b>MODE</b>{preliminary ? 'Preliminary screening' : 'Full experiment'}</span><span><b>REPORT</b>{historical ? 'Historical responses rechecked' : 'Saved live experiment'}</span></div>
        </>}

        {slide === 1 && <>
          <h1 id={headingId}>First, establish<br /><span>what the model reveals.</span></h1>
          <p className="presentation-lead">Reference answers describe the dataset. The actual generated response is evidence of exposure.</p>
          <div className="presentation-discovery-grid">
            <div className="presentation-card presentation-discovery-metric"><Search size={26} /><strong>{facts.length ? `${exposed} / ${facts.length}` : 'Not recorded'}</strong><span>exported discovery facts exposed</span><p>Includes confirmed and partial exposure. This is limited to the candidate facts tested.</p>{discoveryFact && <div className="presentation-fact-reference"><b>DATASET REFERENCE</b><p>{discoveryFact.canonical_qa?.answer || discoveryFact.target_value || 'Reference answer not exported.'}</p></div>}</div>
            <div className="presentation-card presentation-transcript"><div className="presentation-card-heading"><span className="presentation-overline">ORIGINAL MODEL · DISCOVERY</span><span className="presentation-tag">{discoveryEvidence?.style?.replaceAll('_', ' ') || 'Available evidence'}</span></div><label>Question asked</label><p className="presentation-question">{discoveryEvidence?.prompt || discoveryFact?.canonical_qa?.question || 'No discovery question was exported.'}</p><div className="presentation-response"><span>MODEL RESPONSE</span><blockquote>{responseText(discoveryEvidence?.response)}</blockquote></div><div className="presentation-response-footer"><span className="presentation-evidence-dot" />{discoveryEvidence ? verdictLabel(discoveryEvidence.verdict) : 'No generated discovery response available'}</div></div>
          </div>
        </>}

        {slide === 2 && <>
          <div className="presentation-slide-heading"><div><h1 id={headingId}>Same question.<br /><span>Different checkpoint.</span></h1><p className="presentation-lead">Actual exported responses, compared on an identical prompt.</p></div>{paired.length > 1 && <label className="presentation-select-label">Choose an exported test<select aria-label="Presentation recovery question" value={pair?.after.probe_id || ''} onChange={event => setPairId(event.target.value)}>{paired.map(item => <option key={item.after.probe_id} value={item.after.probe_id}>{item.after.probe_id} · {item.calibration === 'RESIDUAL_LEAKAGE' ? 'Residual leak' : item.calibration === 'VERIFIED_SUPPRESSION' ? 'Suppressed' : 'Inconclusive'}</option>)}</select></label>}</div>
          {pair ? <><div className="presentation-comparison-prompt"><span className="presentation-overline">SHARED PROMPT</span><p>{pair.after.prompt}</p></div><div className="presentation-comparison-grid"><div className="presentation-card presentation-before"><div className="presentation-card-heading"><span className="presentation-overline">BEFORE UNLEARNING</span><span className="presentation-model-dot" /></div><blockquote>{responseText(pair.before?.response_text)}</blockquote><span className="presentation-transcript-verdict">{verdictLabel(pair.before?.verdict)}</span></div><div className={'presentation-card presentation-after presentation-after-' + (pair.calibration === 'VERIFIED_SUPPRESSION' ? 'verified' : pair.calibration === 'RESIDUAL_LEAKAGE' ? 'residual' : pair.calibration === 'INCONCLUSIVE' ? 'inconclusive' : 'unverified')}><div className="presentation-card-heading"><span className="presentation-overline">AFTER UNLEARNING</span><Fingerprint size={18} /></div><blockquote>{responseText(pair.after.response_text)}</blockquote><span className="presentation-transcript-verdict">{verdictLabel(pair.after.verdict)}</span></div></div><div className="presentation-calibration-row"><PairStatus pair={pair} /><span>{pair.base ? `Base model control: ${verdictLabel(pair.base.verdict).toLowerCase()}.` : 'Base-model response not exported.'} Suppression alone does not establish answer quality.</span></div></> : <div className="presentation-empty"><CircleHelp size={32} /><h2>No matched response pair was exported.</h2><p>This record cannot demonstrate a before/after comparison on an identical question. Available aggregate measurements follow.</p></div>}
        </>}

        {slide === 3 && <>
          <h1 id={headingId}>An outcome you<br /><span>can inspect.</span></h1>
          <div className={'presentation-outcome presentation-outcome-' + outcome.tone}>{outcome.tone === 'green' ? <ShieldCheck size={23} /> : <ShieldAlert size={23} />}<div><strong>{outcome.label}</strong><p>{description}</p></div></div>
          <div className="presentation-results-grid"><div className="presentation-card presentation-ring-card"><div className={'presentation-ring presentation-ring-' + outcome.tone} style={{ background: `conic-gradient(var(--presentation-ring-color) ${fraction * 360}deg, #28433c ${fraction * 360}deg)` }}><div><strong>{hasSuppressionRatio ? `${suppressed}/${validated}` : '—'}</strong><span>validated checks<br />suppressed</span></div></div><p>{hasSuppressionRatio ? 'Original-target and base-model controls define the denominator.' : validated === 0 ? 'No validated control checks were recorded.' : 'Suppression counts were not fully exported.'}</p></div><div className="presentation-stat-grid"><div className="presentation-card presentation-stat"><span>Residual recovery</span><strong>{residual ?? '—'}</strong><small>{totalChecks !== null ? `of ${totalChecks} exported checks` : 'Check count not exported'}</small></div><div className="presentation-card presentation-stat"><span>Retain answer overlap</span><strong>{measuredPercent(audit?.retain_utility_rate)}</strong><small>{audit?.retain_utility_examples ? `${audit.retain_utility_examples} unrelated answer examples` : 'Evaluation sample count not exported'}</small></div><div className="presentation-card presentation-stat"><span>Optimizer updates</span><strong>{steps ?? '—'}</strong><small>{stepsRecorded ? `Total across ${trials.length} recorded ${trials.length === 1 ? 'attempt' : 'attempts'}` : 'Update counts not fully exported'}</small></div><div className="presentation-card presentation-stat"><span>Inconclusive checks</span><strong>{inconclusive ?? '—'}</strong><small>{inconclusive === null ? 'Count not exported' : 'Excluded from validated suppression'}</small></div></div></div>
          <p className="presentation-footnote">Retain answer overlap measures a limited sample of unrelated answers. It is not a percentage of all knowledge preserved.</p>
        </>}

        {slide === 4 && <>
          <h1 id={headingId}>Transparent evidence.<br /><span>Clear boundaries.</span></h1><p className="presentation-lead">A credible demonstration makes its scope as visible as its result.</p>
          <div className="presentation-closing-grid"><div className="presentation-card presentation-boundaries"><span className="presentation-overline">WHAT THIS RUN ESTABLISHES</span><h2>{selectedCount ? `${selectedCount} selected ${selectedCount === 1 ? 'fact' : 'facts'}.` : 'A bounded set of facts.'}<br />{totalChecks !== null ? `${totalChecks} exported recovery checks.` : 'Recovery check count not exported.'}</h2><ul><li><Check size={16} /><span>Recorded prompts, generated responses and checkpoint identity can be inspected in the full report.</span></li><li><CircleHelp size={16} /><span>{historical ? 'Saved responses were reclassified. Missing historical tests were not regenerated.' : preliminary ? 'This was preliminary screening with reduced computation; it is not a complete audit.' : 'Passing configured questions does not prove that every possible recovery attack fails.'}</span></li><li><CircleHelp size={16} /><span>{steps === 0 ? 'No optimizer updates completed. This record cannot establish a useful training attempt.' : 'Failure to recover a target answer does not guarantee factual accuracy or complete erasure.'}</span></li></ul></div><div className="presentation-card presentation-provenance"><span className="presentation-overline">TRACEABLE RUN RECORD</span><dl><dt>Run</dt><dd>{job.job_id}</dd><dt>Selected method</dt><dd>{methodLabel(method)}</dd><dt>Target checkpoint</dt><dd>{result?.provenance?.target_checkpoint_hash || job.discovery?.checkpoint_hash || 'Not exported'}</dd><dt>Output checkpoint</dt><dd>{result?.checkpoint_hash || 'Not exported'}</dd><dt>Scoring revision</dt><dd>{String(result?.scoring_recheck?.revision || result?.provenance?.scoring_revision || 'Historical / not exported')}</dd><dt>Fact coverage</dt><dd>{typeof audit?.facts_with_validated_checks === 'number' && typeof audit?.facts_requested === 'number' ? `${audit.facts_with_validated_checks} / ${audit.facts_requested} selected facts validated` : 'Fact-level coverage not exported'}</dd></dl></div></div><div className="presentation-closing-line"><ShieldCheck size={23} /><p>Measured forgetting.<span> Evidence before claims.</span></p><button onClick={inspectReport}>Inspect the full report <ArrowRight size={17} /></button></div>
        </>}
      </main>
    </div>
    <footer className="presentation-footer"><div className="presentation-key-hint"><span>←</span><span>→</span> Navigate <i /> Esc to exit</div><div className="presentation-progress" aria-label={`Slide ${slide + 1} of ${slideNames.length}`}>{slideNames.map((name, index) => <button key={name} className={index === slide ? 'active' : ''} aria-label={`Go to slide ${index + 1}: ${name}`} aria-current={index === slide ? 'step' : undefined} onClick={() => setSlide(index)} />)}</div><div className="presentation-controls"><span aria-live="polite" aria-atomic="true">{String(slide + 1).padStart(2, '0')} <em>/ {String(slideNames.length).padStart(2, '0')}</em></span><button aria-label="Previous slide" disabled={slide === 0} onClick={() => setSlide(value => value - 1)}><ArrowLeft size={19} /></button><button aria-label={slide === slideNames.length - 1 ? 'Return to full report' : 'Next slide'} onClick={() => slide === slideNames.length - 1 ? inspectReport() : setSlide(value => value + 1)}>{slide === slideNames.length - 1 ? <ArrowDown size={19} /> : <ArrowRight size={19} />}</button></div></footer>
  </div>;
}
