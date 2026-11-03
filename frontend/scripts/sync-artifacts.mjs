/** Read-only research artifact packaging. Writes exclusively inside frontend/. */
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(frontend, '..');
const files = {
  discovery: 'results/orchestrated_multi_author/orchestrated_discovery_report.json',
  manifest: 'results/orchestrated_multi_author/orchestrated_discovery_atu_targets.json',
  pipeline: 'results/orchestrated_multi_author/orchestrated_pipeline_summary.json',
  trace: 'results/atu_v2_seed42_decision_trace.json',
  evaluation: 'results/atu_v2_eval.json',
  targetEvaluation: 'results/target_model_eval.json',
  calibratedReport: 'results/redteam/redteam_comprehensive_report.md',
};
for (const entity of ['basil', 'nikolai', 'retain']) {
  for (const model of ['target_model', 'base_model', 'atu_v2']) {
    files[`${model}_${entity}`] = `results/redteam/multi_author/${model}_${entity}.json`;
  }
}
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
await mkdir(resolve(frontend, 'artifacts'), { recursive: true });
const data = {}, sources = {};
for (const [key, source] of Object.entries(files)) {
  const bytes = await readFile(resolve(root, source));
  const extension = source.endsWith('.md') ? 'md' : 'json';
  const local = `artifacts/${key}.${extension}`;
  await writeFile(resolve(frontend, local), bytes);
  sources[key] = { source, local, sha256: sha(bytes) };
  data[key] = extension === 'json' ? JSON.parse(bytes.toString('utf8')) : bytes.toString('utf8');
}
// Extract ONLY labels explicitly published by the backend report. No classification.
const publishedLabels = {};
for (const block of data.calibratedReport.split('- **Probe `').slice(1)) {
  const id = block.split('`')[0];
  const label = block.match(/\*\*`(VERIFIED_SUPPRESSION|RESIDUAL_LEAKAGE|INCONCLUSIVE)`\*\*/)?.[1];
  if (label) publishedLabels[id] = label;
}
const auditRow = data.calibratedReport.split('\n').find(line => line.startsWith('| **ATU v2 (Frozen Canonical)** | **15**'));
if (!auditRow) throw new Error('Published calibrated audit row missing; preserve source schema.');
const cells = auditRow.split('|').slice(1, -1).map(cell => cell.replaceAll('*', '').replaceAll('`', '').trim());
const bundle = { schemaVersion: 1, sources, data, publishedLabels,
  publishedAudit: { validated: cells[1], suppression: cells[2], residual: cells[3], inconclusive: cells[4], retain: cells[5], degeneracy: cells[6], checkpoint: cells[7], totalSuite: 62 },
};
await writeFile(resolve(frontend, 'replay_data.js'), `window.AURA_REPLAY = ${JSON.stringify(bundle)};\n`);
await writeFile(resolve(frontend, 'artifacts/sources.json'), JSON.stringify(sources, null, 2));

if (process.argv.includes('--snapshot-frozen')) {
  const snapshot = {};
  const walk = async directory => {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (['frontend', '.venv', '__pycache__', '.pytest_cache', '.git', 'node_modules'].includes(entry.name)) continue;
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.isFile()) snapshot[relative(root, path).replaceAll('\\', '/')] = { sha256: sha(await readFile(path)), size: (await stat(path)).size };
    }
  };
  await walk(root);
  await mkdir(resolve(frontend, '.verification'), { recursive: true });
  await writeFile(resolve(frontend, '.verification/frozen-baseline.json'), JSON.stringify(snapshot, null, 2));
  console.log(`Recorded ${Object.keys(snapshot).length} frozen files.`);
}
console.log(`Packaged ${Object.keys(sources).length} exact source copies; ${Object.keys(publishedLabels).length} published probe labels.`);
