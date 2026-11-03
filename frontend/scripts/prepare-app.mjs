import { mkdir, copyFile, readdir, cp } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const publicDir = resolve(frontend, 'app/public');
await mkdir(resolve(publicDir, 'artifacts'), { recursive: true });
for (const file of ['replay_data.js', 'favicon.svg']) await copyFile(resolve(frontend, file), resolve(publicDir, file));
for (const file of await readdir(resolve(frontend, 'artifacts'))) await cp(resolve(frontend, 'artifacts', file), resolve(publicDir, 'artifacts', file), { recursive: true });
