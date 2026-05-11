"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EquityPoint } from "../../app/(app)/paper/types";

interface Props {
  series: EquityPoint[];
}

const STARTING_EQUITY = 100_000;

export function EquityCurveChart({ series }: Props) {
  const last = series.length > 0 ? series[series.length - 1].equity : STARTING_EQUITY;
  const isUp = last >= STARTING_EQUITY;
  const stroke = isUp ? "#34d399" : "#f87171";

  return (
    <div className="border border-line-1 bg-surface-1 flex flex-col h-full">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-3">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Equity Curve · 90D
        </span>
        <span
          className={`font-mono text-xs tabular-nums ml-auto ${
            isUp ? "text-up" : "text-down"
          }`}
        >
          ${last.toFixed(0)}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        {series.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-ink-4 font-mono">
            No equity data in range.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={series}
              margin={{ top: 8, right: 16, bottom: 4, left: 8 }}
            >
              <CartesianGrid
                stroke="#1f242c"
                strokeDasharray="2 2"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#7a8090" }}
                axisLine={{ stroke: "#2a313e" }}
                tickLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: "#7a8090" }}
                axisLine={{ stroke: "#2a313e" }}
                tickLine={false}
                width={60}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1319",
                  border: "1px solid #2a313e",
                  fontSize: "11px",
                  color: "#e6ebf2",
                }}
                formatter={(v: number) => [`$${v.toFixed(0)}`, "Equity"]}
              />
              <ReferenceLine
                y={STARTING_EQUITY}
                stroke="#7a8090"
                strokeDasharray="3 3"
                ifOverflow="extendDomain"
              />
              <Line
                dataKey="equity"
                type="monotone"
                stroke={stroke}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
