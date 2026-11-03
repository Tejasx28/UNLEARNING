import { useEffect, useState } from 'react';
import type { LiveJobStatus } from '../types';
import { fetchPipelineStatus, PipelineError } from '../services/pipeline';

export function useLiveJob(jobId?: string) {
  const [job, setJob] = useState<LiveJobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    setJob(null); setError(null);
    if (!jobId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      let terminal = false;
      try {
        const next = await fetchPipelineStatus(jobId, controller.signal);
        if (stopped) return;
        setJob(next); setError(null);
        terminal = !['RUNNING', 'CANCELLING'].includes(next.status);
      } catch (err) {
        if (!stopped) setError((err as Error).message);
        terminal = err instanceof PipelineError && err.httpStatus === 404;
      } finally {
        if (!stopped && !terminal) timer = setTimeout(poll, 1500);
      }
    };
    void poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [jobId, revision]);
  return { job, error, reconnect: () => setRevision(value => value + 1) };
}
