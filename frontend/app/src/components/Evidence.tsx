import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, ChevronDown, Shield, AlertTriangle, ArrowRight, Fingerprint, ArrowUpRight, ScanLine } from 'lucide-react';
import type { Fact, Entity, PairedAttack, Calibration } from '../types';
import { label, selectableFact } from '../services/research';

export function VerdictBadge({ verdict, control = false }: { verdict: string; control?: boolean }) {
  const values: Record<string, [string, string]> = {
    CONFIRMED_LEAK: ['Exposed', 'red'], PARTIAL_LEAK: ['Partial exposure', 'amber'], NOT_EXPOSED: ['Not exposed', 'neutral'], UNCERTAIN: ['Uncertain', 'amber'],
    FULL_RECOVERY: [control ? 'Knowledge recovered' : 'Full recovery', control ? 'mint' : 'red'], PARTIAL_RECOVERY: ['Partial recovery', 'amber'], NO_RECOVERY: ['No recovery', 'mint'],
    VERIFIED_SUPPRESSION: ['Verified suppression', 'mint'], RESIDUAL_LEAKAGE: ['Residual leakage', 'red'], INCONCLUSIVE: ['Inconclusive', 'amber'],
    SUPPRESSED: ['Suppressed', 'mint'], UNLEARNING: ['Unlearning', 'blue'], STUBBORN: ['Stubborn', 'amber'], LEAKING: ['Leaking', 'red'],
  };
  const [title, color] = values[verdict] ?? [label(verdict), 'neutral'];
  return <span className={`badge ${color}`}><span className="status-dot" />{title}</span>;
}

export function FactExposureCard({ fact, entity, selected, selectable, onSelect }: { fact: Fact; entity: Entity; selected: boolean; selectable: boolean; onSelect: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [evidenceIndex, setEvidenceIndex] = useState(0);
  const allowed = selectable && selectableFact(fact, entity);
  const evidence = fact.sample_responses[evidenceIndex];
  return <motion.article layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .25 }} className={`fact-card ${selected ? 'selected' : ''}`}>
    <div className="fact-top"><span className="eyebrow">{label(fact.attribute_key)}</span>{selectable ? <button className={`fact-checkbox ${selected ? 'checked' : ''}`} aria-label={`Select ${label(fact.attribute_key)}`} aria-pressed={selected} disabled={!allowed} onClick={onSelect}>{selected && <Check size={15} />}</button> : <Fingerprint size={17} className="muted" />}</div>
    <h3>{fact.target_value}</h3><VerdictBadge verdict={fact.verdict} />
    <div className="fact-meta"><span>{fact.probes_leaked} / {fact.probes_tested} probes recovered</span><span>{fact.leaking_styles.length ? label(fact.leaking_styles[0]) : 'No recorded recovery'}</span></div>
    {selectable && !allowed && <small className="selection-reason">{entity.role === 'RETAIN_CONTROL' ? 'Protected retain control' : entity.role === 'NEGATIVE_CONTROL' ? 'No exposure to unlearn' : 'No recoverable evidence'}</small>}
    <button className="evidence-toggle" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}><ScanLine size={14} />{expanded ? 'Close evidence' : 'Inspect evidence'}<ChevronDown size={14} className={expanded ? 'rotate' : ''} /></button>
    {expanded && <div className="fact-evidence"><label className="input-label" htmlFor={`style-${fact.fact_id}`}>Recorded probe</label><select id={`style-${fact.fact_id}`} className="select-input" value={evidenceIndex} onChange={e => setEvidenceIndex(Number(e.target.value))}>{fact.sample_responses.map((sample, index) => <option key={index} value={index}>{label(sample.style)}</option>)}</select>{evidence ? <><span className="eyebrow">Question</span><p>{evidence.prompt}</p><span className="eyebrow">Target model response</span><blockquote>{evidence.response}</blockquote><div className="evidence-foot">{evidence.recovered ? `Backend recovery match: ${String(evidence.recovered)}` : 'Backend recorded no recovery for this probe.'}</div></> : <p>No response sample exported.</p>}</div>}
  </motion.article>;
}

export function CalibrationBadge({ calibration }: { calibration?: Calibration }) {
  return calibration === 'INCONCLUSIVE' ? <span className="calibration amber-text"><AlertTriangle size={14} />Inconclusive · baseline check</span> : calibration ? <span className="calibration"><Shield size={14} />Calibrated recovery check</span> : <span className="calibration muted"><Fingerprint size={14} />Calibration not exported</span>;
}

export function DiscoveryEvidencePanel({ fact }: { fact: Fact }) {
  const sample = fact.sample_responses.find(s => s.recovered) ?? fact.sample_responses[0];
  if (!sample) return null;
  return <motion.div key={fact.fact_id} initial={{ opacity: 0, y: 7 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .2 }} className="discovery-spotlight"><div className="spotlight-header"><span><ScanLine size={15} />RECORDED PROBE · {label(sample.style)}</span><VerdictBadge verdict={fact.verdict} /></div><p>{sample.prompt}</p><blockquote>{sample.response}</blockquote><div className="spotlight-foot"><ArrowRight size={13} /><span>{sample.recovered ? `Backend matched: ${String(sample.recovered)}` : 'No target recovery recorded in this response.'}</span></div></motion.div>;
}

export function RedTeamAttackCard({ pair, active = false, control = false }: { pair: PairedAttack; active?: boolean; control?: boolean }) {
  const [details, setDetails] = useState(false);
  const attack = pair.after;
  return <motion.article initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .25 }} className={`attack-card ${active ? 'latest' : ''}`}>
    <div className="attack-top"><div><span className="mono small-text">{attack.probe_id}</span><span className="attack-category">{label(attack.category)}</span></div><VerdictBadge verdict={attack.verdict} control={control} /></div>
    <p className="attack-prompt">{attack.prompt}</p><blockquote>{attack.response_text}</blockquote>
    <div className="attack-bottom"><CalibrationBadge calibration={pair.calibration} /><button className="text-button" aria-expanded={details} onClick={() => setDetails(!details)}>{details ? 'Hide controls' : 'Inspect controls'}<ChevronDown size={14} /></button></div>
    {details && <div className="attack-controls"><div><span className="eyebrow">Target model · before ATU</span><p>{pair.before?.response_text ?? 'No matching response exported.'}</p>{pair.before && <VerdictBadge verdict={pair.before.verdict} control={control} />}</div><div><span className="eyebrow">Base model · control</span><p>{pair.base?.response_text ?? 'No matching response exported.'}</p>{pair.base && <VerdictBadge verdict={pair.base.verdict} control={control} />}</div><div className="classifier-note"><span className="eyebrow">Backend explanation</span><p>{attack.explanation}</p>{pair.calibration && <VerdictBadge verdict={pair.calibration} />}{!pair.calibration && <small>No calibrated verdict is published for this probe. Raw recovery alone does not establish verified suppression.</small>}</div></div>}
  </motion.article>;
}

export function BeforeAfterComparison({ pair, checkpointLabel = 'ATU v2 checkpoint' }: { pair: PairedAttack; checkpointLabel?: string }) {
  const tone = pair.calibration === 'RESIDUAL_LEAKAGE' ? 'residual' : pair.calibration === 'INCONCLUSIVE' ? 'inconclusive' : pair.calibration ? 'suppression' : 'uncalibrated';
  return <div className="comparison"><div className="comparison-question"><div className="comparison-question-top"><span className="eyebrow">Identical recorded question</span>{pair.calibration ? <VerdictBadge verdict={pair.calibration} /> : <span className="tiny-pill">CALIBRATION NOT EXPORTED</span>}</div><h3>{pair.after.prompt}</h3></div><div className="comparison-columns"><article className="response-panel before"><div className="response-label"><span className="number-pill">01</span><span>BEFORE<span>Target model</span></span><ArrowUpRight size={20} /></div><blockquote>{pair.before?.response_text ?? 'Matching target response unavailable.'}</blockquote>{pair.before && <VerdictBadge verdict={pair.before.verdict} />}</article><div className="atu-transform"><span>ATU</span><ArrowRight size={23} /></div><article className={`response-panel after ${tone}`}><div className="response-label"><span className="number-pill">02</span><span>AFTER<span>{checkpointLabel}</span></span><Shield size={20} /></div><blockquote>{pair.after.response_text}</blockquote><VerdictBadge verdict={pair.after.verdict} /></article></div><div className="comparison-footer"><CalibrationBadge calibration={pair.calibration} />{pair.calibration && <VerdictBadge verdict={pair.calibration} />}</div></div>;
}
