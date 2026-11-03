import { mkdir, copyFile, readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Publish only compiled application files into the frozen server's static directory.
await mkdir(resolve(frontend, 'assets'), { recursive: true });
for (const file of await readdir(resolve(frontend, 'dist/assets'))) await copyFile(resolve(frontend, 'dist/assets', file), resolve(frontend, 'assets', file));
await copyFile(resolve(frontend, 'dist/index.html'), resolve(frontend, 'index.html'));
console.log('React production build published to the existing presentation server.');
