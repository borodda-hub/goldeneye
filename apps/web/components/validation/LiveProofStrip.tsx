/**
 * Live numbers the page does NOT control (Phase A3) — the self-verification
 * strip. The range-coverage readout and the desk verdicts come from the
 * same live endpoints the rest of the terminal uses; if calibration ever
 * degrades, this page shows it. That asymmetric exposure is the trust
 * argument.
 *
 * Each card renders nothing until its endpoint answers (the ExpectedRange
 * convention), so a partially-deployed backend can never break the page.
 */
"use client";

import { HelpTip } from "@/components/HelpTip";
import type { ValidationResponse } from "@/lib/api";
import { useDeskCalibration, useRangeForecast } from "@/lib/queries";
import { Activity, Archive, Scale } from "lucide-react";

function Card({
  icon: Icon,
  title,
  children,
  help,
}: {
  icon: typeof Activity;
  title: string;
  children: React.ReactNode;
  help?: "walkForward" | "nEff";
}) {
  return (
    <div className="card-interactive rounded-md border border-line-1 bg-surface-1 p-3">
      <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent">
        <Icon
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        {title}
        {help ? <HelpTip k={help} className="ml-1" /> : null}
      </span>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function Num({ v, suffix }: { v: string; suffix?: string }) {
  return (
    <span className="font-mono text-lg tabular-nums text-ink-1">
      {v}
      {suffix ? (
        <span className="ml-0.5 text-[10px] text-ink-4">{suffix}</span>
      ) : null}
    </span>
  );
}

export function LiveProofStrip({ data }: { data: ValidationResponse | null }) {
  const { data: range } = useRangeForecast("NG", "1w", "har_log");
  const { data: desk, isError: deskError } = useDeskCalibration();

  const cov = range?.coverage;
  const verdictCounts =
    desk?.analysts?.reduce(
      (acc: Record<string, number>, a: { verdict?: string }) => {
        const v = a.verdict ?? "insufficient";
        acc[v] = (acc[v] ?? 0) + 1;
        return acc;
      },
      {},
    ) ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card
        icon={Activity}
        title="Interval calibration · live"
        help="walkForward"
      >
        {cov ? (
          <>
            <div className="flex items-baseline gap-4">
              <Num
                v={`${Math.round((cov.cov80 ?? 0) * 100)}%`}
                suffix="of 80% band"
              />
              {typeof range?.forward_vol_corr === "number" ? (
                <Num
                  v={range.forward_vol_corr.toFixed(2)}
                  suffix="fwd-vol corr"
                />
              ) : null}
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-ink-4">
              Measured walk-forward on real delayed prices ({cov.n_eff}{" "}
              non-overlapping windows) — the number the range engine must keep
              earning. Not guaranteed to persist; that is why it is measured
              live.
            </p>
          </>
        ) : (
          <p className="font-mono text-[10px] text-ink-4">Loading…</p>
        )}
      </Card>
      <Card icon={Scale} title="Refuses to crown noise">
        {verdictCounts ? (
          <>
            <div className="flex items-baseline gap-4">
              <Num v={String(verdictCounts.luck ?? 0)} suffix="luck" />
              <Num v={String(verdictCounts.skill ?? 0)} suffix="skill" />
              <Num
                v={String(verdictCounts.insufficient ?? 0)}
                suffix="insufficient"
              />
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-ink-4">
              Wilson 95% verdicts on the desk leaderboard. Blind sample desks
              reading “luck” is the point: the scorer cannot be flattered by a
              hot streak.
            </p>
          </>
        ) : deskError ? (
          <p className="text-[10px] leading-relaxed text-ink-4">
            Live verdicts are account-gated on this deployment. The method is
            the same everywhere: a Wilson 95% interval against the coin-flip
            baseline — “skill” only when the lower bound clears chance.
          </p>
        ) : (
          <p className="font-mono text-[10px] text-ink-4">Loading…</p>
        )}
      </Card>
      <Card icon={Archive} title="Archives accumulating">
        {data ? (
          <>
            <div className="flex items-baseline gap-4">
              <Num
                v={String(data.archives.weather_vintage_days)}
                suffix="weather days"
              />
              <Num
                v={String(data.archives.curve_vintage_days)}
                suffix="curve days"
              />
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-ink-4">
              What we can’t test yet, and the day we can: weather features
              re-enter validation after ~180 archived days spanning a winter;
              the cross-sectional carry test at ~2 years of curve snapshots.
            </p>
          </>
        ) : (
          <p className="font-mono text-[10px] text-ink-4">Loading…</p>
        )}
      </Card>
    </div>
  );
}
