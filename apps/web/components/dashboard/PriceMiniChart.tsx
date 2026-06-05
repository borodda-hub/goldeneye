"use client";

import type { ChartBarsResponse } from "@/app/(app)/chart/types";
import { colors } from "@/lib/colors";
import { useChartBars } from "@/lib/queries";
import { useChartColor } from "@/lib/useChartColor";
import { useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartColorSwatch } from "./ChartColorSwatch";
import { SheenGradient } from "./SheenGradient";

interface Props {
  contractCode: string;
  /** Used in the card header so the title isn't always "NG". */
  symbol?: string;
}

type TimeframeKey = "1Y" | "1M" | "5D" | "1D" | "1H";

interface TimeframeSpec {
  /** Backend resolution (matches the YahooDelayedMarketAdapter's _RESOLUTION_MAP keys). */
  resolution: "1m" | "5m" | "15m" | "1h" | "1d";
  /** How many days back from today to request. 0 = today only. */
  rangeDays: number;
  /** Tooltip price/time formatter granularity. */
  showTime: boolean;
  /** Label rendered in the card header. */
  label: string;
}

const TIMEFRAMES: Record<TimeframeKey, TimeframeSpec> = {
  "1Y": {
    resolution: "1d",
    rangeDays: 365,
    showTime: false,
    label: "1Y Daily",
  },
  "1M": { resolution: "1d", rangeDays: 30, showTime: false, label: "1M Daily" },
  "5D": { resolution: "15m", rangeDays: 5, showTime: true, label: "5D 15m" },
  "1D": { resolution: "5m", rangeDays: 0, showTime: true, label: "1D 5m" },
  "1H": { resolution: "1m", rangeDays: 0, showTime: true, label: "1H 1m" },
};

const TIMEFRAME_ORDER: TimeframeKey[] = ["1Y", "1M", "5D", "1D", "1H"];

function toISODate(d: Date): string {
  return d.toISOString().split("T")[0];
}

function formatTooltipTs(iso: string, showTime: boolean): string {
  try {
    const d = new Date(iso);
    if (!showTime) {
      return d.toISOString().split("T")[0];
    }
    const date = d.toISOString().split("T")[0];
    const h = d.getUTCHours().toString().padStart(2, "0");
    const m = d.getUTCMinutes().toString().padStart(2, "0");
    return `${date} ${h}:${m}`;
  } catch {
    return iso;
  }
}

/** Compact volume: 1.2K / 3.4M / 5.6B. */
function formatVolume(v: number): string {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(2)}K`;
  return v.toFixed(0);
}

/** Compact x-axis tick: MM-DD for daily ranges, HH:MM for intraday. */
function formatAxisTs(iso: string, showTime: boolean): string {
  try {
    const d = new Date(iso);
    if (!showTime) {
      return d.toISOString().slice(5, 10);
    }
    const h = d.getUTCHours().toString().padStart(2, "0");
    const m = d.getUTCMinutes().toString().padStart(2, "0");
    return `${h}:${m}`;
  } catch {
    return iso;
  }
}

export function PriceMiniChart({ contractCode, symbol = "NG" }: Props) {
  const [timeframe, setTimeframe] = useState<TimeframeKey>("1M");
  const [chartColor, setChartColor] = useChartColor();
  const spec = TIMEFRAMES[timeframe];

  const today = toISODate(new Date());
  const from = toISODate(new Date(Date.now() - spec.rangeDays * 86400_000));

  const { data, isLoading } = useChartBars(
    contractCode,
    spec.resolution,
    from,
    today,
  );
  const chartData = (data as ChartBarsResponse | undefined)?.bars ?? [];

  // O/H/L/C/V across the visible window — the chart's own stats, not the
  // daily front-month change.
  const ohlcv = chartData.length
    ? {
        o: chartData[0].o,
        h: chartData.reduce((m, b) => (b.h > m ? b.h : m), chartData[0].h),
        l: chartData.reduce((m, b) => (b.l < m ? b.l : m), chartData[0].l),
        c: chartData[chartData.length - 1].c,
        v: chartData.reduce((s, b) => s + b.v, 0),
      }
    : null;

  return (
    <div
      className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full"
      data-testid="price-mini-chart"
    >
      <div className="flex items-center justify-between gap-3 px-3 pt-2 pb-1">
        <span className="text-xs text-ink-3 uppercase tracking-widest">
          {symbol} · {spec.label}
        </span>
        <div className="flex items-center gap-3">
          <ChartColorSwatch value={chartColor.key} onChange={setChartColor} />
          <div
            className="flex items-center gap-1"
            role="tablist"
            aria-label="Timeframe"
          >
            {TIMEFRAME_ORDER.map((key) => {
              const active = key === timeframe;
              return (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setTimeframe(key)}
                  className={`font-mono text-[10px] px-1.5 py-0.5 rounded-sm transition-colors ${
                    active
                      ? "bg-surface-2 text-ink-1"
                      : "text-ink-4 hover:text-ink-2 hover:bg-surface-2/50"
                  }`}
                >
                  {key}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {ohlcv && (
        <div
          className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-3 pb-1 font-mono text-[11px] tabular-nums"
          aria-label="Range OHLCV"
        >
          <span className="text-ink-3">
            O <span className="text-ink-1">{ohlcv.o.toFixed(3)}</span>
          </span>
          <span className="text-ink-3">
            H <span className="text-up">{ohlcv.h.toFixed(3)}</span>
          </span>
          <span className="text-ink-3">
            L <span className="text-down">{ohlcv.l.toFixed(3)}</span>
          </span>
          <span className="text-ink-3">
            C <span className="text-ink-1">{ohlcv.c.toFixed(3)}</span>
          </span>
          <span className="text-ink-3">
            V <span className="text-ink-2">{formatVolume(ohlcv.v)}</span>
          </span>
        </div>
      )}

      {isLoading || chartData.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-ink-4 text-xs font-mono">
          {isLoading ? "Loading…" : "No data for this range."}
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <XAxis
                dataKey="ts"
                tick={{ fontSize: 10, fill: colors.ink3 }}
                tickFormatter={(v: string) => formatAxisTs(v, spec.showTime)}
                tickLine={{ stroke: colors.line1 }}
                axisLine={{ stroke: colors.line1 }}
                minTickGap={40}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: colors.ink3 }}
                tickLine={{ stroke: colors.line1 }}
                axisLine={{ stroke: colors.line1 }}
                width={52}
                tickFormatter={(v: number) => v.toFixed(3)}
              />
              <Tooltip
                contentStyle={{
                  background: colors.surface1,
                  border: `1px solid ${colors.line1}`,
                  fontSize: "11px",
                  color: colors.ink1,
                }}
                labelFormatter={(label: string) =>
                  formatTooltipTs(label, spec.showTime)
                }
                formatter={(v: number) => [v.toFixed(3), "Close"]}
              />
              <Area
                dataKey="c"
                type="monotone"
                stroke={chartColor.stroke}
                strokeWidth={1.5}
                fill="url(#price-mini-fill)"
                dot={false}
              />
              <defs>
                {/* Soft vertical fade in the stroke color: a gentle glow under
                    the line at the top, fully translucent at the bottom. */}
                <linearGradient
                  id="price-mini-fill"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor={chartColor.stroke}
                    stopOpacity={0.28}
                  />
                  <stop
                    offset="100%"
                    stopColor={chartColor.stroke}
                    stopOpacity={0}
                  />
                </linearGradient>
                <SheenGradient
                  id="sheen-price-mini"
                  color={chartColor.stroke}
                  durationSec={8}
                  peakOpacity={0.14}
                />
              </defs>
              {/* Overlay area: same shape, sheen fill, kept out of the
                  tooltip so it doesn't duplicate the Close row. */}
              <Area
                dataKey="c"
                type="monotone"
                stroke="none"
                fill="url(#sheen-price-mini)"
                isAnimationActive={false}
                dot={false}
                activeDot={false}
                tooltipType="none"
                legendType="none"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
