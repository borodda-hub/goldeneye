"use client";

import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, createChart } from "lightweight-charts";
import type { UTCTimestamp } from "lightweight-charts";
import type {
  Bar,
  EventMarkerData,
  OverlayPoint,
} from "@/app/(app)/chart/types";
import { colors } from "@/lib/colors";

interface Props {
  bars: Bar[];
  overlays: { sma_20: OverlayPoint[]; ema_50: OverlayPoint[] };
  eventMarkers: EventMarkerData[];
  showSMA20: boolean;
  showEMA50: boolean;
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

export function PriceChart({
  bars,
  overlays,
  eventMarkers,
  showSMA20,
  showEMA50,
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

    // SMA20 overlay
    if (showSMA20 && overlays.sma_20.length > 0) {
      const smaSeries = chart.addLineSeries({
        color: colors.accent,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      smaSeries.setData(
        sortedUnique(
          overlays.sma_20.map((p) => ({
            time: toUtcEpoch(p.ts),
            value: p.v,
          })),
        ) as Parameters<typeof smaSeries.setData>[0],
      );
    }

    // EMA50 overlay
    if (showEMA50 && overlays.ema_50.length > 0) {
      const emaSeries = chart.addLineSeries({
        color: colors.amber,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      emaSeries.setData(
        sortedUnique(
          overlays.ema_50.map((p) => ({
            time: toUtcEpoch(p.ts),
            value: p.v,
          })),
        ) as Parameters<typeof emaSeries.setData>[0],
      );
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
  }, [bars, overlays, eventMarkers, showSMA20, showEMA50]);

  return <div ref={containerRef} className="w-full h-full" />;
}
