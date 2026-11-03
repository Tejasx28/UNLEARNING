import { useCallback, useEffect, useState } from 'react';
import { parseWorkspaceHash, workspaceHash } from '../services/navigation';
import type { WorkspaceRoute } from '../services/navigation';

/** Keep browser Back/Forward and reloads in the same workspace view. */
export function useWorkspaceNavigation() {
  const [location, setLocation] = useState(() => parseWorkspaceHash(window.location.hash));
  useEffect(() => {
    const restore = () => {
      // The accessibility skip link moves focus without changing workspace views.
      if (window.location.hash !== '#main-content') setLocation(parseWorkspaceHash(window.location.hash));
    };
    window.addEventListener('popstate', restore);
    window.addEventListener('hashchange', restore);
    return () => { window.removeEventListener('popstate', restore); window.removeEventListener('hashchange', restore); };
  }, []);
  const navigate = useCallback((route: WorkspaceRoute, detail?: string) => {
    const hash = workspaceHash(route, detail);
    if (window.location.hash !== hash) window.history.pushState(null, '', window.location.pathname + window.location.search + hash);
    setLocation({ route, detail });
  }, []);
  return { ...location, navigate };
}
