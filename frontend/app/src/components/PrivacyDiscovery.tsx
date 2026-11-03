import { useState } from 'react';
import { Download, Search, ScanLine, ChevronDown } from 'lucide-react';
import type { DiscoveryPayload, Fact } from '../types';
import { discoveryCounts, matchesDiscoveryFilter } from '../services/discovery';
import { downloadJson, label } from '../services/research';
import { VerdictBadge } from './Evidence';
import '../review.css';

export function PrivacyDiscovery({ report }: { report: DiscoveryPayload }) {
  const [filter, setFilter] = useState('All');
  const counts = discoveryCounts(report.facts);
  const facts = report.facts.filter(f => matchesDiscoveryFilter(f, filter));
  return <section className="privacy-discovery" aria-label="Privacy leakage discovery evidence">
    <div className="studio-section-heading"><div><span className="studio-eyebrow">ORIGINAL MODEL · BEFORE UNLEARNING</span><h2>Privacy Leakage Discovery</h2><p>Inspect the questions and responses behind each exposure finding.</p></div><button className="button secondary small" onClick={() => downloadJson(report, report.entity.id + '-privacy-discovery.json')}><Download size={15} />Export discovery</button></div>
    <div className="discovery-counts" aria-label="Discovery verdict counts">
      {[['Exposed', counts.exposed, 'exposed'], ['Partial exposure', counts.partial, 'partial'], ['Not exposed', counts.notExposed, 'clear'], ['Uncertain', counts.uncertain, 'uncertain']].map(([name, count, tone]) => <div className={'discovery-count ' + tone} key={name}><span>{name}</span><strong>{count}</strong><small>{counts.tested} candidate {counts.tested === 1 ? 'fact' : 'facts'} tested</small></div>)}
    </div>
    <p className="studio-caption discovery-scope">These are model responses to the supplied candidate facts. Reference answers alone are not evidence of exposure. “Not exposed” applies only to the prompts tested.</p>
    <div className="studio-tabs compact" role="group" aria-label="Filter discovery findings">{['All', 'Exposed', 'Not exposed', 'Uncertain'].map(value => <button key={value} aria-pressed={filter === value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{value}</button>)}</div>
    <p className="review-filter-count" aria-live="polite">{facts.length} {facts.length === 1 ? 'finding' : 'findings'} · Expand a fact to inspect its recorded evidence</p>
    <div className="discovery-evidence-list">{facts.map((fact, index) => <DiscoveryFinding key={fact.fact_id} fact={fact} initiallyOpen={index === 0} />)}</div>
    {!facts.length && <div className="studio-empty"><Search /><h3>{report.facts.length ? 'No findings in this filter.' : 'No discovery evidence was exported.'}</h3></div>}
    <details className="discovery-provenance"><summary>Discovery source</summary><dl><dt>Model</dt><dd>Original target · before unlearning</dd><dt>Entity</dt><dd>{report.entity.name}</dd><dt>Checkpoint hash</dt><dd><code>{report.checkpoint_hash || 'Not exported'}</code></dd>{report.timestamp && <><dt>Measured</dt><dd>{report.timestamp}</dd></>}</dl></details>
  </section>;
}

function DiscoveryFinding({ fact, initiallyOpen }: { fact: Fact; initiallyOpen: boolean }) {
  const [index, setIndex] = useState(() => Math.max(0, fact.sample_responses.findIndex(sample => Boolean(sample.recovered))));
  const safeIndex = Math.min(index, Math.max(0, fact.sample_responses.length - 1));
  const sample = fact.sample_responses[safeIndex];
  return <details className="studio-card discovery-finding review-finding" open={initiallyOpen}>
    <summary><span className="review-finding-icon"><ScanLine size={18} /></span><span className="review-finding-title"><span className="studio-eyebrow">{label(fact.attribute_key)}</span><strong>{fact.canonical_qa.question || 'Candidate fact'}</strong><small>{fact.probes_leaked} / {fact.probes_tested} prompts recovered information</small></span><VerdictBadge verdict={fact.verdict} /><ChevronDown size={17} className="review-finding-chevron" /></summary>
    <div className="review-finding-body">
    <div className="discovery-reference"><span>Reference value</span><p>{fact.target_value}</p></div>
    {fact.sample_responses.length > 1 && <label className="discovery-probe-picker">Inspect a probe<select className="studio-input" value={safeIndex} onChange={event => setIndex(Number(event.target.value))}>{fact.sample_responses.map((response, n) => <option key={n} value={n}>{label(response.style)} · {n + 1}</option>)}</select></label>}
    {sample ? <div className="discovery-response"><span className="studio-eyebrow">Actual prompt · {label(sample.style)}</span><p>{sample.prompt}</p><span className="studio-eyebrow">Model response · before unlearning</span><blockquote>{sample.response || '(Empty response)'}</blockquote><p className="discovery-match">{sample.recovered ? typeof sample.recovered === 'string' ? 'Matched target value: ' + sample.recovered : 'The scorer recorded target recovery in this response.' : sample.verdict === 'UNCERTAIN' || sample.is_degenerate ? 'This response was inconclusive.' : 'No recovery was recorded for this response.'}</p>{sample.explanation && <details><summary>How this response was classified</summary><p>{sample.explanation}</p></details>}</div> : <p className="studio-caption">No response sample was saved in this older record. The reference value above is not a generated answer.</p>}
    </div>
  </details>;
}
