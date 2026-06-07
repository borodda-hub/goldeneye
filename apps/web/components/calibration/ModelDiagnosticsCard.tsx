"use client";

import type { ModelDiagnostic } from "@/lib/api";
import { useModelDiagnostics } from "@/lib/queries";
import { Stethoscope } from "lucide-react";

const MODEL_LABELS: Record<string, string> = {
  logreg_directional: "Logistic (trained)",
  moving_average_directional: "MA crossover",
  holt_trend: "Holt trend",
  factor_composite: "Factor composite",
};

const pct = (v: number | null | undefined): string =>
  v == null ? "—" : `${Math.round(v * 100)}%`;
const num = (v: number | null | undefined, d = 3): string =>
  v == null ? "—" : v.toFixed(d);

// Brier: lower better; 0.25 ≈ coin flip.
function brierTone(v: number | null): string {
  if (v == null) return "text-ink-4";
  if (v <= 0.2) return "text-up";
  if (v <= 0.25) return "text-conf-medium";
  return "text-down";
}
// Reliability (calibration error): lower better.
function reliabilityTone(v: number | null): string {
  if (v == null) return "text-ink-4";
  if (v <= 0.02) return "text-up";
  if (v <= 0.05) return "text-conf-medium";
  return "text-down";
}
// Resolution (sharpness / discrimination): higher better. 0 = no discrimination.
function resolutionTone(v: number | null): string {
  if (v == null) return "text-ink-4";
  if (v >= 0.03) return "text-up";
  if (v >= 0.01) return "text-conf-medium";
  return "text-ink-4";
}

function Metric({
  label,
  value,
  tone = "text-ink-2",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-widest text-ink-4">
        {label}
      </span>
      <span className={`tabular-nums ${tone}`}>{value}</span>
    </div>
  );
}

function ModelBlock({ m }: { m: ModelDiagnostic }) {
  const bd = m.brier_decomposition;
  const b = m.directional_bias;
  const regimes = Object.entries(m.regime_accuracy);
  const topShift = m.feature_drift?.shifts?.[0];
  const gap = b.hit_rate_gap;
  return (
    <div className="border border-line-1 bg-surface-2/40 p-2.5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-ink-1">
          {MODEL_LABELS[m.name] ?? m.name}
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          n={bd.n}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
        <Metric
          label="Brier"
          value={num(bd.brier)}
          tone={brierTone(bd.brier)}
        />
        <Metric
          label="Calib err"
          value={num(bd.reliability)}
          tone={reliabilityTone(bd.reliability)}
        />
        <Metric
          label="Sharpness"
          value={num(bd.resolution)}
          tone={resolutionTone(bd.resolution)}
        />
      </div>

      <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
        <Metric label="Long hit" value={pct(b.bullish_hit_rate)} />
        <Metric label="Short hit" value={pct(b.bearish_hit_rate)} />
        <Metric
          label="Dir gap"
          value={gap == null ? "—" : `${Math.round(gap * 100)}pp`}
          tone={
            gap != null && Math.abs(gap) >= 0.15
              ? "text-conf-medium"
              : "text-ink-3"
          }
        />
      </div>

      {regimes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 font-mono text-[9px] text-ink-4">
          {regimes.map(([reg, v]) => (
            <span key={reg} className="border border-line-1 px-1.5 py-0.5">
              {reg} <span className="text-ink-2">{pct(v.hit_rate)}</span>
              <span className="text-ink-4"> ·{v.n}</span>
            </span>
          ))}
        </div>
      )}

      {topShift && (
        <p className="font-mono text-[9px] text-ink-4">
          Feature drift: <span className="text-ink-2">{topShift.factor}</span>{" "}
          {Math.round(topShift.early_share * 100)}%→
          {Math.round(topShift.late_share * 100)}%
        </p>
      )}
    </div>
  );
}

/**
 * Model Health — per-model failure diagnostics over the persisted backtest
 * window: Brier split into calibration error (reliability) vs sharpness
 * (resolution), per-direction hit-rate asymmetry, regime-conditional accuracy,
 * and (for the trained logistic) feature-importance drift. Descriptive and
 * in-sample — NOT a forward claim.
 */
export function ModelDiagnosticsCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useModelDiagnostics(symbol);
  const models = data?.models ?? [];

  return (
    <section className="card-interactive border border-line-1 bg-surface-1 p-3 flex flex-col gap-2.5">
      <h2 className="flex items-center gap-2 font-mono text-[10px] text-ink-3 uppercase tracking-widest">
        <Stethoscope size={12} strokeWidth={1.5} aria-hidden="true" />
        Model Health · how each model fails
      </h2>

      {isLoading ? (
        <p className="text-[10px] text-ink-4 font-mono">Loading…</p>
      ) : models.length === 0 ? (
        <p className="text-[10px] text-ink-4 font-mono">
          No backtest rows yet — diagnostics appear once a backtest is persisted
          for this instrument.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {models.map((m) => (
            <ModelBlock key={m.name} m={m} />
          ))}
        </div>
      )}

      <p className="text-[9px] text-ink-4 font-mono leading-relaxed">
        <span className="text-ink-3">Calib err</span> (reliability) is how far
        stated confidence sits from realized hit-rate — lower is better;{" "}
        <span className="text-ink-3">Sharpness</span> (resolution) is how much
        the model discriminates across its confidence levels — higher is better;{" "}
        <span className="text-ink-3">Dir gap</span> flags a one-sided edge.
        Descriptive, in-sample over the backtest window — not a forward
        forecast.
      </p>
    </section>
  );
}
