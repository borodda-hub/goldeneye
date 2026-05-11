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
                tick={{ fontSize: 10, fill: "#6b7589" }}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: "#6b7589" }}
                width={40}
                tickFormatter={(v: number) => v.toFixed(3)}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1319",
                  border: "1px solid #2a313e",
                  fontSize: "11px",
                  color: "#e6ebf2",
                }}
                formatter={(v: number) => [v.toFixed(3), "Mid"]}
              />
              <Line
                type="monotone"
                dataKey="mid"
                stroke="#7dd3fc"
                strokeWidth={1.5}
                dot={{ fill: "#7dd3fc", r: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
