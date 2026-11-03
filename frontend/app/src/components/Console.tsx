import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, MousePointer2, BrainCircuit, Swords, ShieldCheck, Check, ChevronRight, X, Download, FileJson, ExternalLink, ShieldAlert, Activity, CircleCheck, Target, SlidersHorizontal, ScanLine } from 'lucide-react';
import type { Bundle, Round, Stage, TargetState } from '../types';
import { stages } from '../workflow';
import { VerdictBadge } from './Evidence';
import { downloadJson } from '../services/research';

export const stageIcons = { discover: Search, select: MousePointer2, unlearn: BrainCircuit, attack: Swords, verify: ShieldCheck };
export function PipelineStepper({ stage, reached, onNavigate }: { stage: Stage; reached: number; onNavigate: (stage: Stage) => void }) {
  return <nav className="pipeline" aria-label="Research pipeline">{stages.map((value, index) => {
    const Icon = stageIcons[value]; const complete = index < reached;
    return <div className="pipeline-segment" key={value}><button aria-current={stage === value ? 'step' : undefined} disabled={index > reached} className={`pipeline-step ${stage === value ? 'current' : ''} ${complete ? 'complete' : ''}`} onClick={() => onNavigate(value)}><span className="step-icon">{complete ? <Check size={16} /> : <Icon size={17} />}</span><span className="step-name">{value}</span><span className="step-number">0{index + 1}</span></button>{index < stages.length - 1 && <ChevronRight size={14} className="step-arrow" />}</div>;
  })}</nav>;
}

const stateMeta = [
  { key: 'suppressed_targets', name: 'Suppressed', tone: 'mint', detail: 'Pressure stopped', icon: CircleCheck },
  { key: 'unlearning_targets', name: 'Unlearning', tone: 'blue', detail: 'Pressure active', icon: Activity },
  { key: 'stubborn_targets', name: 'Stubborn', tone: 'amber', detail: 'Additional pressure', icon: Target },
  { key: 'leaking_targets', name: 'Leaking', tone: 'red', detail: 'Probe recovery flagged', icon: ShieldAlert },
] as const;

export function AdaptiveLoopVisualizer({ round, traceIndex, total, config, finalTargets }: { round: Round; traceIndex: number; total: number; config: Record<string, number>; finalTargets?: TargetState[] }) {
  const [showTargets, setShowTargets] = useState(false);
  const [stateFilter, setStateFilter] = useState('ALL');
  const tiles: string[] = stateMeta.flatMap(state => Array.from({ length: round[state.key] ?? 0 }, () => state.tone));
  if (!tiles.length) tiles.push(...Array.from({ length: round.active_targets }, () => 'neutral'));
  const currentOperation = round.should_stop ? 4 : round.action === 'INITIALIZATION' ? 0 : 1;
  const operations = ['Measure', 'Adapt', 'Unlearn', 'Verify', 'Decide'];
  const targets = finalTargets?.filter(t => stateFilter === 'ALL' || t.state === stateFilter) ?? [];
  return <div className="adaptive-board">
    <div className="board-top"><div><span className="eyebrow">Adaptive target controller</span><h3>{round.action === 'INITIALIZATION' ? '40 targets. One adaptive controller.' : round.should_stop ? 'Retain guardrail triggered.' : 'Pressure follows the evidence.'}</h3></div><span className="round-label">ROUND <strong>{round.round}</strong><small>Record {traceIndex + 1} / {total}</small></span></div>
    <div className="adaptive-loop">{operations.map((operation, index) => <div key={operation} className={index === currentOperation ? 'active' : ''}><span>{index === 1 ? <SlidersHorizontal size={14} /> : index === 3 ? <ScanLine size={14} /> : <span className="loop-dot" />}{operation}</span>{index !== 4 && <ChevronRight size={12} />}</div>)}</div>
    <div className="target-matrix" aria-label={`Aggregate target states at recorded round ${round.round}`}>{tiles.map((tone, index) => <motion.div layout key={index} className={`target-tile ${tone}`} animate={{ backgroundColor: { mint: '#173b30', blue: '#1d3049', amber: '#382e1d', red: '#3b2430', neutral: '#1b2732' }[tone] }} transition={{ duration: .5 }}><span className="tile-state-mark">{tone === 'mint' ? <Check size={15} /> : tone === 'red' ? <ShieldAlert size={15} /> : tone === 'blue' ? <Activity size={15} /> : tone === 'amber' ? <Target size={15} /> : <span className="status-dot" />}</span></motion.div>)}</div>
    <div className="matrix-caption"><span>1 tile = 1 target · aggregate counts, not identities</span><span>{round.action === 'INITIALIZATION' ? 'Uniform initial pressure' : `${round.active_targets} targets under active pressure`}</span></div>
    <div className="state-counts">{stateMeta.map(state => <div className={`state-count ${state.tone}`} key={state.key}><state.icon size={17} /><strong>{round[state.key] ?? '—'}</strong><span>{state.name}<small>{state.detail}</small></span></div>)}</div>
    <div className={`retain-guard ${round.retain_safe === false ? 'at-risk' : ''}`}><div className="guard-icon">{round.retain_safe === false ? <ShieldAlert size={23} /> : <ShieldCheck size={23} />}</div><div><strong>{round.retain_safe === false ? 'Safety stop · retain utility at risk' : round.retain_safe ? 'Retain check passed' : 'Retain baseline recorded'}</strong><span>{round.retain_safe === false ? 'Controller stopped further training.' : 'Unrelated knowledge is checked alongside target pressure.'}</span></div><div className="guard-reading"><strong>{round.retain_drift.toFixed(4)}</strong><span>drift · limit {config.retain_max_drop.toFixed(2)}</span></div></div>
    {finalTargets && <><button className="text-button final-target-toggle" aria-expanded={showTargets} onClick={() => setShowTargets(!showTargets)}>{showTargets ? 'Hide individual target states' : 'Inspect final individual target states'}<ChevronRight size={15} /></button>{showTargets && <div className="final-targets"><label className="input-label" htmlFor="target-state-filter">Final target state</label><select id="target-state-filter" className="select-input" value={stateFilter} onChange={e => setStateFilter(e.target.value)}>{['ALL', 'SUPPRESSED', 'UNLEARNING', 'STUBBORN', 'LEAKING'].map(state => <option key={state} value={state}>{state === 'ALL' ? 'All 40 targets' : state}</option>)}</select><div className="target-state-list">{targets.map(target => <article className="final-target" key={target.question}><VerdictBadge verdict={target.state} /><p>{target.question}</p><small>Pressure weight {target.weight} · current log probability {target.current_log_prob.toFixed(3)}</small></article>)}</div></div>}</>}
  </div>;
}

export function LiveActivityFeed({ records }: { records: { title: string; detail: string; tone?: string }[] }) {
  return <aside className="activity-panel"><div className="panel-heading"><Activity size={16} /><span>Activity</span><span className="live-indicator">RECORDED</span></div><div className="activity-feed" aria-live="polite">{records.length ? [...records].reverse().slice(0, 7).map((record, index) => <motion.div initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} key={`${record.title}-${index}`} className={`activity-item ${record.tone ?? ''}`}><span className="feed-dot" /><div><strong>{record.title}</strong><p>{record.detail}</p></div></motion.div>) : <div className="activity-empty"><ScanLine size={26} /><span>Evidence will appear here as you advance the demo.</span></div>}</div><div className="activity-source"><FileJson size={15} /><span>Source-backed playback<br /><small>UI pace ≠ model execution time</small></span></div></aside>;
}

export function ResearchDetailsDrawer({ bundle, section, onClose }: { bundle: Bundle; section: string; onClose: () => void }) {
  const [tab, setTab] = useState(section);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    dialog.current?.focus();
    const handle = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab') {
        const focusable = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, a, select, [tabindex="0"]') ?? []);
        const first = focusable[0]; const last = focusable.at(-1);
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) { event.preventDefault(); last?.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', handle); document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', handle); document.body.style.overflow = ''; previous?.focus(); };
  }, [onClose]);
  const raw = tab === 'trace' ? bundle.data.trace : tab === 'discovery' ? bundle.data.discovery : tab === 'audit' ? bundle.data.pipeline : bundle.data.evaluation;
  return <div className="drawer-backdrop" onClick={onClose}><motion.div initial={{ x: 60, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: .2 }} ref={dialog} className="research-drawer" role="dialog" aria-modal="true" aria-label="Research details" tabIndex={-1} onClick={e => e.stopPropagation()}><div className="drawer-header"><div><span className="eyebrow">Recorded research</span><h2>Behind the saved evidence</h2></div><button className="icon-button" aria-label="Close research details" onClick={onClose}><X size={20} /></button></div><div className="drawer-tabs">{[['scope', 'Run scope'], ['discovery', 'Discovery'], ['trace', 'ATU trace'], ['audit', 'Audit'], ['metrics', 'Metrics'], ['sources', 'Sources']].map(([key, title]) => <button className={tab === key ? 'active' : ''} key={key} onClick={() => setTab(key)}>{title}</button>)}</div><div className="drawer-content">
    {tab === 'scope' ? <div className="scope-notes"><h3>One console. Distinct saved records.</h3><p>This drawer describes historical experiments with fictional benchmark authors. In a recorded replay, selected facts change the presentation focus. Live experiments are available from the New experiment workspace.</p><div className="scope-row"><span>01</span><div><strong>Multi-author discovery</strong><p>27 candidate facts across four entities. The frozen report provides the exposure verdicts and response samples.</p></div></div><div className="scope-row"><span>02</span><div><strong>Canonical ATU v2 training trace</strong><p>A historical 40-question training run. Six exported records include two evaluations at round 4. Per-target identities are exported only for the final state. Colored tiles show aggregate counts, not tracked fact identities.</p></div></div><div className="scope-row"><span>03</span><div><strong>Raw adversarial response collection</strong><p>Basil has 37, Nikolai 25, and the retain control 21 saved attacks. Published calibrated labels are shown where available. Missing labels remain unavailable.</p></div></div><div className="scope-row"><span>04</span><div><strong>Later orchestrated audit</strong><p>A separate 25-attack-per-author cohort reused the canonical checkpoint and skipped active training. Its summary is shown separately; per-probe responses were not exported for that cohort.</p></div></div><div className="notice warning"><ShieldAlert size={18} /><p>These records belong to the historical V2 experiment. Current V3 live results appear in their own run view. Job completion and refusal alone do not establish complete forgetting or full retain preservation.</p></div></div> : tab === 'sources' ? <div className="sources-list"><h3>16 genuine source artifacts</h3><p>Packaged as exact byte copies. Hashes are checked against the original files by the frontend verification script.</p>{Object.entries(bundle.sources).map(([key, source]) => <article key={key}><strong>{key}</strong><p>{source.source}</p><code>{source.sha256}</code><a className="text-button" href={`./${source.local}`} target="_blank" rel="noreferrer">Open original artifact<ExternalLink size={14} /></a></article>)}</div> : <><div className="raw-toolbar"><span>Read-only backend export</span><button className="button subtle small" onClick={() => downloadJson(raw, `ske-llm-${tab}.json`)}><Download size={14} />Download JSON</button></div><pre>{JSON.stringify(raw, null, 2)}</pre></>}
  </div></motion.div></div>;
}
