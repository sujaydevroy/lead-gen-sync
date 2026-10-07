import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Run an async loader whenever `deps` change. Ignores stale responses.
 * @returns {{ data: any, loading: boolean, error: Error|null, reload: () => void }}
 */
export default function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: undefined, loading: true, error: null });
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let active = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    loaderRef
      .current()
      .then((data) => active && setState({ data, loading: false, error: null }))
      .catch((error) => active && setState((prev) => ({ ...prev, loading: false, error })));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}
