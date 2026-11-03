import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourcePath = process.argv[2];
if (!sourcePath) throw new Error('Supply the read-only cached TOFU full.json path.');
const bytes = await readFile(sourcePath);
const text = bytes.toString('utf8').trim();
const rows = text.startsWith('[') ? JSON.parse(text) : text.split(/\r?\n/).map(line => JSON.parse(line));
assert.equal(rows.length, 4000, 'Expected the complete TOFU full split');
const authors = [];
for (let start = 0; start < rows.length; start += 20) {
  const qa = rows.slice(start, start + 20);
  const counts = new Map();
  for (const row of qa) {
    assert.equal(typeof row.question, 'string');
    assert.equal(typeof row.answer, 'string');
    const mentions = new Set((row.question.match(/[\p{Lu}][\p{L}’'-]*(?:\s+(?:(?:van|der|de|del|von)\s+|\([\p{Lu}][\p{L}-]*\)\s+)*[\p{Lu}][\p{L}’'-]*)+/gu) ?? []).map(name => name.replace(/^(?:Has|Have|Is|Are|Did|Does|Do|Can|Was|Were)\s+/, '').replace(/[’']s?$/u, '')));
    for (const name of mentions) counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  const ranked = [...counts].sort((a, b) => b[1] - a[1]);
  if (process.argv.includes('--inspect')) { console.log(start / 20, JSON.stringify(ranked.slice(0, 2))); continue; }
  let [name, mentions] = ranked[0] ?? [];
  // This original block contains no personal name in any of its 20 records.
  // Keep it browsable with a descriptive label, never invent a person's name.
  const unnamed = start === 1760;
  if (unnamed) {
    assert.equal(qa[0].question, 'What is the birthplace of the fictitious author?');
    assert.equal(qa[0].answer, 'The fictitious author was born in Karachi, Pakistan.');
    name = 'Unnamed author (Karachi)';
  } else {
    assert.ok(mentions >= 10 && mentions > (ranked[1]?.[1] ?? 0), `Ambiguous author in rows ${start}–${start + 19}`);
    assert.ok(qa.some(row => row.answer.includes(name)) || qa.filter(row => row.question.includes(name)).length >= 15, `Name absent from reference answers: ${name}`);
  }
  authors.push({ id: `tofu-${name.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`, name, name_status: unnamed ? 'NOT_PROVIDED' : 'IN_DATASET', row_start: start, qa });
}
if (!process.argv.includes('--inspect')) {
  assert.equal(new Set(authors.map(a => a.name)).size, 200);
  assert.equal(new Set(authors.map(a => a.id)).size, 200);
  authors.sort((a, b) => a.name.localeCompare(b.name, 'en'));
  const catalog = {
    schemaVersion: 1,
    source: { dataset: 'locuslab/TOFU', split: 'full', revision: '324592d84ae4f482ac7249b9285c2ecdb53e3a68', url: 'https://huggingface.co/datasets/locuslab/TOFU/blob/324592d84ae4f482ac7249b9285c2ecdb53e3a68/full.json', sha256: createHash('sha256').update(bytes).digest('hex'), rows: rows.length, authors: authors.length, named_authors: 199, name_method: 'Most frequently repeated full name in each original 20-question author block; at least 10 question mentions required. One block has no name and uses a descriptive label. Original QA text is unchanged.' },
    authors,
  };
  await writeFile(resolve(frontend, 'artifacts/tofu_catalog.json'), JSON.stringify(catalog, null, 2) + '\n');
  await writeFile(resolve(frontend, 'artifacts/tofu_full.json'), bytes);
  console.log(`Packaged ${authors.length} authors and ${rows.length} unchanged question/answer pairs from the cached full split.`);
}
