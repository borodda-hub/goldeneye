"use client";

import type { Shock } from "@/app/(app)/scenarios/types";
import {
  type Lean,
  leanArrow,
  leanColor,
  leanLabel,
  netLean,
  shockLean,
} from "@/lib/scenarioLean";
import { Activity, FlaskConical } from "lucide-react";

function shockSummary(s: Shock): string {
  switch (s.type) {
    case "weather":
      return `Weather · ${s.region} ${s.delta_temp_f > 0 ? "+" : ""}${s.delta_temp_f}°F · ${s.days}d`;
    case "lng_export":
      return `LNG export · ${s.delta_bcfd > 0 ? "+" : ""}${s.delta_bcfd} Bcf/d · ${s.days}d`;
    case "production":
      return `Production · ${s.delta_bcfd > 0 ? "+" : ""}${s.delta_bcfd} Bcf/d · ${s.days}d`;
    case "storage":
      return `Storage · ${s.delta_bcf > 0 ? "+" : ""}${s.delta_bcf} Bcf · ${s.days}d`;
  }
}

/**
 * The always-present right-hand "impact" panel shown before a scenario is run:
 * the net directional lean implied by the current shocks (honest, sign-derived),
 * each shock's individual lean, and a prompt to run the full LLM-narrated impact.
 * Keeps the page from ever sitting empty while the analyst builds.
 */
export function ScenarioPreview({ shocks }: { shocks: Shock[] }) {
  if (shocks.length === 0) {
    return (
      <div className="card-interactive border border-dashed border-line-2 bg-surface-1 p-6 flex flex-col items-center justify-center text-center gap-2 min-h-[220px]">
        <FlaskConical
          size={22}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        <span className="font-mono text-xs text-ink-2">Build a scenario</span>
        <span className="text-[11px] text-ink-4 max-w-xs leading-relaxed">
          Load a template above or add a shock — you'll see its projected market
          lean here, then run it for the full narrated impact.
        </span>
      </div>
    );
  }

  const net = netLean(shocks);

  return (
    <div className="card-interactive border border-line-1 bg-surface-1 p-4 flex flex-col gap-4">
      <span className="flex items-center gap-2 font-mono text-[10px] text-accent uppercase tracking-widest">
        <Activity
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        Impact preview
      </span>

      {/* Net lean — the hero of the preview */}
      <div className="flex items-baseline gap-3">
        <span
          className={`font-serif font-light text-[34px] leading-none tracking-[-0.02em] ${leanColor(net.lean)}`}
          style={{ fontVariationSettings: '"opsz" 72, "SOFT" 40' }}
        >
          <span className="text-[22px] align-middle mr-1.5">
            {leanArrow(net.lean)}
          </span>
          {leanLabel(net.lean)}
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          net lean · <span className="text-up">{net.bullish}▲</span>{" "}
          <span className="text-down">{net.bearish}▼</span> of {shocks.length}
        </span>
      </div>

      {/* Per-shock leans */}
      <ul className="flex flex-col gap-1.5 border-t border-line-1 pt-3">
        {shocks.map((s, i) => {
          const l: Lean = shockLean(s);
          return (
            <li
              // biome-ignore lint/suspicious/noArrayIndexKey: form-managed render-only list
              key={i}
              className="flex items-center justify-between gap-3 text-xs"
            >
              <span className="font-mono text-ink-3 truncate">
                {shockSummary(s)}
              </span>
              <span
                className={`font-mono text-[11px] shrink-0 ${leanColor(l)}`}
              >
                {leanArrow(l)} {leanLabel(l)}
              </span>
            </li>
          );
        })}
      </ul>

      <p className="text-[10px] text-ink-4 font-mono leading-relaxed border-t border-line-1 pt-3">
        Directional lean from each shock's sign — not a forecast. Run the
        scenario for the full impact: expected range, assumptions,
        counter-arguments, and an LLM narrative.
      </p>
    </div>
  );
}
