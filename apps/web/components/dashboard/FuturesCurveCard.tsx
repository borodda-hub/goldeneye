"use client";

import type { FuturesCurvePoint } from "@/app/(app)/dashboard/types";
import { HelpTip } from "@/components/HelpTip";
import { colors } from "@/lib/colors";
import { LineChart as LineChartIcon } from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  curve: FuturesCurvePoint[];
}

export function FuturesCurveCard({ curve }: Props) {
  return (
    <div className="card-interactive border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
      <div className="flex items-center gap-1.5 px-3 pt-2 pb-1 text-xs text-ink-3 uppercase tracking-widest">
        <LineChartIcon
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        Futures Curve
        <HelpTip k="futuresCurve" className="ml-1" />
      </div>
      {curve.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-1.5 p-3 text-ink-4">
          <LineChartIcon size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-xs font-mono">No curve data.</span>
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={curve}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
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
