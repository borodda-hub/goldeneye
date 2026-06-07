"use client";

import type { InstrumentRow } from "@/lib/api";
import { useInstruments, useRangeForecast } from "@/lib/queries";

interface Props {
  symbol: string;
}

/**
 * Expected Range strip (Phase 30a) — the platform's one *calibrated* forecast.
 *
 * Sits below the directional hero deliberately: direction has no proven out-of-sample
 * edge (Phase 26), but the volatility band does — its 80% coverage is measured
 * walk-forward (~0.80 on the seeded series). Makes NO directional claim. Compact,
 * auto-height (never h-full — a prior version filled the screen).
 */
export function ExpectedRange({ symbol }: Props) {
  const { data } = useRangeForecast(symbol, "1w");
  const { data: instruments } = useInstruments();

  // Graceful: render nothing until the (additive, safety-wrapped) endpoint answers,
  // so a not-yet-deployed backend can never break the page.
  if (!data) return null;

  const { range, coverage } = data;
  const cov80 = coverage?.cov80 ?? null;
  const nEff = coverage?.n_eff ?? null;
  const corr = data.forward_vol_corr ?? null;

  const spot =
    (instruments?.instruments as InstrumentRow[] | undefined)?.find(
      (r) => r.symbol === symbol,
    )?.quote.last_price ?? null;

  const dp = spot != null && spot < 20 ? 3 : 2;
  const lo = spot != null ? spot * (1 + range.band80_low_pct) : null;
  const hi = spot != null ? spot * (1 + range.band80_high_pct) : null;
  const pct = (range.band80_high_pct * 100).toFixed(1);
  const dailyVol = (range.sigma_daily * 100).toFixed(2);

  return (
    <div className="card-interactive border border-line-1 bg-surface-1 px-5 py-4">
      <div className="flex items-center gap-x-8 gap-y-3 flex-wrap">
        {/* The band — the calibrated headline */}
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Expected range · 1 week · 80% band
          </span>
          <span className="font-mono font-medium tabular-nums text-2xl leading-none text-ink-1">
            {lo != null && hi != null ? (
              <>
                ${lo.toFixed(dp)} <span className="text-ink-4">–</span> $
                {hi.toFixed(dp)}
              </>
            ) : (
              <span className="text-ink-2">±{pct}%</span>
            )}
          </span>
          {lo != null && (
            <span className="font-mono text-[10px] text-ink-4 tabular-nums mt-0.5">
              ±{pct}% around spot
            </span>
          )}
        </div>

        {/* Daily vol */}
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Daily volatility
          </span>
          <span className="font-mono tabular-nums text-lg leading-none text-ink-2">
            {dailyVol}%
          </span>
        </div>

        {/* Live calibration readout — the honest track record */}
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Walk-forward coverage
          </span>
          {cov80 != null ? (
            <span className="font-mono tabular-nums text-lg leading-none text-up">
              {(cov80 * 100).toFixed(0)}%
            </span>
          ) : (
            <span className="font-mono text-sm text-ink-4">—</span>
          )}
          <span className="font-mono text-[10px] text-ink-4 tabular-nums mt-0.5">
            of the 80% band{nEff ? ` · ${nEff} windows` : ""}
          </span>
        </div>

        {/* Forward-vol correlation — the evidence it carries information */}
        {corr != null && (
          <div className="flex flex-col gap-0.5">
            <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
              Forward-vol signal
            </span>
            <span className="font-mono tabular-nums text-lg leading-none text-up">
              {corr >= 0 ? "+" : ""}
              {corr.toFixed(2)}
            </span>
            <span className="font-mono text-[10px] text-ink-4 mt-0.5">
              corr w/ realized vol
            </span>
          </div>
        )}
      </div>

      <p className="mt-3 pt-3 border-t border-line-1 font-mono text-[11px] leading-snug text-ink-3">
        <span className="text-up">ⓘ</span> Range only — no directional (up/down)
        claim. The 80% band is the calibrated surface (coverage measured
        walk-forward, not guaranteed); the central vol level is not a reliable
        point forecast. This is the measured edge the directional call above
        lacks.
      </p>
    </div>
  );
}
