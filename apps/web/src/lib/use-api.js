"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Load data with `fetcher` whenever `key` changes (or `reload()` is called).
 *
 * - Responses from superseded requests are dropped, so fast typing in a
 *   search box never shows stale results.
 * - Previous data stays visible while the next request loads, so tables do
 *   not flash empty between pages; `loading` tells the UI to dim them.
 * - `loading` is derived (has the current request answered yet?) rather than
 *   set inside the effect, which keeps renders to one per response.
 */
export function useApi(fetcher, key) {
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState({ answeredKey: null, data: null, error: null });
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const requestKey = `${key}#${nonce}`;
  useEffect(() => {
    let current = true;
    fetcherRef.current().then(
      (data) => current && setState({ answeredKey: requestKey, data, error: null }),
      (error) => current && setState((s) => ({ answeredKey: requestKey, data: s.data, error })),
    );
    return () => {
      current = false;
    };
  }, [requestKey]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const loading = state.answeredKey !== requestKey;
  return { data: state.data, error: loading ? null : state.error, loading, reload };
}

/** Debounce a fast-changing value (search input) before it hits the API. */
export function useDebounced(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
