"use client";

import type { SeasonalityResponse } from "@/lib/api";
import { colors } from "@/lib/colors";
import {
  ColorType,
  CrosshairMode,
  LineSeries,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

/** Map an "MM-DD" to a fixed reference (leap) year so every calendar year
 *  aligns on one Jan→Dec axis. 2000 is a leap year so 02-29 stays valid. */
function mdToEpoch(md: string): UTCTimestamp {
  return Math.floor(
    new Date(`2000-${md}T00:00:00Z`).getTime() / 1000,
  ) as UTCTimestamp;
}

function lerpHex(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => Number.parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => Number.parseInt(b.slice(i, i + 2), 16));
  return `#${pa
    .map((v, i) =>
      Math.round(v + (pb[i] - v) * t)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
}

function sortedUnique(
  pts: { time: UTCTimestamp; value: number }[],
): { time: UTCTimestamp; value: number }[] {
  const sorted = [...pts].sort((x, y) => x.time - y.time);
  const out: typeof sorted = [];
  let prev: number | null = null;
  for (const p of sorted) {
    if (Number.isFinite(p.value) && p.time !== prev) {
      out.push(p);
      prev = p.time;
    }
  }
  return out;
}

export function SeasonalityChart({ data }: { data: SeasonalityResponse }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || data.years.length === 0) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.bg },
        textColor: colors.ink2,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: colors.line1 },
        horzLines: { color: colors.line1 },
      },
      rightPriceScale: { borderColor: colors.line1 },
      timeScale: {
        borderColor: colors.line1,
        timeVisible: false,
        secondsVisible: false,
      },
      crosshair: { mode: CrosshairMode.Magnet },
    });

    const n = data.years.length;
    data.years.forEach((yr, i) => {
      const t = n > 1 ? i / (n - 1) : 1; // older → newer
      const recent = i === n - 1;
      const series = chart.addSeries(LineSeries, {
        color: recent ? colors.accentBright : lerpHex("#4a4a44", "#c9a35c", t),
        lineWidth: recent ? 2 : 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: String(yr.year),
      });
      series.setData(
        sortedUnique(
          yr.points.map((p) => ({ time: mdToEpoch(p.md), value: p.v })),
        ) as Parameters<typeof series.setData>[0],
      );
    });

    // Cross-year average — a thick muted dashed reference line.
    const avg = chart.addSeries(LineSeries, {
      color: colors.ink2,
      lineWidth: 2,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: "Avg",
    });
    avg.setData(
      sortedUnique(
        data.average.map((p) => ({ time: mdToEpoch(p.md), value: p.v })),
      ) as Parameters<typeof avg.setData>[0],
    );

    chart.timeScale().fitContent();

    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) chart.resize(e.contentRect.width, e.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data]);

  return <div ref={containerRef} className="w-full h-full" />;
}
