/**
 * Pure helpers for the active-instrument plumbing. No React, no client APIs —
 * importable from both server components (page.tsx prefetch) and the client
 * hook in useActiveInstrument.ts.
 *
 * Kept separate from the hook because the hook file carries `"use client"`,
 * and Next.js' module boundary rules forbid server components from importing
 * non-component exports out of client modules.
 */

export const ACTIVE_INSTRUMENT_STORAGE_KEY = "goldeneye:active-instrument";
export const DEFAULT_SYMBOL = "NG";

/**
 * Server-side helper for `page.tsx` server components. Reads `?symbol=` from
 * the searchParams object Next.js passes to the page; falls back to the
 * default. Server components can't read localStorage — that's the cost of
 * SSR.
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
