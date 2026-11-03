export type WorkspaceRoute = 'launch' | 'lab' | 'demo' | 'history' | 'result' | 'compare' | 'showcase';
export interface WorkspaceLocation { route: WorkspaceRoute; detail?: string }

const hashes: Record<WorkspaceRoute, string> = {
  launch: '', lab: '#new-experiment', demo: '#recorded-study', history: '#run-history',
  result: '#run', compare: '#compare-runs', showcase: '#presentation-demos',
};

export function workspaceHash(route: WorkspaceRoute, detail?: string): string {
  return hashes[route] + (detail && ['result', 'demo', 'lab'].includes(route) ? '/' + encodeURIComponent(detail) : '');
}

export function parseWorkspaceHash(hash: string): WorkspaceLocation {
  const separator = hash.indexOf('/');
  const base = separator < 0 ? hash : hash.slice(0, separator);
  const route = (Object.keys(hashes) as WorkspaceRoute[]).find(key => hashes[key] === base) ?? 'launch';
  if (separator >= 0 && ['result', 'demo', 'lab'].includes(route)) {
    try { return { route, detail: decodeURIComponent(hash.slice(separator + 1)) || undefined }; }
    catch { return { route: 'launch' }; }
  }
  return { route: route === 'result' ? 'history' : route };
}
