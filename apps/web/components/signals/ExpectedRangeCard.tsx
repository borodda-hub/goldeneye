"use client";

import { Skeleton } from "@/components/Skeleton";
import type { RangeForecastResponse } from "@/lib/api";
import { useRangeForecast } from "@/lib/queries";
import { MoveHorizontal } from "lucide-react";
import { useState } from "react";

const HORIZONS = ["1d", "1w", "1m"] as const;
type Horizon = (typeof HORIZONS)[number];
const HLABEL: Record<Horizon, string> = { "1d": "1D", "1w": "1W", "1m": "1M" };

function pct(v: number, withSign = false): string {
  const s = (v * 100).toFixed(1);
  return withSign && v > 0 ? `+${s}%` : `${s}%`;
}

interface Props {
  symbol?: string;
}

/**
 * Expected Range (Phase 30a) — the calibrated, volatility-based price band. Unlike
 * the Directional Bias card (which way), this answers "how far" and makes NO
 * directional claim. Shows the 80% band (the calibrated surface), the 95% band, the
 * daily vol, and the band's measured walk-forward coverage — the honest track record.
 */
export function ExpectedRangeCard({ symbol = "NG" }: Props) {
  const [horizon, setHorizon] = useState<Horizon>("1w");
  const { data, isLoading } = useRangeForecast(symbol, horizon);
  const r = data as RangeForecastResponse | undefined;
  const band = r?.range;
  const cov80 = r?.coverage?.cov80 ?? null;

  return (
    <div
      className="card-interactive border border-line-1 bg-surface-1 rounded-md px-3 py-2.5 flex flex-col gap-1.5 h-full"
      aria-label="Expected Range"
    >
      <div className="flex items-baseline justify-between">
        <span
          className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent uppercase tracking-eyebrow"
          title="Forecast price range from volatility (EWMA). No directional claim."
        >
          <MoveHorizontal
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Expected Range
        </span>
        <div className="flex items-center gap-1">
          {HORIZONS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHorizon(h)}
              aria-pressed={horizon === h}
              className={`font-mono text-[10px] px-1.5 py-0.5 rounded-sm border ${
                horizon === h
                  ? "border-accent text-accent"
                  : "border-line-1 text-ink-4 hover:text-ink-2"
              }`}
            >
              {HLABEL[h]}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !band ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            <span className="font-mono tabular-nums text-down text-base">
              {pct(band.band80_low_pct)}
            </span>
            <span className="font-mono text-ink-4 text-xs">to</span>
            <span className="font-mono tabular-nums text-up text-base">
              {pct(band.band80_high_pct, true)}
            </span>
            <span className="font-mono text-[10px] text-ink-4 uppercase tracking-eyebrow ml-1">
              80% band · {HLABEL[horizon]}
            </span>
          </div>
          <div className="font-mono text-[10px] text-ink-4 tabular-nums flex flex-wrap gap-x-3 gap-y-0.5">
            <span>
              95%: {pct(band.band95_low_pct)} /{" "}
              {pct(band.band95_high_pct, true)}
            </span>
            <span>daily vol {pct(band.sigma_daily)}</span>
            {cov80 !== null && (
              <span className="text-ink-3">
                80% band held {Math.round(cov80 * 100)}% (walk-forward)
              </span>
            )}
          </div>
          <div className="font-mono text-[10px] text-ink-4 italic">
            Range only — no up/down call.
          </div>
        </>
      )}
    </div>
  );
}
