"use client";

import { useBacktestSummary, useRunBacktest } from "@/lib/queries";

interface ModelSummary {
  name: string;
  n: number;
  scored: number;
  hits: number;
  misses: number;
  indeterminate: number;
  pending: number;
  neutral: number;
  hit_rate: number;
  last_generated_at: string | null;
  from_date: string | null;
  to_date: string | null;
}

interface SummaryResponse {
  models: ModelSummary[];
  horizon: string;
  symbol: string;
}

// Stable ordering so models don't reshuffle when one finishes a re-run.
const MODEL_ORDER = [
  "moving_average_directional",
  "prophet_trend",
  "volatility_regime",
  "xgboost_placeholder",
] as const;

const MODEL_LABEL: Record<string, string> = {
  moving_average_directional: "SMA Cross",
  prophet_trend: "Prophet Trend",
  volatility_regime: "Vol Regime",
  xgboost_placeholder: "XGBoost",
};

function HitRateBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  // Color the bar by where it sits vs 50% (coin flip baseline).
  const color = pct >= 55 ? "bg-up" : pct >= 45 ? "bg-conf-medium" : "bg-down";
  return (
    <div
      className="relative w-32 h-2 bg-surface-2 rounded-sm overflow-hidden"
      aria-label={`hit rate ${pct.toFixed(1)} percent`}
    >
      <div
        className={`absolute left-0 top-0 h-full ${color}`}
        style={{ width: `${pct}%` }}
      />
      {/* 50% reference line */}
      <div className="absolute top-0 left-1/2 w-px h-full bg-line-2/60" />
    </div>
  );
}

function ModelRow({
  model,
  onRun,
  isRunning,
}: {
  model: ModelSummary | undefined;
  onRun: () => void;
  isRunning: boolean;
}) {
  if (!model || model.scored === 0) {
    return (
      <div className="flex items-center gap-3 px-3 py-2 border-b border-line-1/60 text-xs">
        <span className="font-mono text-ink-2 w-40 truncate">
          {MODEL_LABEL[model?.name ?? ""] ?? "—"}
        </span>
        <span className="flex-1 font-mono text-ink-4 italic">
          {model
            ? "No scored forecasts yet — model returned only neutral / pending."
            : "Not run yet."}
        </span>
        <button
          type="button"
          onClick={onRun}
          disabled={isRunning}
          className="font-mono text-[10px] uppercase tracking-widest border border-line-1 px-2 py-0.5 hover:bg-surface-2 disabled:text-ink-4 disabled:cursor-not-allowed"
        >
          {isRunning ? "running…" : "Run"}
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b border-line-1/60 text-xs">
      <span className="font-mono text-ink-2 w-40 truncate">
        {MODEL_LABEL[model.name] ?? model.name}
      </span>
      <HitRateBar value={model.hit_rate} />
      <span className="font-mono tabular-nums text-ink-1 w-14 text-right">
        {(model.hit_rate * 100).toFixed(1)}%
      </span>
      <span className="font-mono tabular-nums text-ink-3 w-24 text-right text-[10px]">
        {model.scored} scored
      </span>
      <span className="font-mono tabular-nums text-ink-4 w-20 text-right text-[10px]">
        {model.hits}H · {model.misses}M
        {model.indeterminate > 0 ? ` · ${model.indeterminate}∅` : ""}
      </span>
      <button
        type="button"
        onClick={onRun}
        disabled={isRunning}
        className="font-mono text-[10px] uppercase tracking-widest border border-line-1 px-2 py-0.5 hover:bg-surface-2 disabled:text-ink-4 disabled:cursor-not-allowed ml-auto"
        aria-label={`Re-run backtest for ${MODEL_LABEL[model.name] ?? model.name}`}
      >
        {isRunning ? "running…" : "Re-run"}
      </button>
    </div>
  );
}

interface BacktestCardProps {
  symbol?: string;
}

export function BacktestCard({ symbol = "NG" }: BacktestCardProps = {}) {
  const { data, isLoading, isError } = useBacktestSummary(symbol, "1d");
  const mutation = useRunBacktest(symbol, "1d");
  const resp = data as SummaryResponse | undefined;
  const modelsByName = new Map<string, ModelSummary>(
    (resp?.models ?? []).map((m) => [m.name, m]),
  );

  // The range comes from whichever model has the widest window — gives
  // viewers a single "this is the backtest window" date pair to read.
  const allFrom = (resp?.models ?? [])
    .map((m) => m.from_date)
    .filter((d): d is string => Boolean(d))
    .sort()[0];
  const allTo = (resp?.models ?? [])
    .map((m) => m.to_date)
    .filter((d): d is string => Boolean(d))
    .sort()
    .at(-1);

  return (
    <div
      className="border border-line-1 rounded-md bg-surface-1 flex flex-col"
      data-testid="backtest-card"
    >
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <span className="text-xs text-ink-3 uppercase tracking-widest">
          Backtest Performance · 1d horizon
        </span>
        {allFrom && allTo ? (
          <span className="font-mono text-[10px] text-ink-4">
            {allFrom} → {allTo}
          </span>
        ) : null}
      </div>

      {isLoading ? (
        <div className="px-3 py-6 text-xs text-ink-4 font-mono text-center">
          Loading backtest summary…
        </div>
      ) : isError ? (
        <div className="px-3 py-6 text-xs text-ink-4 font-mono text-center">
          Summary unavailable.
        </div>
      ) : (resp?.models ?? []).length === 0 ? (
        <div className="px-3 py-6 text-xs text-ink-4 font-mono text-center">
          No backtest rows persisted yet. Run a backtest to populate per-model
          hit-rates.
        </div>
      ) : (
        <div className="flex flex-col">
          {MODEL_ORDER.map((name) => (
            <ModelRow
              key={name}
              model={modelsByName.get(name)}
              isRunning={mutation.isPending && mutation.variables === name}
              onRun={() => mutation.mutate(name)}
            />
          ))}
        </div>
      )}

      <div className="px-3 py-1 text-[10px] font-mono text-ink-4 border-t border-line-1">
        Honest backtest · look-ahead-safe · 50% line = coin-flip baseline
      </div>
    </div>
  );
}
