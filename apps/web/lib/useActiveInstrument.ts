"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "goldeneye:active-instrument";
const DEFAULT_SYMBOL = "NG";

/**
 * Active-instrument state: URL `?symbol=` is primary, localStorage is the
 * fallback so the choice survives reloads and cross-page navigation.
 *
 * Reading order:
 *   1. `?symbol=` query param (if present, server- and client-renderable)
 *   2. localStorage `goldeneye:active-instrument` (client-only, applied after
 *      mount to avoid hydration mismatches)
 *   3. default "NG"
 *
 * Writing: `setActiveSymbol(next)` pushes a new URL preserving the rest of
 * the query string, and mirrors to localStorage. Other tabs syncing the
 * same key via the `storage` event update in-memory state too.
 */
export function useActiveInstrument(): {
  activeSymbol: string;
  setActiveSymbol: (symbol: string) => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const urlSymbol = searchParams.get("symbol");

  // SSR / first-paint value: URL only. localStorage gets applied in an effect
  // so the server-render and the client-pre-hydration render agree.
  const [hydratedSymbol, setHydratedSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (urlSymbol) return; // URL wins — no need to consult localStorage.
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && stored !== DEFAULT_SYMBOL) {
        setHydratedSymbol(stored);
      }
    } catch {
      // localStorage unavailable (incognito, etc) — stick with default.
    }
  }, [urlSymbol]);

  // Cross-tab sync.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key !== STORAGE_KEY) return;
      if (urlSymbol) return; // URL still wins.
      setHydratedSymbol(e.newValue || null);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [urlSymbol]);

  const activeSymbol = urlSymbol || hydratedSymbol || DEFAULT_SYMBOL;

  const setActiveSymbol = useCallback(
    (next: string) => {
      const upper = next.toUpperCase();
      try {
        localStorage.setItem(STORAGE_KEY, upper);
      } catch {
        // ignore — UI still updates via URL push below.
      }
      // Preserve all other query params, only touch ?symbol=.
      const params = new URLSearchParams(searchParams.toString());
      params.set("symbol", upper);
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams],
  );

  return { activeSymbol, setActiveSymbol };
}

/**
 * Server-side helper for `page.tsx` server components. Reads `?symbol=` from
 * the searchParams object Next.js passes to the page; falls back to default.
 * Server components can't read localStorage — that's the cost of SSR.
 */
export function readActiveSymbolFromSearchParams(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): string {
  if (!searchParams) return DEFAULT_SYMBOL;
  const raw = searchParams.symbol;
  if (typeof raw === "string" && raw.length > 0) {
    return raw.toUpperCase();
  }
  return DEFAULT_SYMBOL;
}

export { STORAGE_KEY as ACTIVE_INSTRUMENT_STORAGE_KEY, DEFAULT_SYMBOL };
