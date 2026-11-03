import { lazy, Suspense, useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ArrowRight, ArrowUpRight, Play, Pause, SkipForward, RotateCcw, FlaskConical, History, PanelRightOpen, ShieldCheck, ShieldAlert, Search, BrainCircuit, Swords, Check, Layers, FileCheck2, MousePointer2, ChevronRight, CircleHelp, Download, Database, Activity, Menu, Zap } from 'lucide-react';
import { loadBundle, fetchCatalog, recordedCatalog, entityFacts, attacksFor, label, downloadJson } from './services/research';
import type { Entity, Fact, PairedAttack, TofuCatalog, LiveJobStatus, LiveHyperparameters } from './types';
import { initialWorkflow, workflowReducer } from './workflow';
import { EntitySelector, CustomEntityBuilder, DatasetAuthorPanel } from './components/TargetPicker';
import { FactExposureCard, VerdictBadge, RedTeamAttackCard, BeforeAfterComparison, DiscoveryEvidencePanel } from './components/Evidence';
import { PipelineStepper, AdaptiveLoopVisualizer, LiveActivityFeed, ResearchDetailsDrawer } from './components/Console';
import { LiveExecutionModal } from './components/LiveExecutionModal';
import { triggerLiveUnlearning, fetchPipelineStatus, PipelineError, cancelPipeline, fetchJobHistory } from './services/pipeline';
import { StudioHome, LiveWorkspace, StudioHistory } from './components/StudioWorkspace';
import { defaultConfig } from './components/ExperimentControls';
import type { ExperimentConfig } from './components/ExperimentControls';
const RunComparison = lazy(() => import('./components/RunComparison').then(module => ({ default: module.RunComparison })));
import { LiveResults } from './components/LiveResults';
const PresentationView = lazy(() => import('./components/PresentationView').then(module => ({ default: module.PresentationView })));
const PresentationDemos = lazy(() => import('./components/PresentationDemos').then(module => ({ default: module.PresentationDemos })));
import { useLiveJob } from './hooks/useLiveJob';
import { useWorkspaceNavigation } from './hooks/useWorkspaceNavigation';
import { parseCollection } from './services/demos';
import { loadSavedRuns, mergeRun, readActiveJob, rememberActiveJob, saveRun, sortRuns } from './services/jobs';
import type { ActiveJob } from './services/jobs';
import { LayoutDashboard, Sun, Moon, X, Loader2 } from 'lucide-react';

const stageCopy = {
  discover: ['01 / MEMORY DISCOVERY', 'Find what the model remembers.', 'Recorded probes reveal which candidate facts can be recovered.'],
  select: ['02 / EVIDENCE FOCUS', 'Focus the recorded evidence.', 'Select exposed facts to inspect within the saved experiment.'],
  unlearn: ['03 / ADAPTIVE TARGETED UNLEARNING', 'Every target. Different pressure.', 'Replay how ATU adapts and checks unrelated knowledge.'],
  attack: ['04 / ADVERSARIAL VERIFICATION', 'Try to recover what was forgotten.', 'Recorded attacks test the final checkpoint from different angles.'],
  verify: ['05 / FINAL VERIFICATION', 'The evidence, side by side.', 'Same question. Two model states. A separate check on retained knowledge.'],
};

export default function App() {
  const bundle = useMemo(() => loadBundle(), []);
  const [entities, setEntities] = useState<Entity[]>(() => recordedCatalog(bundle));
  const [connected, setConnected] = useState<boolean | null>(null);
  const [catalog, setCatalog] = useState<TofuCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const { route, detail: routeDetail, navigate: setRoute } = useWorkspaceNavigation();
  const [workflow, dispatch] = useReducer(workflowReducer, undefined, () => initialWorkflow());
  const [custom, setCustom] = useState(false);
  const [research, setResearch] = useState<string | null>(null);
  const [speed, setSpeed] = useState(1);
  const [attackFilter, setAttackFilter] = useState('All');
  const [attackLimit, setAttackLimit] = useState(8);
  const [comparisonId, setComparisonId] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeJob, setActiveJob] = useState<ActiveJob | null>(() => readActiveJob());
  const [monitorOpen, setMonitorOpen] = useState(() => window.location.hash === '' && Boolean(readActiveJob()));
  const [savedRuns, setSavedRuns] = useState<LiveJobStatus[]>([]);
  const [selectedRun, setSelectedRun] = useState<LiveJobStatus | null>(null);
  const [resultLoadError, setResultLoadError] = useState('');
  const [resultFromDemos, setResultFromDemos] = useState(false);
  const [presentationJob, setPresentationJob] = useState<LiveJobStatus | null>(null);
  const [historyRevision, setHistoryRevision] = useState(0);
  const closePresentation = useCallback(() => setPresentationJob(null), []);
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [labAuthorId, setLabAuthorId] = useState(() => route === 'lab' ? routeDetail ?? '' : '');
  const [experimentConfig, setExperimentConfig] = useState<ExperimentConfig>({ ...defaultConfig });
  const [catalogRevision, setCatalogRevision] = useState(0);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => { try { return localStorage.getItem('atu-studio-theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } });
  const launchLock = useRef(false);
  const { job: monitoredJob, error: monitorError, reconnect } = useLiveJob(activeJob?.jobId);
  const busy = launching || Boolean(activeJob && (!monitoredJob || ['RUNNING', 'CANCELLING'].includes(monitoredJob.status)));
  const closeMonitor = useCallback(() => setMonitorOpen(false), []);
  const dismissMonitor = useCallback(() => { setMonitorOpen(false); setActiveJob(null); rememberActiveJob(null); }, []);
  const openLab = (authorId = '') => { setLabAuthorId(authorId); setRoute('lab', authorId); dispatch({ type: 'PLAY', value: false }); };
  const openHistory = () => { setRoute('history'); setHistoryRevision(value => value + 1); dispatch({ type: 'PLAY', value: false }); };
  const featuredRun = savedRuns.find(job => job.status === 'COMPLETED' && job.result && job.mode === 'full' && !job.result.scoring_recheck) ?? savedRuns.find(job => job.status === 'COMPLETED' && job.result);
  const presentable = route === 'showcase' ? null : route === 'result' ? selectedRun : featuredRun;
  const openDemos = () => { setRoute('showcase'); setMobileOpen(false); setMonitorOpen(false); dispatch({ type: 'PLAY', value: false }); };
  useEffect(() => {
    if (route === 'lab') setLabAuthorId(routeDetail ?? '');
    if (route === 'demo' && routeDetail && workflow.entityId !== routeDetail && recordedCatalog(bundle).some(entity => entity.id === routeDetail)) {
      dispatch({ type: 'ENTITY', id: routeDetail });
    }
  }, [route, routeDetail, bundle, workflow.entityId]);
  useEffect(() => {
    if (route !== 'result' || !routeDetail || selectedRun?.job_id === routeDetail) return;
    const saved = savedRuns.find(job => job.job_id === routeDetail);
    setSelectedRun(saved ?? null); setResultLoadError('');
    if (saved) return;
    // Packaged demos remain reopenable when the live backend is unavailable.
    const controller = new AbortController();
    void fetch('./artifacts/presentation_demos.json', { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]) })
      .then(response => { if (!response.ok) throw new Error('Saved evidence is unavailable.'); return response.json(); })
      .then(value => {
        if (controller.signal.aborted) return;
        const packaged = parseCollection(value).cases.find(item => item.job_id === routeDetail)?.job;
        if (packaged) { setSelectedRun(packaged); setResultFromDemos(true); }
        else setResultLoadError('This run is not available in saved history or the presentation collection.');
      }).catch(() => { if (!controller.signal.aborted) setResultLoadError('This run could not be reopened. Refresh the backend connection or choose another saved run.'); });
    return () => controller.abort();
  }, [route, routeDetail, savedRuns, selectedRun?.job_id]);
  const openResult = (job: LiveJobStatus) => { setResultFromDemos(route === 'showcase'); setSelectedRun(job); setResultLoadError(''); setRoute('result', job.job_id); dispatch({ type: 'PLAY', value: false }); };
  useEffect(() => { try { localStorage.setItem('atu-studio-theme', theme); } catch { /* Theme works without persistence. */ } }, [theme]);
  useEffect(() => { let cancelled = false; void loadSavedRuns().then(runs => { if (!cancelled) setSavedRuns(current => sortRuns([...current, ...runs.filter(run => !current.some(existing => existing.job_id === run.job_id))])); }).catch(() => { if (!cancelled) setStorageError(true); }); return () => { cancelled = true; }; }, []);
  useEffect(() => {
    if (!monitoredJob || ['RUNNING', 'CANCELLING'].includes(monitoredJob.status)) return;
    setSavedRuns(current => mergeRun(current, monitoredJob));
    void saveRun(monitoredJob).catch(() => setStorageError(true));
  }, [monitoredJob]);
  useEffect(() => { let ignore = false; void fetchJobHistory().then(jobs => { if (ignore) return; const finished = jobs.filter(job => !['RUNNING', 'CANCELLING'].includes(job.status)); setSavedRuns(current => sortRuns([...current.filter(job => !finished.some(saved => saved.job_id === job.job_id)), ...finished])); for (const job of finished) void saveRun(job).catch(() => setStorageError(true)); const active = jobs.find(job => ['RUNNING', 'CANCELLING'].includes(job.status)); if (active) setActiveJob(current => { if (current?.jobId === active.job_id) return current; const recovered = { jobId: active.job_id, authorId: active.author_id, authorName: active.author_name, mode: active.mode, startedAt: (active.start_time || Date.now()/1000) * 1000 }; rememberActiveJob(recovered); return recovered; }); }).catch(() => { /* Cached evidence remains available while the backend reconnects. */ }); return () => { ignore = true; }; }, [catalogRevision, historyRevision]);
  const stopActive = async () => { if (!activeJob) return; await cancelPipeline(activeJob.jobId); reconnect(); };
  const closeResearch = useCallback(() => setResearch(null), []);
  useEffect(() => {
    if (!mobileOpen) return;
    document.querySelector<HTMLElement>('#mobile-nav button')?.focus();
    const closeOutside = (event: PointerEvent) => {
      if (!(event.target instanceof Element) || !event.target.closest('.mobile-navigation')) setMobileOpen(false);
    };
    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpen(false);
        document.querySelector<HTMLElement>('[aria-controls="mobile-nav"]')?.focus();
      }
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeWithEscape);
    return () => { document.removeEventListener('pointerdown', closeOutside); document.removeEventListener('keydown', closeWithEscape); };
  }, [mobileOpen]);
  const entity = entities.find(e => e.id === workflow.entityId) ?? entities[0];
  const facts = useMemo(() => entityFacts(bundle, entity), [bundle, entity]);
  const selected = useMemo(() => facts.filter(f => workflow.selected.includes(f.fact_id)), [facts, workflow.selected]);
  const attacks = useMemo(() => attacksFor(bundle, entity.id, selected), [bundle, entity.id, selected]);
  const rounds = bundle.data.trace.decision_trace;
  const discoveryDone = workflow.discoveryCount >= facts.length && facts.length > 0;
  const atuDone = workflow.roundIndex === rounds.length - 1;
  const attackDone = workflow.attackCount >= attacks.length && attacks.length > 0;
  const currentRound = rounds[Math.max(workflow.roundIndex, 0)];
  const visibleFacts = facts.slice(0, workflow.stage === 'discover' ? workflow.discoveryCount : facts.length);
  const visibleAttacks = attacks.slice(0, workflow.attackCount);
  const comparison = attacks.find(a => a.after.probe_id === comparisonId) ?? attacks.find(a => a.before && selected.some(f => a.after.target_facts.includes(f.target_value))) ?? attacks.find(a => a.before && a.calibration && a.calibration !== 'INCONCLUSIVE') ?? attacks[0];
  const audit = useMemo(() => {
    return Object.values(bundle.data.pipeline.redteam_summary.per_author).find(a => {
      const key = entity.id === 'basil' ? 'basil_mahfouz' : entity.id === 'nikolai' ? 'nikolai_abilov' : entity.id === 'jaime' ? 'jaime_vasquez_control' : '';
      return bundle.data.pipeline.redteam_summary.per_author[key] === a;
    });
  }, [bundle, entity.id]);

  const handleLaunchLive = async (authorId: string, mode: 'fast' | 'full' = 'fast', hyperparameters?: LiveHyperparameters) => {
    if (launchLock.current || busy) { if (activeJob) setMonitorOpen(true); return; }
    launchLock.current = true; setLaunching(true); setLaunchError(null);
    try {
      const { jobId, authorName, authorId: actualAuthorId } = await triggerLiveUnlearning(authorId, mode, hyperparameters);
      const active = { jobId, authorId: actualAuthorId || authorId, authorName, mode, startedAt: Date.now() };
      rememberActiveJob(active); setActiveJob(active); setMonitorOpen(true);
    } catch (err) {
      if (err instanceof PipelineError && err.jobId) {
        try {
          const existing = await fetchPipelineStatus(err.jobId);
          const active = { jobId: existing.job_id, authorId: existing.author_id, authorName: existing.author_name, mode: existing.mode, startedAt: Date.now() };
          rememberActiveJob(active); setActiveJob(active); setMonitorOpen(true);
        } catch (failure) { setLaunchError((failure as Error).message); }
      } else setLaunchError((err as Error).name === 'TimeoutError' ? 'The launch response timed out. Retry to reconnect to any job already started.' : (err as Error).message);
    } finally { launchLock.current = false; setLaunching(false); }
  };
  const handleLiveComplete = (status: LiveJobStatus) => {
    if (!status.result) return;
    setSavedRuns(current => mergeRun(current, status));
    openResult(status); dismissMonitor();
  };

  useEffect(() => { let cancelled = false; setConnected(null); void fetchCatalog(bundle).then(result => { if (!cancelled) { setEntities(result.entities); setConnected(result.connected); setCatalog(result.catalog); setCatalogError(result.catalogError); } }); return () => { cancelled = true; }; }, [bundle, catalogRevision]);
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }); }, [route, workflow.stage]);
  useEffect(() => { if (research) dispatch({ type: 'PLAY', value: false }); }, [research]);
  useEffect(() => {
    if (!workflow.playing || route !== 'demo') return;
    const advance = () => {
      if (workflow.stage === 'discover') dispatch({ type: 'DISCOVERY', count: Math.min(facts.length, workflow.discoveryCount + 1) });
      if (workflow.stage === 'unlearn') dispatch({ type: 'ROUND', index: Math.min(rounds.length - 1, workflow.roundIndex + 1) });
      if (workflow.stage === 'attack') dispatch({ type: 'ATTACK', count: Math.min(attacks.length, workflow.attackCount + 1) });
    };
    if ((workflow.stage === 'discover' && discoveryDone) || (workflow.stage === 'unlearn' && atuDone) || (workflow.stage === 'attack' && attackDone)) { dispatch({ type: 'PLAY', value: false }); return; }
    const timer = setTimeout(advance, (workflow.stage === 'unlearn' ? 2500 : workflow.stage === 'attack' ? 1600 : 900) / speed);
    return () => clearTimeout(timer);
  }, [workflow, route, facts.length, rounds.length, attacks.length, speed, discoveryDone, atuDone, attackDone]);

  const start = (id = 'basil', autoplay = false) => {
    dispatch({ type: 'ENTITY', id }); setCustom(false); setComparisonId(''); setAttackFilter('All'); setAttackLimit(8); setRoute('demo', id);
    if (autoplay) dispatch({ type: 'PLAY', value: true });
  };
  const changeEntity = (next: Entity) => { if (next.role === 'DATASET_AUTHOR') { openLab(next.id); return; } dispatch({ type: 'ENTITY', id: next.id }); setComparisonId(''); setAttackFilter('All'); setAttackLimit(8); };
  const goSelect = () => { dispatch({ type: 'ADVANCE', stage: 'select' }); };
  const goUnlearn = () => { dispatch({ type: 'ADVANCE', stage: 'unlearn' }); dispatch({ type: 'ROUND', index: 0 }); dispatch({ type: 'PLAY', value: true }); };
  const goAttack = () => { dispatch({ type: 'ADVANCE', stage: 'attack' }); dispatch({ type: 'ATTACK', count: 1 }); dispatch({ type: 'PLAY', value: true }); };
  const nextRecord = () => {
    dispatch({ type: 'PLAY', value: false });
    if (workflow.stage === 'discover') dispatch({ type: 'DISCOVERY', count: Math.min(facts.length, workflow.discoveryCount + 1) });
    if (workflow.stage === 'unlearn') dispatch({ type: 'ROUND', index: Math.min(rounds.length - 1, workflow.roundIndex + 1) });
    if (workflow.stage === 'attack') dispatch({ type: 'ATTACK', count: Math.min(attacks.length, workflow.attackCount + 1) });
  };
  const finishReplay = () => {
    dispatch({ type: 'PLAY', value: false });
    if (workflow.stage === 'discover') dispatch({ type: 'DISCOVERY', count: facts.length });
    if (workflow.stage === 'unlearn') dispatch({ type: 'ROUND', index: rounds.length - 1 });
    if (workflow.stage === 'attack') dispatch({ type: 'ATTACK', count: attacks.length });
  };
  const activity = useMemo(() => {
    if (workflow.stage === 'discover' || workflow.stage === 'select') return visibleFacts.map(f => ({ title: `${label(f.attribute_key)} · ${{ CONFIRMED_LEAK: 'exposed', PARTIAL_LEAK: 'partial exposure', NOT_EXPOSED: 'not exposed', UNCERTAIN: 'uncertain' }[f.verdict]}`, detail: `${f.probes_leaked} of ${f.probes_tested} probes recovered ${f.target_value}.`, tone: f.probes_leaked ? 'red' : 'neutral' }));
    if (workflow.stage === 'unlearn') return rounds.slice(0, workflow.roundIndex + 1).map(r => ({ title: r.should_stop ? 'Controller safety stop' : r.action === 'INITIALIZATION' ? '40 targets initialized' : `Round ${r.round} · pressure adapted`, detail: r.should_stop ? 'Retain drift exceeded the saved guardrail.' : r.decision, tone: r.should_stop ? 'amber' : 'mint' }));
    if (workflow.stage === 'attack') return visibleAttacks.map(a => ({ title: `${a.after.probe_id} · ${label(a.after.verdict)}`, detail: a.calibration ? label(a.calibration) : 'Raw result · calibrated label not exported.', tone: a.calibration === 'RESIDUAL_LEAKAGE' ? 'red' : a.calibration === 'VERIFIED_SUPPRESSION' ? 'mint' : 'neutral' }));
    return [{ title: 'Canonical checkpoint loaded', detail: bundle.data.evaluation.checkpoint_hash, tone: 'mint' }, { title: 'Evidence paired', detail: 'Before and after use the identical exported prompt.', tone: 'mint' }, { title: 'Audit kept separate', detail: 'Later orchestrated audit reused the saved checkpoint.', tone: 'neutral' }];
  }, [workflow.stage, workflow.discoveryCount, workflow.roundIndex, workflow.attackCount, entity.id]);
  const statusText = entity.role === 'DATASET_AUTHOR' ? 'Dataset author selected · model testing pending' : workflow.stage === 'discover' ? discoveryDone ? 'Discovery evidence loaded' : workflow.playing ? 'Replaying recorded discovery evidence…' : 'Ready to inspect model memory' : workflow.stage === 'select' ? `${selected.length} exposed fact${selected.length === 1 ? '' : 's'} selected` : workflow.stage === 'unlearn' ? atuDone ? 'ATU stopped on retain safety' : workflow.playing ? `Replaying adaptive round ${currentRound.round}` : 'Adaptive replay paused' : workflow.stage === 'attack' ? attackDone ? 'Adversarial replay complete' : workflow.playing ? 'Revealing saved attack responses…' : 'Attack replay paused' : 'Final audit loaded';
  const filteredAttacks = visibleAttacks.filter(a => attackFilter === 'All' || attackFilter === 'Leaks' && ['FULL_RECOVERY', 'PARTIAL_RECOVERY'].includes(a.after.verdict) || attackFilter === 'Suppressed' && a.calibration === 'VERIFIED_SUPPRESSION' || attackFilter === 'Inconclusive' && a.calibration === 'INCONCLUSIVE' || attackFilter === 'Uncalibrated' && !a.calibration);
  const activeReplay = ['discover', 'unlearn', 'attack'].includes(workflow.stage);
  const done = workflow.stage === 'discover' ? discoveryDone : workflow.stage === 'unlearn' ? atuDone : attackDone;

  const navigate = (next: 'launch' | 'lab' | 'history') => { if (next === 'lab') openLab(); else if (next === 'history') openHistory(); else setRoute(next); setMobileOpen(false); dispatch({ type: 'PLAY', value: false }); };
  const routeName = route === 'showcase' ? 'Presentation demos' : route === 'launch' ? 'Overview' : route === 'lab' ? 'New experiment' : route === 'demo' ? 'Recorded experiment' : route === 'result' ? 'Live results' : route === 'compare' ? 'Compare runs' : 'Run history';
  return <div className="app-shell studio" data-theme={theme}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar"><button className="brand" aria-label="ATU Studio home" onClick={() => navigate('launch')}><div className="brand-symbol"><Layers size={23} /></div><span>ATU Studio<small>UNLEARNING RESEARCH</small></span></button><span className="sidebar-label">WORKSPACE</span><nav className="main-nav" aria-label="Main navigation">
      <button aria-label="Overview" title="Overview" aria-current={route === 'launch' ? 'page' : undefined} className={route === 'launch' ? 'active' : ''} onClick={() => navigate('launch')}><LayoutDashboard size={18} /><span>Overview</span></button>
      <button aria-label="New experiment V3" title="New experiment" aria-current={route === 'lab' ? 'page' : undefined} className={route === 'lab' ? 'active' : ''} onClick={() => navigate('lab')}><FlaskConical size={18} /><span>New experiment</span><span className="nav-shortcut">V3</span></button>
      <button aria-label="Run history" title="Run history" aria-current={['history', 'result', 'demo', 'compare'].includes(route) ? 'page' : undefined} className={['history', 'result', 'demo', 'compare'].includes(route) ? 'active' : ''} onClick={() => navigate('history')}><History size={18} /><span>Run history</span></button>
      <span className="nav-section-label">PRESENT &amp; REVIEW</span>
      <button aria-label="Presentation demos" title="Presentation demos" aria-current={route === 'showcase' ? 'page' : undefined} className={route === 'showcase' ? 'active' : ''} onClick={openDemos}><Play size={18} /><span>Presentation demos</span><span className="nav-shortcut">3</span></button>
      <a className="nav-report-link" aria-label="Method comparison" title="Method comparison" href="./artifacts/feedback-validation/index.html"><FileCheck2 size={18} /><span>Method comparison</span><ArrowUpRight size={13} /></a>
      <button aria-label="Research details" title="Research details" onClick={() => setResearch('scope')}><PanelRightOpen size={18} /><span>Research details</span><ArrowUpRight size={13} /></button>
    </nav><div className="sidebar-bottom"><div className="model-card"><span className="eyebrow">MODEL ENVIRONMENT</span><strong>Qwen 2.5 <span>1.5B</span></strong><span>TOFU fine-tuned · LoRA adapters</span><div><ShieldCheck size={14} />Original model preserved</div></div><span className="sidebar-version">ATU V3 · LOCAL RESEARCH</span></div></aside>
    <div className="main-shell"><header className="topbar"><div className="mobile-navigation"><button className="icon-button" aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="mobile-nav" onClick={() => setMobileOpen(!mobileOpen)}><Menu size={19} /></button>{mobileOpen && <nav id="mobile-nav" aria-label="Mobile navigation"><button onClick={openDemos}><Play size={16} />Presentation demos</button><button onClick={() => navigate('launch')}><LayoutDashboard size={16} />Overview</button><button onClick={() => navigate('lab')}><FlaskConical size={16} />New experiment</button><button onClick={() => navigate('history')}><History size={16} />Run history</button><button onClick={() => { setResearch('scope'); setMobileOpen(false); }}><PanelRightOpen size={16} />Research details</button></nav>}</div><div className="breadcrumb"><span>Workspace</span><ChevronRight size={13} /><strong>{routeName}</strong></div><div className="topbar-actions"><button className="demo-access" aria-label="Open demo collection" title="Open demo collection" onClick={openDemos}><Play size={14} /><span>Demo collection</span></button><button className={'connection-status ' + (connected ? 'online' : '')} title="Refresh backend connection" onClick={() => setCatalogRevision(value => value + 1)}><span className="status-dot" />{connected === null ? 'Connecting' : connected ? 'Server online' : 'Server offline'}</button>{presentable?.result && <button className="present-toggle" aria-label="Present evidence" title="Present saved evidence" onClick={() => setPresentationJob(presentable)}><Play size={14} /><span>Present evidence</span></button>}{activeJob && <button className="monitor-toggle" onClick={() => setMonitorOpen(true)}><Activity size={15} />{monitoredJob?.status === 'COMPLETED' ? 'Results ready' : monitoredJob?.status === 'FAILED' ? 'Run failed' : monitoredJob?.status === 'CANCELLED' ? 'Run stopped' : monitoredJob?.status === 'CANCELLING' ? 'Stopping' : 'View live run'}</button>}<button className="icon-button" aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>{theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}</button><button className="icon-button help-button" aria-label="About this workspace" onClick={() => setResearch('scope')}><CircleHelp size={19} /></button></div></header>
      <main id="main-content" tabIndex={-1}>
        {launchError && <div className="studio-global-notice red" role="alert"><ShieldAlert size={19} /><div><strong>Could not start the experiment</strong><p>{launchError}</p></div><button className="icon-button" aria-label="Dismiss launch error" onClick={() => setLaunchError(null)}><X size={17} /></button></div>}
        {storageError && <div className="studio-global-notice amber" role="status"><Database size={18} /><p>Browser storage is unavailable. Export your results to keep a copy.</p><button className="icon-button" aria-label="Dismiss storage notice" onClick={() => setStorageError(false)}><X size={17} /></button></div>}
        {catalogError && route !== 'demo' && <div className="studio-global-notice amber" role="status"><Database size={18} /><p>{catalogError}</p><button className="text-button" onClick={() => setCatalogRevision(value => value + 1)}>Retry</button></div>}
        {launching && <div className="studio-global-notice" role="status"><Loader2 size={17} className="spin" /><p>Starting your experiment…</p></div>}
        {activeJob && !monitorOpen && (!monitoredJob || ['RUNNING', 'CANCELLING'].includes(monitoredJob.status)) && <div className="active-run-banner"><Activity size={20} /><div><strong>{activeJob.authorName}</strong><span>{monitorError ? 'Connection interrupted. Monitoring will reconnect.' : monitoredJob?.current_step || 'Connecting to the experiment…'}</span></div><button className="button secondary small" onClick={() => setMonitorOpen(true)}>Open monitor<ArrowRight size={14} /></button></div>}

        {route === 'showcase' && <Suspense fallback={<div className="studio-page" role="status">Opening presentation demos…</div>}><PresentationDemos onPresent={setPresentationJob} onOpen={openResult} /></Suspense>}
        {route === 'launch' && <StudioHome catalog={catalog} bundle={bundle} runs={savedRuns} featured={featuredRun} onPresent={setPresentationJob} onLab={() => openLab()} onReplay={id => start(id)} onHistory={openHistory} onResult={openResult} onDemos={openDemos} />}
        {route === 'lab' && <LiveWorkspace key={labAuthorId || 'catalog'} initialAuthorId={labAuthorId} entities={entities} catalog={catalog} connected={connected} busy={busy} onLaunch={handleLaunchLive} onReplay={() => start()} experimentConfig={experimentConfig} onConfigChange={setExperimentConfig} />}
        {route === 'history' && <StudioHistory runs={savedRuns} bundle={bundle} onOpen={openResult} onReplay={id => start(id)} onLab={() => openLab()} onCompare={() => setRoute('compare')} />}
        {route === 'compare' && <Suspense fallback={<div className="studio-page" role="status">Opening saved comparison…</div>}><RunComparison runs={savedRuns} onBack={openHistory} /></Suspense>}
        {route === 'result' && selectedRun && selectedRun.job_id === routeDetail && <LiveResults key={selectedRun.job_id} job={selectedRun} onBack={resultFromDemos ? openDemos : openHistory} backLabel={resultFromDemos ? 'Presentation demos' : 'Run history'} onNew={() => openLab(selectedRun.author_id)} onFull={() => { setExperimentConfig(current => ({ ...current, mode: 'full' })); openLab(selectedRun.author_id); }} />}
        {route === 'result' && (!selectedRun || selectedRun.job_id !== routeDetail) && <div className="studio-page"><section className="studio-card studio-empty" role={resultLoadError ? 'alert' : 'status'}><FileCheck2 size={28} /><h2>{resultLoadError ? 'Saved run unavailable' : 'Reopening saved evidence…'}</h2><p>{resultLoadError || 'Loading the original result from your saved history.'}</p>{resultLoadError && <button className="button secondary" onClick={openHistory}>Open run history<ArrowRight size={15} /></button>}</section></div>}
        {route === 'demo' && <div className="demo-page recorded-workspace"><PipelineStepper stage={workflow.stage} reached={workflow.reached} onNavigate={stage => dispatch({ type: 'NAVIGATE', stage })} /><div className="demo-context"><div><span className="status-dot mint-dot" /><span>{statusText}</span></div><div><span className="mono">Historical ATU v2 · seed 42</span><button className="text-button" onClick={() => setResearch('scope')}>Run scope<ArrowUpRight size={13} /></button></div></div><div className="page-heading demo-heading"><span className="eyebrow">{stageCopy[workflow.stage][0]}</span><h1>{stageCopy[workflow.stage][1]}</h1><p>{stageCopy[workflow.stage][2]}</p></div>
          <div className={`workspace-grid ${workflow.stage === 'verify' || entity.role === 'DATASET_AUTHOR' ? 'verification-layout' : ''}`}><section className="stage-workspace">
            {(workflow.stage === 'discover' || workflow.stage === 'select') && <><div className="target-bar"><div className="target-bar-left"><span className="input-label">Research target</span>{!custom && <EntitySelector entities={entities} entity={entity} onChange={changeEntity} loading={connected === null} />}</div>{workflow.stage === 'discover' && <div className="target-bar-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>{entity.role !== 'NEGATIVE_CONTROL' && entity.role !== 'DATASET_AUTHOR' && <button className="button subtle small" title="Run live GPU unlearning on this author" disabled={busy || !connected} onClick={() => handleLaunchLive(entity.dataset?.id || entity.id, 'fast')}><Zap size={14} className="mint-text" />Run on GPU</button>}<button className={`button ${custom ? 'secondary' : 'subtle'} small`} onClick={() => { setCustom(!custom); dispatch({ type: 'PLAY', value: false }); }}>{custom ? 'Use dataset entity' : 'Use Custom Entity'}<ArrowUpRight size={14} /></button></div>}</div>
              {catalogError && <div className="notice warning" role="status"><Database size={17} /><p>{catalogError}</p></div>}
              {custom ? <CustomEntityBuilder onReplay={() => setCustom(false)} onLaunchLive={handleLaunchLive} launching={busy} connected={connected === true} /> : <>
                {entity.role === 'DATASET_AUTHOR' && catalog && entity.dataset ? <DatasetAuthorPanel key={entity.id} entity={entity} catalog={catalog} onReplay={() => start()} onLaunchLive={handleLaunchLive} launching={busy} connected={connected === true} experimentConfig={experimentConfig} onConfigChange={setExperimentConfig} /> : !workflow.discoveryCount && workflow.stage === 'discover' ? <div className="discovery-ready"><div className="ready-icon"><Search size={32} /></div><h2>Explore the model’s memory.</h2><p>{facts.length} candidate facts · real multi-style probe responses</p><div className="ready-preview">{facts.slice(0, 4).map(f => <span key={f.fact_id}>{label(f.attribute_key)}</span>)}</div><button className="button primary" disabled={!facts.length} onClick={() => dispatch({ type: 'PLAY', value: true })}><Search size={16} />Discover recorded exposure<ArrowRight size={16} /></button>{!facts.length && <p>No saved discovery evidence for this entity.</p>}<small>Replays saved model tests. No new inference is started.</small></div> : <>
                  <div className="results-heading"><div><strong>{workflow.stage === 'select' ? 'Select the evidence to focus on' : 'Discovery findings'}</strong><span>{visibleFacts.length} / {facts.length} recorded fact results</span></div>{workflow.stage === 'select' ? <span className="selected-count"><Check size={14} />{selected.length} selected</span> : discoveryDone && <span className="badge mint"><Check size={13} />Evidence loaded</span>}</div>
                  {workflow.stage === 'discover' && visibleFacts.length > 0 && !discoveryDone && <DiscoveryEvidencePanel fact={visibleFacts[visibleFacts.length - 1]} />}
                  <div className="fact-grid">{visibleFacts.map(fact => <FactExposureCard key={fact.fact_id} fact={fact} entity={entity} selected={workflow.selected.includes(fact.fact_id)} selectable={workflow.stage === 'select'} onSelect={() => dispatch({ type: 'SELECT', id: fact.fact_id })} />)}</div>
                  {workflow.stage === 'select' && <div className="selection-footnote"><ShieldCheck size={16} /><span>{entity.role === 'FORGET_TARGET' ? 'Only exposed or partially exposed facts can be selected. Your choices focus the saved replay.' : entity.role === 'RETAIN_CONTROL' ? 'This entity is a protected retain control. Its facts cannot be selected for forgetting.' : 'The saved probes found no exposure. There is no evidence-backed target to unlearn.'}</span></div>}
                </>}
              </>}
            </>}

            {workflow.stage === 'unlearn' && <><div className="focus-strip"><BrainCircuit size={19} /><div><strong>{entity.name}</strong><span>{selected.length} selected fact{selected.length === 1 ? '' : 's'} · presentation focus</span></div><button className="text-button" onClick={() => setResearch('scope')}>Historical 40-target run<ArrowUpRight size={14} /></button></div><AdaptiveLoopVisualizer round={currentRound} traceIndex={Math.max(workflow.roundIndex, 0)} total={rounds.length} config={bundle.data.trace.config} finalTargets={atuDone ? Object.values(bundle.data.trace.final_target_states) : undefined} /><div className="round-timeline" aria-label="Recorded adaptive rounds">{rounds.map((round, index) => <button key={index} className={workflow.roundIndex === index ? 'current' : index < workflow.roundIndex ? 'complete' : ''} aria-label={`Show trace record ${index + 1}, round ${round.round}`} onClick={() => { dispatch({ type: 'PLAY', value: false }); dispatch({ type: 'ROUND', index }); }}><span>{round.action === 'INITIALIZATION' ? 'Start' : `R${round.round}`}</span><small>{index === rounds.length - 1 ? 'Final check' : round.should_stop ? 'Safety stop' : index ? 'Adapt' : 'Baseline'}</small></button>)}</div><div className="dev-probes"><div className="results-heading"><div><strong>Verification probes</strong><span>{currentRound.probe_details ? `${currentRound.dev_probes_leaking} / ${currentRound.total_dev_probes} probes recovered target information` : 'No verification responses exported at initialization'}</span></div></div><div className="dev-probe-grid">{currentRound.probe_details?.map(probe => <details className={`dev-probe ${probe.leaked ? 'leaking' : ''}`} key={probe.probe_id}><summary><span className="mono">{probe.probe_id}</span><span>{probe.leaked ? 'Recovery detected' : 'No recovery'}</span><ChevronRight size={14} /></summary><p>{probe.prompt}</p><blockquote>{probe.gen_text}</blockquote></details>)}</div></div></>}

            {workflow.stage === 'attack' && <><div className="attack-summary"><div className="attack-summary-icon"><Swords size={24} /></div><div><strong>{entity.name}</strong><span>ATU checkpoint · adversarial response collection</span></div><div className="attack-counter"><strong>{workflow.attackCount}</strong><span>/ {attacks.length} records</span></div></div><div className="attack-stats"><div><span className="status-dot red-dot" /><strong>{visibleAttacks.filter(a => ['FULL_RECOVERY', 'PARTIAL_RECOVERY'].includes(a.after.verdict)).length}</strong><span>raw recoveries</span></div><div><span className="status-dot mint-dot" /><strong>{visibleAttacks.filter(a => a.calibration === 'VERIFIED_SUPPRESSION').length}</strong><span>published suppressions</span></div><div><span className="status-dot amber-dot" /><strong>{visibleAttacks.filter(a => a.calibration === 'INCONCLUSIVE').length}</strong><span>published inconclusive</span></div></div>
              <div className="filter-bar" aria-label="Attack filters">{['All', 'Leaks', 'Suppressed', 'Inconclusive', 'Uncalibrated'].map(filter => <button className={attackFilter === filter ? 'active' : ''} aria-pressed={attackFilter === filter} key={filter} onClick={() => { setAttackFilter(filter); setAttackLimit(8); }}>{filter}</button>)}</div><div className="attack-list">{(attackDone ? filteredAttacks.slice(0, attackLimit) : [...filteredAttacks].reverse().slice(0, 4)).map(pair => <RedTeamAttackCard key={pair.after.probe_id} pair={pair} active={!attackDone && pair.after.probe_id === visibleAttacks.at(-1)?.after.probe_id} />)}{!filteredAttacks.length && <div className="empty-state"><Swords size={25} /><h3>No matching saved attacks yet.</h3><p>Choose another filter or continue the replay.</p></div>}</div>{attackDone && filteredAttacks.length > attackLimit && <button className="button secondary load-more" onClick={() => setAttackLimit(limit => limit + 8)}>Show more attacks<ChevronRight size={15} /></button>}</>}

            {workflow.stage === 'verify' && <>{comparison && <><div className="comparison-selector"><div><span className="input-label">Evidence pair</span><select className="select-input" aria-label="Choose before and after question" value={comparison.after.probe_id} onChange={e => setComparisonId(e.target.value)}>{attacks.filter(a => a.before).map(a => <option key={a.after.probe_id} value={a.after.probe_id}>{a.after.probe_id} · {label(a.after.category)} · {a.after.target_facts.join(', ')}</option>)}</select></div><button className="button subtle small" onClick={() => setResearch('sources')}><FileCheck2 size={15} />Source artifacts</button></div><BeforeAfterComparison pair={comparison} /></>}
              <div className="verification-cards"><div className="verification-card"><div className="verification-card-heading"><Swords size={20} /><h3>Red-Team verification</h3></div><p>Alternative questions challenge the same final checkpoint.</p><div className="mini-stat-row"><div><strong className="mint-text">{attacks.filter(a => a.calibration === 'VERIFIED_SUPPRESSION').length}</strong><span>published suppression labels</span></div><div><strong className="red-text">{attacks.filter(a => a.calibration === 'RESIDUAL_LEAKAGE').length}</strong><span>published residual labels</span></div></div><small>These labels cover explicitly documented probes in the raw collection. Unlabeled probes remain uncalibrated.</small><button className="text-button" onClick={() => dispatch({ type: 'NAVIGATE', stage: 'attack' })}>View attack evidence<ArrowRight size={14} /></button></div><RetainUtilityCard before={bundle.data.targetEvaluation.sample_retain_pred} after={bundle.data.evaluation.sample_retain_pred} score={bundle.data.evaluation.retain_rougeL} auditRate={bundle.data.pipeline.redteam_summary.retain_utility_rate} /></div>
              <ExperimentSummary entity={entity} selected={selected} pair={comparison} audit={audit} checkpoint={bundle.data.evaluation.checkpoint_hash} stopReason={bundle.data.evaluation.stop_reason} onEvidence={() => setResearch('discovery')} onTrace={() => setResearch('trace')} onAudit={() => setResearch('audit')} />
            </>}
          </section>{workflow.stage !== 'verify' && entity.role !== 'DATASET_AUTHOR' && <LiveActivityFeed records={activity} />}</div>

          {!custom && entity.role !== 'DATASET_AUTHOR' && <div className="action-dock"><div className="dock-context"><span className="eyebrow">{workflow.stage === 'select' ? 'PRESENTATION FOCUS' : workflow.stage === 'verify' ? 'AUDIT COMPLETE' : 'RECORDED PLAYBACK'}</span><strong>{workflow.stage === 'select' ? selected.length ? selected.map(f => label(f.attribute_key)).join(' · ') : 'Choose an exposed fact to continue' : statusText}</strong></div><div className="dock-actions">{activeReplay && !done && (workflow.discoveryCount > 0 || workflow.stage !== 'discover' || workflow.playing) && <><label className="speed-select"><span className="sr-only">Replay speed</span><select aria-label="Replay speed" value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value={1}>1× pace</option><option value={2}>2× pace</option><option value={.5}>0.5× pace</option></select></label><button className="button secondary small" onClick={() => dispatch({ type: 'PLAY', value: !workflow.playing })}>{workflow.playing ? <Pause size={15} /> : <Play size={15} />}{workflow.playing ? 'Pause' : 'Resume'}</button><button className="icon-button" aria-label="Next saved record" onClick={nextRecord}><SkipForward size={17} /></button><button className="text-button" onClick={finishReplay}>Show saved result<ArrowRight size={14} /></button></>}
            {workflow.stage === 'discover' && discoveryDone && <button className="button primary" onClick={goSelect}>Select facts<MousePointer2 size={16} /></button>}
            {workflow.stage === 'select' && entity.role === 'FORGET_TARGET' && <button className="button primary" disabled={!selected.length} onClick={goUnlearn}><BrainCircuit size={16} />Inspect unlearning replay<ArrowRight size={16} /></button>}
            {workflow.stage === 'select' && entity.role !== 'FORGET_TARGET' && <button className="button primary" onClick={() => start()}>Choose a forget target<ArrowRight size={16} /></button>}
            {workflow.stage === 'unlearn' && atuDone && <button className="button primary" onClick={goAttack}><Swords size={16} />Inspect recovery tests<ArrowRight size={16} /></button>}
            {workflow.stage === 'attack' && attackDone && <button className="button primary" onClick={() => dispatch({ type: 'ADVANCE', stage: 'verify' })}>Before / After<ArrowRight size={16} /></button>}
            {workflow.stage === 'verify' && <><button className="button secondary" onClick={() => downloadJson({ presentation_focus: { entity: entity.name, selected_facts: selected.map(f => f.fact_id) }, execution: 'RECORDED_REPLAY_NO_NEW_TRAINING', checkpoint: bundle.data.evaluation.checkpoint_hash, canonical_stop: bundle.data.evaluation.stop_reason, displayed_probe: comparison, separate_orchestrated_audit: audit }, 'ske-llm-evidence-summary.json')}><Download size={16} />Export evidence</button><button className="button primary" onClick={() => start()}><RotateCcw size={16} />New demo</button></>}
          </div></div>}
        </div>}
      </main><footer className="app-footer"><span>ATU Studio<span>Machine unlearning research workspace</span></span><button className="text-button" onClick={() => setResearch('sources')}>Evidence provenance<ArrowUpRight size={12} /></button></footer>
    </div><AnimatePresence>{research && <ResearchDetailsDrawer key={research} bundle={bundle} section={research} onClose={closeResearch} />}</AnimatePresence>
    {presentationJob && <Suspense fallback={<div className="presentation-loading" role="status"><Loader2 size={24} className="spin" /><span>Opening saved evidence…</span></div>}><PresentationView job={presentationJob} onClose={closePresentation} onInspect={() => { openResult(presentationJob); closePresentation(); }} /></Suspense>}
    <AnimatePresence>{activeJob && monitorOpen && <LiveExecutionModal active={activeJob} job={monitoredJob} error={monitorError} onClose={closeMonitor} onComplete={handleLiveComplete} onReconnect={reconnect} onDismiss={dismissMonitor} onStop={stopActive} />}</AnimatePresence>
  </div>;
}

function RetainUtilityCard({ before, after, score, auditRate }: { before: string; after: string; score: number; auditRate: number }) {
  const [expanded, setExpanded] = useState(false);
  return <div className="verification-card"><div className="verification-card-heading"><ShieldCheck size={20} /><h3>Retained knowledge</h3></div><p>Jaime Vasquez · unrelated author control</p><div className="retain-metrics"><div><strong>{(score * 100).toFixed(1)}<small>%</small></strong><span>canonical response overlap</span></div><div><strong className="amber-text">{(auditRate * 100).toFixed(0)}<small>%</small></strong><span>later adversarial retain utility</span></div></div><small>High canonical overlap does not establish robust retention across adversarial questions.</small><button className="text-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? 'Hide retained response' : 'Inspect retained response'}<ChevronRight size={14} /></button>{expanded && <div className="retain-response"><span className="eyebrow">Before · canonical sample</span><p>{before}</p><span className="eyebrow">After · same exported sample</span><p>{after}</p></div>}</div>;
}

function ExperimentSummary({ entity, selected, pair, audit, checkpoint, stopReason, onEvidence, onTrace, onAudit }: { entity: Entity; selected: Fact[]; pair?: PairedAttack; audit?: { total_attacks: number; validated_attacks: number; verified_suppressions: number; residual_leaks: number; inconclusive_attacks: number }; checkpoint: string; stopReason: string; onEvidence: () => void; onTrace: () => void; onAudit: () => void }) {
  const residual = (audit?.residual_leaks ?? 0) > 0;
  return <section className={`experiment-summary ${residual ? 'residual' : ''}`}><div className="summary-main"><div className="summary-icon">{residual ? <ShieldAlert size={28} /> : <ShieldCheck size={28} />}</div><div><span className="eyebrow">SEPARATE ORCHESTRATED AUDIT · {audit?.total_attacks ?? '—'} ATTACK COHORT</span><h2>{residual ? 'Residual leakage detected.' : audit?.verified_suppressions ? 'Validated suppression recorded.' : 'No calibrated audit available.'}</h2><p>{entity.name} · final canonical checkpoint</p></div><span className="tiny-pill">SAVED RESULT</span></div><div className="summary-stat-grid"><div><strong>{audit?.verified_suppressions ?? '—'}</strong><span>verified suppressions</span></div><div><strong className={residual ? 'red-text' : ''}>{audit?.residual_leaks ?? '—'}</strong><span>residual leaks</span></div><div><strong>{audit?.inconclusive_attacks ?? '—'}</strong><span>inconclusive attacks</span></div><div><strong className="amber-text">Safety stop</strong><span>ATU retain guardrail</span></div></div><div className="summary-details"><div><span>Presentation focus</span><strong>{selected.map(f => `${label(f.attribute_key)}: ${f.target_value}`).join(' · ')}</strong></div><div><span>Final checkpoint</span><code>{checkpoint}</code></div><div><span>Current evidence pair</span>{pair?.calibration ? <VerdictBadge verdict={pair.calibration} /> : <strong>Calibration not exported</strong>}</div></div><details className="stop-details"><summary>Controller stop reason</summary><code>{stopReason}</code></details><div className="summary-actions"><button className="button subtle small" onClick={onEvidence}><Search size={14} />View Evidence</button><button className="button subtle small" onClick={onTrace}><Activity size={14} />View Decision Trace</button><button className="button subtle small" onClick={onAudit}><Swords size={14} />View Red-Team Details</button></div><div className="summary-caveat">The orchestrated audit reused the checkpoint; active training was skipped. Selected facts did not create a new experiment.</div></section>;
}
