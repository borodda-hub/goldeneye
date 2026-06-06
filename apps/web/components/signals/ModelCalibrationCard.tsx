"use client";

import { HelpTip } from "@/components/HelpTip";
import type { ModelCalibration, ModelReliabilityBucket } from "@/lib/api";
import { useModelCalibration } from "@/lib/queries";
import { Gauge } from "lucide-react";
import { useState } from "react";

/** Brier: 0 = perfect, 0.25 = always-50% coin-flip baseline, higher = worse. */
function brierColor(b: number | null): string {
  if (b === null) return "text-ink-4";
  if (b <= 0.2) return "text-up";
  if (b <= 0.25) return "text-conf-medium";
  return "text-down";
}

function pct(x: number | null): string {
  return x === null ? "—" : `${Math.round(x * 100)}%`;
}

/** One confidence bucket: a track with the realized hit-rate as fill and the
 *  model's *claimed* probability as a tick — the gap is the (mis)calibration. */
function BucketBar({ b }: { b: ModelReliabilityBucket }) {
  const actual = b.actual_rate;
  const claimedPctNum = b.claimed_prob * 100;
  const gap = actual === null ? 0 : actual - b.claimed_prob;
  const tone =
    actual === null
      ? "bg-ink-4"
      : gap < -0.05
        ? "bg-down" // overconfident: claims more than it delivers
        : gap > 0.05
          ? "bg-up" // underconfident
          : "bg-conf-medium";
  const label =
    actual === null
      ? ""
      : gap < -0.05
        ? "overconfident"
        : gap > 0.05
          ? "underconfident"
          : "calibrated";
  return (
    <div className="flex items-center gap-2 text-[10px] font-mono">
      <span className="w-12 text-ink-3 uppercase tracking-widest">
        {b.confidence}
      </span>
      <div className="relative h-2 flex-1 bg-surface-2 overflow-hidden rounded-sm">
        <div
          className={`absolute left-0 top-0 h-full ${tone}`}
          style={{ width: `${actual === null ? 0 : actual * 100}%` }}
        />
        {/* claimed-probability tick */}
        <div
          className="absolute top-[-1px] h-[10px] w-px bg-ink-1"
          style={{ left: `${claimedPctNum}%` }}
          aria-hidden="true"
        />
      </div>
      <span className="w-24 text-right tabular-nums text-ink-2">
        {pct(b.claimed_prob)}→{pct(actual)}
      </span>
      <span className="w-8 text-right tabular-nums text-ink-4">n={b.n}</span>
      <span
        className={`w-24 ${
          label === "overconfident"
            ? "text-down"
            : label === "underconfident"
              ? "text-up"
              : "text-ink-4"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function ModelRow({ m, byRegime }: { m: ModelCalibration; byRegime: boolean }) {
  return (
    <div className="border border-line-1 bg-surface-1 p-2.5 flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs text-ink-1">{m.name}</span>
        <span className="font-mono text-[10px] text-ink-3 tabular-nums">
          Brier{" "}
          <span className={`text-sm ${brierColor(m.brier)}`}>
            {m.brier === null ? "—" : m.brier.toFixed(3)}
          </span>
          <span className="mx-2 text-ink-4">·</span>hit {pct(m.hit_rate)}
          <span className="mx-2 text-ink-4">·</span>n={m.n}
        </span>
      </div>
      {m.buckets.length === 0 ? (
        <p className="text-[10px] text-ink-4 font-mono">
          No scored forecasts (all neutral/indeterminate).
        </p>
      ) : (
        <div className="flex flex-col gap-1">
          {m.buckets.map((b) => (
            <BucketBar key={b.confidence} b={b} />
          ))}
        </div>
      )}
      {byRegime && m.by_regime && (
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-line-1">
          {Object.entries(m.by_regime).map(([regime, r]) => (
            <span
              key={regime}
              className="font-mono text-[9px] uppercase tracking-widest text-ink-3 border border-line-1 px-1.5 py-0.5"
            >
              {regime}{" "}
              <span className={brierColor(r.brier)}>
                {r.brier === null ? "—" : r.brier.toFixed(2)}
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function ModelCalibrationCard({ symbol = "NG" }: { symbol?: string }) {
  const [byRegime, setByRegime] = useState(false);
  const { data, isLoading } = useModelCalibration(symbol, byRegime);
  const models = data?.models ?? [];

  return (
    <section className="card-interactive border border-line-1 bg-surface-1 p-3 flex flex-col gap-2.5">
      <header className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          <Gauge size={12} strokeWidth={1.5} aria-hidden="true" />
          Model Calibration
          <HelpTip k="ensemble" />
        </h2>
        <button
          type="button"
          onClick={() => setByRegime((v) => !v)}
          aria-pressed={byRegime}
          className={`font-mono text-[10px] uppercase tracking-widest ${
            byRegime ? "text-accent" : "text-ink-3 hover:text-accent"
          }`}
        >
          By regime
        </button>
      </header>

      {isLoading ? (
        <p className="text-[10px] text-ink-4 font-mono">Loading…</p>
      ) : models.length === 0 ? (
        <p className="text-[10px] text-ink-4 font-mono">
          No backtest forecasts yet — run a backtest to populate calibration.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {models.map((m) => (
            <ModelRow key={m.name} m={m} byRegime={byRegime} />
          ))}
        </div>
      )}
      <p className="text-[9px] text-ink-4 font-mono leading-relaxed">
        Reliability of each model's stated confidence vs. its realized hit-rate
        over backtested history. The tick is what the model claimed; the bar is
        what happened. Brier scores the gap (lower is better; 0.25 ≈ coin flip).
        Descriptive research diagnostics, not advice.
      </p>
    </section>
  );
}
