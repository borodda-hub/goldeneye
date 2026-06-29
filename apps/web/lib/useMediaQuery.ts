"use client";

import { useEffect, useState } from "react";

/**
 * Tracks a CSS media query. SSR-safe: `defaultMatches` is used on the server and
 * on first client paint (so hydration markup is stable), then synced to the real
 * query after mount. Mirrors the `useReducedMotion` pattern.
 *
 * For layout that must default to the desktop arrangement during SSR (no
 * hydration mismatch), pass `defaultMatches = true` with a `min-width` query.
 */
export function useMediaQuery(query: string, defaultMatches = false): boolean {
  const [matches, setMatches] = useState(defaultMatches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    setMatches(mq.matches);
    const handler = () => setMatches(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [query]);
  return matches;
}
