"use client";

import type { EquityCurveResponse, EquityPoint } from "@/app/(app)/paper/types";
import { colors } from "@/lib/colors";
import { usePaperEquityCurve } from "@/lib/queries";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { SheenGradient } from "./SheenGradient";

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
}

function fmtUsd(v: number, withSign = false): string {
  const abs = Math.abs(v);
  const formatted = abs.toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
  if (!withSign) return `$${formatted}`;
  return v >= 0 ? `+$${formatted}` : `-$${formatted}`;
}

export function PaperEquityCard() {
  const since = isoDaysAgo(30);
  const { data } = usePaperEquityCurve(since);
  const series: EquityPoint[] =
    (data as EquityCurveResponse | undefined)?.series ?? [];

  const last = series.length ? series[series.length - 1].equity : null;
  const prev = series.length > 1 ? series[series.length - 2].equity : null;
  const dayChange = last !== null && prev !== null ? last - prev : null;
  const dayPct =
    dayChange !== null && prev !== null && prev !== 0 ? dayChange / prev : null;

  const isUp = dayChange !== null && dayChange >= 0;
  const tone =
    dayChange === null
      ? "text-flat"
      : dayChange > 0
        ? "text-up"
        : dayChange < 0
          ? "text-down"
          : "text-flat";
  const arrow = dayChange === null || dayChange === 0 ? "·" : isUp ? "▲" : "▼";

  return (
    <div
      className="border border-line-1 bg-surface-1 rounded-md px-3 py-2.5 flex flex-col gap-1"
      aria-label="Paper equity"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          Equity · Paper
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {series.length ? `${series.length}d` : "—"}
        </span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-3xl tabular-nums text-ink-1 leading-none">
          {last !== null ? fmtUsd(last) : "—"}
        </span>
      </div>
      <div
        className={`flex items-baseline gap-2 font-mono text-xs tabular-nums ${tone}`}
      >
        <span>{arrow}</span>
        <span>{dayChange !== null ? fmtUsd(dayChange, true) : "—"}</span>
        <span className="text-[11px]">
          ({dayPct !== null ? `${(dayPct * 100).toFixed(2)}%` : "—"})
        </span>
        <span className="ml-auto text-[10px] text-ink-4 uppercase tracking-widest">
          day
        </span>
      </div>
      {series.length > 1 && (
        <div className="h-10 -mx-1 mt-1" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={series}
              margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
            >
              <defs>
                <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor={isUp ? colors.up : colors.down}
                    stopOpacity={0.35}
                  />
                  <stop
                    offset="100%"
                    stopColor={isUp ? colors.up : colors.down}
                    stopOpacity={0}
                  />
                </linearGradient>
                <SheenGradient
                  id="eq-sheen"
                  color={isUp ? colors.up : colors.down}
                  durationSec={11}
                  peakOpacity={0.22}
                />
              </defs>
              <Area
                dataKey="equity"
                type="monotone"
                stroke={isUp ? colors.up : colors.down}
                strokeWidth={1.2}
                fill="url(#eq-grad)"
                isAnimationActive={false}
                dot={false}
              />
              <Area
                dataKey="equity"
                type="monotone"
                stroke="none"
                fill="url(#eq-sheen)"
                isAnimationActive={false}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
