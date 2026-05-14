"use client";

import type { Bar, EventMarkerData } from "@/app/(app)/chart/types";
import type { IndicatorSeriesDTO } from "@/lib/api";
import type { IndicatorSpec } from "@/lib/chart/indicatorRegistry";
import { colors } from "@/lib/colors";
import { ColorType, CrosshairMode, createChart } from "lightweight-charts";
import type { UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";

interface Props {
  bars: Bar[];
  eventMarkers: EventMarkerData[];
  /** Active indicator specs — drives color / weight per series. */
  indicators: IndicatorSpec[];
  /** Computed series from /v1/chart/indicators, indexed by `type` order in `indicators`. */
  indicatorSeries: IndicatorSeriesDTO[];
}

/** Convert an ISO timestamp to UTC epoch seconds. Lightweight Charts accepts
 *  UTCTimestamp uniformly across daily and intraday resolutions, so we always
 *  use it. (The old "split-on-T" trick collapsed all intraday bars on the same
 *  day to identical time values, which Lightweight rejects as non-ascending.)
 */
function toUtcEpoch(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

/** Sort by time ascending and drop any duplicates that share a timestamp.
 *  Lightweight Charts panics on either. Defensive — the API should not be
 *  producing dupes, but a single bad bar shouldn't whitescreen the chart. */
function sortedUnique<T extends { time: UTCTimestamp }>(rows: T[]): T[] {
  const sorted = [...rows].sort((a, b) => a.time - b.time);
  const out: T[] = [];
  let prev: number | null = null;
  for (const r of sorted) {
    if (r.time !== prev) {
      out.push(r);
      prev = r.time;
    }
  }
  return out;
}

/** Match server-returned series to a frontend spec. Server returns one
 *  series per request item in order; the response carries `type` + `params`
 *  so we can pair on (type, period, source) even if order drifts. */
function pairSeriesToSpec(
  specs: IndicatorSpec[],
  series: IndicatorSeriesDTO[],
): { spec: IndicatorSpec; series: IndicatorSeriesDTO }[] {
  const out: { spec: IndicatorSpec; series: IndicatorSeriesDTO }[] = [];
  const used = new Set<number>();
  for (const spec of specs) {
    if (!spec.visible) continue;
    const idx = series.findIndex((s, i) => {
      if (used.has(i)) return false;
      const period = (s.params as { period?: number }).period;
      const source = (s.params as { source?: string }).source;
      return (
        s.type === spec.type && period === spec.period && source === spec.source
      );
    });
    if (idx === -1) continue;
    used.add(idx);
    out.push({ spec, series: series[idx] });
  }
  return out;
}

export function PriceChart({
  bars,
  eventMarkers,
  indicators,
  indicatorSeries,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

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
      rightPriceScale: {
        borderColor: colors.line1,
      },
      timeScale: {
        borderColor: colors.line1,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
      },
      handleScroll: true,
      handleScale: true,
    });

    // Candle series
    const candleSeries = chart.addCandlestickSeries({
      upColor: colors.up,
      downColor: colors.down,
      borderUpColor: colors.up,
      borderDownColor: colors.down,
      wickUpColor: colors.up,
      wickDownColor: colors.down,
    });

    const candleData = sortedUnique(
      bars.map((b) => ({
        time: toUtcEpoch(b.ts),
        open: b.o,
        high: b.h,
        low: b.l,
        close: b.c,
      })),
    );
    candleSeries.setData(
      candleData as Parameters<typeof candleSeries.setData>[0],
    );

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      color: colors.line1,
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    const volumeData = sortedUnique(
      bars.map((b) => ({
        time: toUtcEpoch(b.ts),
        value: b.v,
        color: b.c >= b.o ? colors.upSoft : colors.downSoft,
      })),
    );
    volumeSeries.setData(
      volumeData as Parameters<typeof volumeSeries.setData>[0],
    );

    // Indicator overlays — one LineSeries per visible spec
    for (const { spec, series } of pairSeriesToSpec(
      indicators,
      indicatorSeries,
    )) {
      const line = chart.addLineSeries({
        color: spec.color,
        lineWidth: spec.weight,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const points = series.points
        .filter((p) => p.v !== null)
        .map((p) => ({
          time: toUtcEpoch(p.t),
          value: p.v as number,
        }));
      line.setData(sortedUnique(points) as Parameters<typeof line.setData>[0]);
    }

    // Event markers
    if (eventMarkers.length > 0) {
      const markers = sortedUnique(
        eventMarkers.map((m) => ({
          time: toUtcEpoch(m.ts),
          position: "aboveBar" as const,
          color: colors.accent,
          shape: "circle" as const,
          text:
            m.kind === "eia_storage"
              ? "EIA"
              : m.label.substring(0, 3).toUpperCase(),
          size: 1,
        })),
      );
      candleSeries.setMarkers(
        markers as Parameters<typeof candleSeries.setMarkers>[0],
      );
    }

    chart.timeScale().fitContent();

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        chart.resize(entry.contentRect.width, entry.contentRect.height);
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [bars, eventMarkers, indicators, indicatorSeries]);

  return <div ref={containerRef} className="w-full h-full" />;
}
