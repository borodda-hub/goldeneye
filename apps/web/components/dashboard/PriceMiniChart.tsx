"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useChartBars } from "@/lib/queries";
import type { VolRegime } from "@/app/(app)/dashboard/types";
import type { ChartBarsResponse } from "@/app/(app)/chart/types";

interface Props {
  volRegime: VolRegime;
  contractCode: string;
}

function toISODate(d: Date): string {
  return d.toISOString().split("T")[0];
}

export function PriceMiniChart({ volRegime, contractCode }: Props) {
  const today = toISODate(new Date());
  const from30dAgo = toISODate(new Date(Date.now() - 30 * 86400_000));

  const { data, isLoading } = useChartBars(contractCode, "1d", from30dAgo, today);
  const chartData = (data as ChartBarsResponse | undefined)?.bars ?? [];

  const isHot = volRegime === "elevated" || volRegime === "crisis";
  const strokeColor = isHot ? "#f87171" : "#34d399";
  const fillColor = isHot ? "#2c1416" : "#0d2820";

  if (isLoading || chartData.length === 0) {
    return (
      <div className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
        <div className="px-3 pt-2 pb-1 text-xs text-ink-3 uppercase tracking-widest">
          NG · 30D Daily
        </div>
        <div className="flex-1 flex items-center justify-center text-ink-4 text-xs font-mono">
          Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
      <div className="px-3 pt-2 pb-1 text-xs text-ink-3 uppercase tracking-widest">
        NG · 30D Daily
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <XAxis dataKey="ts" hide />
            <YAxis domain={["auto", "auto"]} hide />
            <Tooltip
              contentStyle={{
                background: "#0f1319",
                border: "1px solid #2a313e",
                fontSize: "11px",
                color: "#e6ebf2",
              }}
              formatter={(v: number) => [v.toFixed(3), "Close"]}
            />
            <Area
              dataKey="c"
              type="monotone"
              stroke={strokeColor}
              strokeWidth={1.5}
              fill={fillColor}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
