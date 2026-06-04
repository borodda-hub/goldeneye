"use client";

import type { Bar, ChartBarsResponse } from "@/app/(app)/chart/types";
import { colors } from "@/lib/colors";
import { useChartBars } from "@/lib/queries";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface Props {
  contractCode: string | null;
  changePct: number | null;
  width?: number;
  height?: number;
}

function toISODate(d: Date): string {
  return d.toISOString().split("T")[0];
}

export function WatchlistSparkline({
  contractCode,
  changePct,
  width = 48,
  height = 18,
}: Props) {
  const today = toISODate(new Date());
  const from = toISODate(new Date(Date.now() - 30 * 86400_000));
  const { data } = useChartBars(
    contractCode ?? "",
    "1d",
    from,
    today,
  );
  const bars: Bar[] = contractCode
    ? ((data as ChartBarsResponse | undefined)?.bars ?? [])
    : [];

  if (bars.length < 2) {
    return (
      <span
        aria-hidden="true"
        style={{ width, height }}
        className="inline-block"
      />
    );
  }

  const isUp = changePct != null ? changePct >= 0 : true;
  const stroke = isUp ? colors.up : colors.down;
  const fill = isUp ? colors.upSoft : colors.downSoft;
  const id = `spk-${contractCode}-${isUp ? "u" : "d"}`;

  return (
    <span
      aria-hidden="true"
      style={{ width, height }}
      className="inline-block shrink-0"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={bars} margin={{ top: 1, right: 0, bottom: 1, left: 0 }}>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
              <stop offset="100%" stopColor={fill} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            dataKey="c"
            type="monotone"
            stroke={stroke}
            strokeWidth={1.2}
            fill={`url(#${id})`}
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </span>
  );
}
