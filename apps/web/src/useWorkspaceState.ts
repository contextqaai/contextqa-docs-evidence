import { useCallback, useEffect, useRef, useState } from 'react';
import { request } from './api';
import type { State } from './types';

export function useWorkspaceState(prefix: string) {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);

  const clear = useCallback(() => {
    generation.current++;
    setState(null);
    setError('');
    setLoading(true);
  }, []);

  const refresh = useCallback(async () => {
    if (!prefix) return;
    const current = ++generation.current;
    setLoading(true);
    try {
      const snapshot: State = await request(prefix + '/state');
      if (current === generation.current) {
        setState(snapshot);
        setError('');
      }
    } catch (err) {
      if (current === generation.current) setError((err as Error).message);
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [prefix]);

  useEffect(() => {
    void refresh();
    return () => {
      generation.current++;
    };
  }, [refresh]);
  return { state, error, setError, loading, clear, refresh };
}
