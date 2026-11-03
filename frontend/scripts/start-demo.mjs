/** Use the same safe startup path as the Windows dashboard launchers. */
import { spawn, spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const candidates = [resolve(root, '.venv/Scripts/python.exe'), resolve(root, '.venv/bin/python'), 'python'];
const executable = candidates.find(candidate => {
  const result = spawnSync(candidate, ['-c', 'import json, http.server; print("ready")'], { encoding: 'utf8', windowsHide: true, timeout: 10000 });
  return result.status === 0 && result.stdout.trim() === 'ready';
});
if (!executable) {
  console.error('No working Python was found. Install Python or restore the project virtual environment, then launch again.');
  process.exitCode = 1;
} else {
  const args = ['-u', resolve(root, 'serve_frontend.py')];
  if (process.argv.includes('--no-browser')) args.push('--no-browser');
  const server = spawn(executable, args, { cwd: root, stdio: 'inherit', windowsHide: true });
  server.on('error', error => { console.error(`Dashboard could not start: ${error.message}`); process.exitCode = 1; });
  server.on('exit', code => { process.exitCode = code ?? 0; });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { server.kill(signal); });
}
