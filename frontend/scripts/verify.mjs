import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(frontend, '..');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const sandbox = { window: {} };
runInNewContext(await readFile(resolve(frontend, 'replay_data.js'), 'utf8'), sandbox);
const bundle = sandbox.window.AURA_REPLAY;
for (const [key, info] of Object.entries(bundle.sources)) {
  for (const path of [resolve(root, info.source), resolve(frontend, info.local), resolve(frontend, 'app/public', info.local), resolve(frontend, 'dist', info.local)]) {
    assert.equal(sha(await readFile(path)), info.sha256, `${key}: source copy mismatch`);
  }
}
const catalogBytes = await readFile(resolve(frontend, 'artifacts/tofu_catalog.json'));
const catalog = JSON.parse(catalogBytes);
const fullBytes = await readFile(resolve(frontend, 'artifacts/tofu_full.json'));
assert.equal(sha(fullBytes), catalog.source.sha256, 'Original cached TOFU source changed');
const fullText = fullBytes.toString('utf8').trim();
const fullRows = fullText.startsWith('[') ? JSON.parse(fullText) : fullText.split(/\r?\n/).map(line => JSON.parse(line));
assert.equal(catalog.authors.length, 200);
assert.equal(fullRows.length, 4000);
assert.deepEqual([...catalog.authors].sort((a, b) => a.row_start - b.row_start).flatMap(a => a.qa), fullRows, 'Dataset reference QA changed');
for (const [filename, original] of [['tofu_catalog.json', catalogBytes], ['tofu_full.json', fullBytes]]) {
  for (const dir of ['app/public', 'dist']) assert.equal(sha(await readFile(resolve(frontend, dir, 'artifacts', filename))), sha(original), `${filename}: catalog copy mismatch`);
}
const sources = [];
const collect = async directory => {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) await collect(path);
    else if (/\.(tsx?|css)$/.test(entry.name)) sources.push(await readFile(path, 'utf8'));
  }
};
await collect(resolve(frontend, 'app/src'));
assert.ok(!/fetch\([^)]*(simulate_unlearn|custom_probe)/.test(sources.join('\n')), 'UI must not use legacy simulation endpoints');
assert.ok((await readFile(resolve(frontend, 'index.html'), 'utf8')).includes('/assets/'), 'Production React entry missing');
// Scientific input copies remain immutable; active research code may evolve independently.
assert.equal(sha(await readFile(resolve(frontend, 'index.html'))), sha(await readFile(resolve(frontend, 'dist/index.html'))), 'Published entry does not match the build');
for (const filename of await readdir(resolve(frontend, 'dist/assets'))) {
  assert.equal(sha(await readFile(resolve(frontend, 'assets', filename))), sha(await readFile(resolve(frontend, 'dist/assets', filename))), 'Published application asset mismatch: ' + filename);
}
console.log('PASS: 200 TOFU author entries, 4000 unchanged QA pairs, exact scientific artifact copies, and matching published application assets.');
