"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FuturesCurvePoint } from "@/app/(app)/dashboard/types";
import { colors } from "@/lib/colors";

interface Props {
  curve: FuturesCurvePoint[];
}

export function FuturesCurveCard({ curve }: Props) {
  return (
    <div className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
      <div className="px-3 pt-2 pb-1 text-xs text-ink-3 uppercase tracking-widest">
        Futures Curve
      </div>
      {curve.length === 0 ? (
        <p className="text-ink-4 text-xs font-mono p-3">No curve data.</p>
      ) : (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={curve} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <XAxis
                dataKey="contract_code"
                tick={{ fontSize: 10, fill: colors.ink3 }}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: colors.ink3 }}
                width={40}
                tickFormatter={(v: number) => v.toFixed(3)}
              />
              <Tooltip
                contentStyle={{
                  background: colors.surface1,
                  border: `1px solid ${colors.line1}`,
                  fontSize: "11px",
                  color: colors.ink1,
                }}
                formatter={(v: number) => [v.toFixed(3), "Mid"]}
              />
              <Line
                type="monotone"
                dataKey="mid"
                stroke={colors.accent}
                strokeWidth={1.5}
                dot={{ fill: colors.accent, r: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
