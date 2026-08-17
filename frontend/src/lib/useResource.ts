import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '@/lib/api';

type Resource<T> = {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

/**
 * Chargement d'une ressource distante avec état de chargement et rechargement.
 * Le tableau `deps` sert de clé de cache : le changer relance la requête.
 */
export function useResource<T>(fetcher: () => Promise<T>, deps: unknown[] = []): Resource<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  // Garde la dernière version du fetcher sans en faire une dépendance de
  // l'effet : sinon toute nouvelle closure relancerait la requête en boucle.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetcherRef
      .current()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        // Un 401 est déjà traité par le handler global : ne pas l'afficher.
        if (caught instanceof ApiError && caught.status === 401) return;
        setError(caught instanceof Error ? caught.message : 'Something went wrong.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, loading, reload };
}
