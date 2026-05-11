"use client";

import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, createChart } from "lightweight-charts";
import type {
  Bar,
  EventMarkerData,
  OverlayPoint,
} from "@/app/(app)/chart/types";

interface Props {
  bars: Bar[];
  overlays: { sma_20: OverlayPoint[]; ema_50: OverlayPoint[] };
  eventMarkers: EventMarkerData[];
  showSMA20: boolean;
  showEMA50: boolean;
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
        background: { type: ColorType.Solid, color: "#0a0d12" },
        textColor: "#a7b0bf",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#2a313e" },
        horzLines: { color: "#2a313e" },
      },
      rightPriceScale: {
        borderColor: "#2a313e",
      },
      timeScale: {
        borderColor: "#2a313e",
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
      upColor: "#34d399",
      downColor: "#f87171",
      borderUpColor: "#34d399",
      borderDownColor: "#f87171",
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    const candleData = bars.map((b) => ({
      time: b.ts.split("T")[0],
      open: b.o,
      high: b.h,
      low: b.l,
      close: b.c,
    }));
    candleSeries.setData(
      candleData as Parameters<typeof candleSeries.setData>[0],
    );

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      color: "#2a313e",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    const volumeData = bars.map((b) => ({
      time: b.ts.split("T")[0],
      value: b.v,
      color: b.c >= b.o ? "#0d2820" : "#2c1416",
    }));
    volumeSeries.setData(
      volumeData as Parameters<typeof volumeSeries.setData>[0],
    );

    // SMA20 overlay
    if (showSMA20 && overlays.sma_20.length > 0) {
      const smaSeries = chart.addLineSeries({
        color: "#7dd3fc",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      smaSeries.setData(
        overlays.sma_20.map((p) => ({
          time: p.ts.split("T")[0],
          value: p.v,
        })) as Parameters<typeof smaSeries.setData>[0],
      );
    }

    // EMA50 overlay
    if (showEMA50 && overlays.ema_50.length > 0) {
      const emaSeries = chart.addLineSeries({
        color: "#fbbf24",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      emaSeries.setData(
        overlays.ema_50.map((p) => ({
          time: p.ts.split("T")[0],
          value: p.v,
        })) as Parameters<typeof emaSeries.setData>[0],
      );
    }

    // Event markers
    if (eventMarkers.length > 0) {
      const markers = eventMarkers.map((m) => ({
        time: m.ts.split("T")[0],
        position: "aboveBar" as const,
        color: "#7dd3fc",
        shape: "circle" as const,
        text:
          m.kind === "eia_storage"
            ? "EIA"
            : m.label.substring(0, 3).toUpperCase(),
        size: 1,
      }));
      markers.sort((a, b) =>
        a.time < b.time ? -1 : a.time > b.time ? 1 : 0,
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
