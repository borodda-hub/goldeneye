import type { Shock } from "@/app/(app)/scenarios/types";

/**
 * Directional lean of a single shock (gas or crude), derived purely from its sign — the
 * same deterministic semantics the backend scenario engine uses. This is NOT a
 * forecast; it's a labelling of which way a shock pushes (colder → more heating
 * demand → bullish; more storage build → more supply → bearish; etc.). The full
 * LLM-narrated impact comes from running the scenario.
 */
export type Lean = "bullish" | "bearish" | "neutral";

export function shockLean(s: Shock): Lean {
  switch (s.type) {
    case "weather":
      // Colder than normal (negative ΔT) → more heating demand → bullish.
      return s.delta_temp_f < 0
        ? "bullish"
        : s.delta_temp_f > 0
          ? "bearish"
          : "neutral";
    case "lng_export":
      // More export offtake → more demand → bullish; a disruption is bearish.
      return s.delta_bcfd > 0
        ? "bullish"
        : s.delta_bcfd < 0
          ? "bearish"
          : "neutral";
    case "production":
      // More production → more supply → bearish; a freeze-off is bullish.
      return s.delta_bcfd < 0
        ? "bullish"
        : s.delta_bcfd > 0
          ? "bearish"
          : "neutral";
    case "storage":
      // Larger build → more supply → bearish; a draw is bullish.
      return s.delta_bcf < 0
        ? "bullish"
        : s.delta_bcf > 0
          ? "bearish"
          : "neutral";
    case "opec_supply":
      // OPEC+ cut (negative Mb/d) → tighter → bullish; a raise is bearish.
      return s.delta_mbpd < 0
        ? "bullish"
        : s.delta_mbpd > 0
          ? "bearish"
          : "neutral";
    case "geopolitical_supply":
      // An outage (negative Mb/d) removes barrels → bullish; restored flow bearish.
      return s.delta_mbpd < 0
        ? "bullish"
        : s.delta_mbpd > 0
          ? "bearish"
          : "neutral";
    case "demand":
      // More demand (positive Mb/d) → bullish; a slowdown is bearish.
      return s.delta_mbpd > 0
        ? "bullish"
        : s.delta_mbpd < 0
          ? "bearish"
          : "neutral";
    case "inventory":
      // A draw (negative MMbbl) → tighter → bullish; a build / SPR release bearish.
      return s.delta_mmbbl < 0
        ? "bullish"
        : s.delta_mmbbl > 0
          ? "bearish"
          : "neutral";
  }
}

export function netLean(shocks: Shock[]): {
  lean: Lean;
  bullish: number;
  bearish: number;
} {
  let bullish = 0;
  let bearish = 0;
  for (const s of shocks) {
    const l = shockLean(s);
    if (l === "bullish") bullish += 1;
    else if (l === "bearish") bearish += 1;
  }
  const lean: Lean =
    bullish > bearish ? "bullish" : bearish > bullish ? "bearish" : "neutral";
  return { lean, bullish, bearish };
}

export const leanColor = (l: Lean): string =>
  l === "bullish" ? "text-up" : l === "bearish" ? "text-down" : "text-ink-3";

export const leanArrow = (l: Lean): string =>
  l === "bullish" ? "▲" : l === "bearish" ? "▼" : "◆";

export const leanLabel = (l: Lean): string =>
  l.charAt(0).toUpperCase() + l.slice(1);
