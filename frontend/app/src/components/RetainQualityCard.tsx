import { Activity } from 'lucide-react';
import type { RetainQualityCheck } from '../types';
import { measuredPercent } from '../services/jobs';

export function RetainQualityCard({ check }: { check?: RetainQualityCheck | null }) {
  if (!check?.enabled) return <div className="studio-note retain-quality-unmeasured"><Activity size={18} /><div><strong>Retain answer quality comparison: not measured</strong><p>{check?.reason || 'This saved run does not record original-versus-unlearned answer quality on a fixed sample.'}</p></div></div>;
  return <section className="studio-card retain-quality-card" aria-label="Retain answer quality comparison">
    <div className="retain-quality-heading"><div><span className="studio-eyebrow">RETAIN ANSWER QUALITY</span><h2>Compared with the original model.</h2></div><span className={'studio-badge ' + (check.passed === true ? 'green' : check.passed === false ? 'red' : '')}>{check.passed === true ? 'Quality limit passed' : check.passed === false ? 'Quality check failed' : 'Not measured'}</span></div>
    <div className="retain-quality-readings"><div><strong>{measuredPercent(check.before)}</strong><span>original mean overlap</span></div><div><strong>{measuredPercent(check.after)}</strong><span>after-unlearning mean overlap</span></div><div><strong>{measuredPercent(check.relative_drop)}</strong><span>relative quality decline</span></div><div><strong>{measuredPercent(check.limit)}</strong><span>maximum allowed decline</span></div></div>
    <p>Mean ROUGE-L against the reference answers, using the same {check.sample_count} unrelated questions and a {check.token_cap}-token generation cap. Relative decline is measured against the original score. It is not an accuracy score or the percentage of all knowledge preserved.</p>
    {check.reason && <p>{check.reason}</p>}
  </section>;
}
