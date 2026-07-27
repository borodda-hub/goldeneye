/**
 * Vol vs Market (Phase D1b) — the implied-vs-forecast comparison card.
 *
 * The claim split (pre-registered in docs/PHASE_D1_PLAN.md §D1b):
 * - Layer 1 (a fact): our 1-month vol forecast vs the market's implied
 *   index, plus the spread's walk-forward percentile. Gated LIVE by the
 *   ship gate (our forecast must not be worse than the market's own as an
 *   RV predictor) — a failing pair renders the honest note instead.
 * - Layer 2 (tested, not crowned): per-tercile historical premium stats
 *   with n and SE. NO signal chip, NO rich/cheap verdict word — the
 *   percentile gauge conveys position, not pronouncement.
 *
 * Renders nothing for unsupported symbols (no free implied-vol index —
 * e.g. NG) and nothing until the endpoint answers (house convention).
 */
"use client";

import { HelpTip } from "@/components/HelpTip";
import type { VolPremiumTercile } from "@/lib/api";
import { useVolPremium } from "@/lib/queries";
import { Scale } from "lucide-react";
import Link from "next/link";

function pct(x: number): string {
  return `${(x * 100).toFixed(1)}%`;
}

function TercileNote({
  label,
  t,
  active,
}: {
  label: string;
  t: VolPremiumTercile | null;
  active: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-0.5 border-t pt-1.5 ${
        active ? "border-accent/60" : "border-line-1"
      }`}
    >
      <span
        className={`font-mono text-[8px] uppercase tracking-wide ${
          active ? "text-accent" : "text-ink-4"
        }`}
      >
        {label}
        {active ? " · now" : ""}
      </span>
      {t ? (
        <span className="font-mono text-[10px] tabular-nums text-ink-3">
          {(t.mean * 100).toFixed(1)}±{(t.se * 100).toFixed(1)} pts
          <span className="text-ink-4"> · n={t.n}</span>
        </span>
      ) : (
        <span className="font-mono text-[10px] text-ink-4">—</span>
      )}
    </div>
  );
}

export function VolPremiumCard({ symbol }: { symbol: string }) {
  const { data } = useVolPremium(symbol);

  // Unsupported (no free IV index) or not yet answered → no card at all:
  // absence is the honest degradation; nothing is ever fabricated.
  if (!data || !data.supported || !data.current) return null;

  const { current, pair, terciles, g1, timing_tested, sample } = data;

  return (
    <div className="card-interactive rounded-md border border-line-1 bg-surface-1 px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          <Scale
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Vol vs Market
          <HelpTip k="volPremium" className="ml-1" />
        </span>
        <span className="rounded-sm border border-line-2 bg-surface-2 px-1 py-px font-mono text-[8px] normal-case tracking-normal text-ink-3">
          {pair?.underlying} / {pair?.iv_index}
        </span>
      </div>

      {data.ship_gate ? (
        <>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <span className="font-mono text-lg tabular-nums text-ink-1">
              {pct(current.sigma_f)}
              <span className="ml-1 text-[10px] text-ink-4">
                our 1m forecast
              </span>
            </span>
            <span className="font-mono text-lg tabular-nums text-ink-1">
              {pct(current.iv)}
              <span className="ml-1 text-[10px] text-ink-4">
                market implied
              </span>
            </span>
            <span className="font-mono text-sm tabular-nums text-ink-2">
              {current.spread >= 0 ? "+" : ""}
              {pct(current.spread)}
              <span className="ml-1 text-[10px] text-ink-4">spread</span>
            </span>
          </div>

          {/* Percentile gauge — position, not pronouncement. */}
          <div className="mt-3">
            <div className="relative h-2 w-full overflow-hidden rounded-sm border border-line-1">
              <div className="absolute inset-y-0 left-0 w-1/3 bg-surface-2" />
              <div className="absolute inset-y-0 left-1/3 w-1/3 bg-surface-3" />
              <div className="absolute inset-y-0 left-2/3 w-1/3 bg-surface-2" />
              <div
                className="absolute inset-y-0 w-[3px] bg-accent"
                style={{
                  left: `calc(${Math.min(99, Math.max(1, current.percentile))}% - 1px)`,
                }}
                aria-label={`spread percentile ${Math.round(current.percentile)}`}
              />
            </div>
            <div className="mt-1 flex justify-between font-mono text-[8px] uppercase tracking-wide text-ink-4">
              <span>forecast below market</span>
              <span>
                {Math.round(current.percentile)}th pct of walk-forward history
              </span>
              <span>forecast above market</span>
            </div>
          </div>

          {/* Layer 2 — conditional context: tested, not crowned. */}
          {terciles ? (
            <div className="mt-3 grid grid-cols-3 gap-3">
              <TercileNote
                label="low tercile"
                t={terciles.low}
                active={current.bucket === "low"}
              />
              <TercileNote
                label="mid tercile"
                t={terciles.mid}
                active={current.bucket === "mid"}
              />
              <TercileNote
                label="high tercile"
                t={terciles.high}
                active={current.bucket === "high"}
              />
            </div>
          ) : null}
          <p className="mt-1.5 font-mono text-[9px] leading-relaxed text-ink-4">
            Historical mean 1m premium (implied − realized) per spread tercile,
            walk-forward{sample ? ` · n_eff≈${sample.n_eff}` : ""}.{" "}
            {timing_tested
              ? "Timing is tested, not crowned"
              : "This pair FAILED the timing test"}{" "}
            —{" "}
            <Link
              href="/validation"
              className="text-accent hover:text-accent-bright"
            >
              see the verdict →
            </Link>
          </p>
        </>
      ) : (
        <p className="mt-2 text-[11px] leading-relaxed text-ink-3">
          The live ship gate is not met for this pair right now — our forecast
          is not currently competitive with the market&apos;s own implied
          number, so no comparison is shown. That check runs on every request;{" "}
          <Link
            href="/validation"
            className="text-accent hover:text-accent-bright"
          >
            how we validate →
          </Link>
        </p>
      )}

      <p className="mt-2 border-t border-line-1 pt-1.5 font-mono text-[9px] text-ink-4">
        har_log estimator · 30-day tenor matched · comparison is measured, not
        predicted
        {g1
          ? ` · live MAE ours ${(g1.mae_forecast * 100).toFixed(1)} vs market ${(g1.mae_iv * 100).toFixed(1)}`
          : ""}
      </p>
    </div>
  );
}
