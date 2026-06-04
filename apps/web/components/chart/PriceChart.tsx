"use client";

import type {
  Bar,
  ChartApi,
  ChartType,
  CurvePoint,
  EventMarkerData,
} from "@/app/(app)/chart/types";
import type { CandlestickPattern, IndicatorSeriesDTO } from "@/lib/api";
import type { IndicatorSpec } from "@/lib/chart/indicatorRegistry";
import { colors } from "@/lib/colors";
import {
  AreaSeries,
  BarSeries,
  BaselineSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  LineSeries,
  PriceScaleMode,
  type SeriesType,
  type UTCTimestamp,
  createChart,
  createSeriesMarkers,
} from "lightweight-charts";
import { type MutableRefObject, useEffect, useRef } from "react";

interface Props {
  bars: Bar[];
  eventMarkers: EventMarkerData[];
  indicators: IndicatorSpec[];
  indicatorSeries: IndicatorSeriesDTO[];
  chartType: ChartType;
  logScale: boolean;
  showCurve: boolean;
  curve: CurvePoint[];
  /** Candlestick-pattern detections to mark below the bars. */
  patterns: CandlestickPattern[];
  /** Latest live price (from the front-month tick channel); updates the last bar. */
  livePrice: number | null;
  /** Populated with an imperative handle (screenshot) once the chart exists. */
  apiRef?: MutableRefObject<ChartApi | null>;
}

function toUtcEpoch(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

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

/** Color per indicator line role. Single-line roles use the spec's color;
 *  secondary lines (signal/hist/mid/%D) get muted/contrast tokens. */
function roleColor(base: string, role: string): string {
  switch (role) {
    case "signal":
      return colors.down;
    case "hist":
      return colors.line2;
    case "mid":
      return colors.ink3;
    case "d":
      return colors.amber;
    default:
      return base; // line, rsi, adx, macd, k, upper, lower
  }
}

type OhlcPoint = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

/** Heikin-Ashi transform — smoothed OHLC for trend clarity. */
function heikinAshi(bars: Bar[]): OhlcPoint[] {
  const out: OhlcPoint[] = [];
  let prevOpen: number | null = null;
  let prevClose: number | null = null;
  for (const b of bars) {
    const haClose: number = (b.o + b.h + b.l + b.c) / 4;
    const haOpen: number =
      prevOpen === null || prevClose === null
        ? (b.o + b.c) / 2
        : (prevOpen + prevClose) / 2;
    out.push({
      time: toUtcEpoch(b.ts),
      open: haOpen,
      high: Math.max(b.h, haOpen, haClose),
      low: Math.min(b.l, haOpen, haClose),
      close: haClose,
    });
    prevOpen = haOpen;
    prevClose = haClose;
  }
  return out;
}

/** Whether a chart type plots full OHLC candles/bars vs a single value line. */
function isOhlcType(t: ChartType): boolean {
  return t === "candlestick" || t === "bars" || t === "heikin-ashi";
}

export function PriceChart({
  bars,
  eventMarkers,
  indicators,
  indicatorSeries,
  chartType,
  logScale,
  showCurve,
  curve,
  patterns,
  livePrice,
  apiRef,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const lastBarRef = useRef<OhlcPoint | null>(null);

  // Build / rebuild the chart on any structural or data change. Live ticks are
  // handled in a separate effect so they don't recreate the chart.
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
        mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      },
      timeScale: {
        borderColor: colors.line1,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: { mode: CrosshairMode.Magnet },
      handleScroll: true,
      handleScale: true,
    });
    chartRef.current = chart;

    // ── Price series (per chart type) ──────────────────────────────────────
    let priceSeries: ISeriesApi<SeriesType>;
    const ohlc = isOhlcType(chartType);
    if (chartType === "line") {
      priceSeries = chart.addSeries(LineSeries, {
        color: colors.accent,
        lineWidth: 2,
      });
    } else if (chartType === "area") {
      priceSeries = chart.addSeries(AreaSeries, {
        lineColor: colors.accent,
        topColor: colors.accentSoft,
        bottomColor: colors.bg,
        lineWidth: 2,
      });
    } else if (chartType === "baseline") {
      const base = bars[0]?.c ?? 0;
      priceSeries = chart.addSeries(BaselineSeries, {
        baseValue: { type: "price", price: base },
        topLineColor: colors.up,
        bottomLineColor: colors.down,
      });
    } else if (chartType === "bars") {
      priceSeries = chart.addSeries(BarSeries, {
        upColor: colors.up,
        downColor: colors.down,
      });
    } else {
      // candlestick + heikin-ashi
      priceSeries = chart.addSeries(CandlestickSeries, {
        upColor: colors.up,
        downColor: colors.down,
        borderUpColor: colors.up,
        borderDownColor: colors.down,
        wickUpColor: colors.up,
        wickDownColor: colors.down,
      });
    }
    priceSeriesRef.current = priceSeries;

    if (ohlc) {
      const data =
        chartType === "heikin-ashi"
          ? heikinAshi(bars)
          : bars.map((b) => ({
              time: toUtcEpoch(b.ts),
              open: b.o,
              high: b.h,
              low: b.l,
              close: b.c,
            }));
      const clean = sortedUnique(data);
      lastBarRef.current = clean.at(-1) ?? null;
      priceSeries.setData(clean as Parameters<typeof priceSeries.setData>[0]);
    } else {
      const data = sortedUnique(
        bars.map((b) => ({ time: toUtcEpoch(b.ts), value: b.c })),
      );
      const last = bars.at(-1);
      lastBarRef.current = last
        ? {
            time: toUtcEpoch(last.ts),
            open: last.o,
            high: last.h,
            low: last.l,
            close: last.c,
          }
        : null;
      priceSeries.setData(data as Parameters<typeof priceSeries.setData>[0]);
    }

    // ── Volume ─────────────────────────────────────────────────────────────
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: colors.line1,
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volumeSeries.setData(
      sortedUnique(
        bars.map((b) => ({
          time: toUtcEpoch(b.ts),
          value: b.v,
          color: b.c >= b.o ? colors.upSoft : colors.downSoft,
        })),
      ) as Parameters<typeof volumeSeries.setData>[0],
    );

    // ── Indicators (order-based pairing; multi-line + sub-pane aware) ──────
    // The backend returns one series per visible spec, in spec order. Each
    // series carries one or more named lines and a target pane: "price"
    // overlays the candles; "sub" gets its own pane below (RSI/MACD/etc.).
    const visibleSpecs = indicators.filter((s) => s.visible);
    let nextPane = 1;
    visibleSpecs.forEach((spec, i) => {
      const series = indicatorSeries[i];
      if (!series) return;
      const paneIndex = series.pane === "sub" ? nextPane++ : 0;
      for (const ln of series.lines) {
        const clean = sortedUnique(
          ln.points
            .filter((p) => p.v !== null)
            .map((p) => ({ time: toUtcEpoch(p.t), value: p.v as number })),
        );
        const color = roleColor(spec.color, ln.role);
        if (ln.role === "hist") {
          const hist = chart.addSeries(
            HistogramSeries,
            { color, priceLineVisible: false, lastValueVisible: false },
            paneIndex,
          );
          hist.setData(clean as Parameters<typeof hist.setData>[0]);
        } else {
          const line = chart.addSeries(
            LineSeries,
            {
              color,
              lineWidth: ln.role === "mid" ? 1 : spec.weight,
              lineStyle: ln.role === "mid" ? 2 : 0,
              priceLineVisible: false,
              lastValueVisible: false,
            },
            paneIndex,
          );
          line.setData(clean as Parameters<typeof line.setData>[0]);
        }
      }
    });

    // ── Futures-curve overlay (forward term structure) ─────────────────────
    if (showCurve && curve.length > 0) {
      const curveLine = chart.addSeries(LineSeries, {
        color: colors.accentBright,
        lineWidth: 1,
        lineStyle: 2, // dashed
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Curve",
      });
      const pts = curve
        .filter((c) => Number.isFinite(c.mid))
        .map((c) => ({
          time: toUtcEpoch(`${c.expiry}T00:00:00Z`),
          value: c.mid,
        }));
      curveLine.setData(
        sortedUnique(pts) as Parameters<typeof curveLine.setData>[0],
      );
    }

    // ── Markers: events (above) + candlestick patterns (below) ─────────────
    type Marker = {
      time: UTCTimestamp;
      position: "aboveBar" | "belowBar";
      color: string;
      shape: "circle" | "arrowUp" | "arrowDown";
      text: string;
      size: number;
    };
    const markers: Marker[] = [
      ...eventMarkers.map((m) => ({
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
      ...patterns.map((p) => ({
        time: toUtcEpoch(p.ts),
        position: "belowBar" as const,
        color:
          p.direction === "bullish"
            ? colors.up
            : p.direction === "bearish"
              ? colors.down
              : colors.flat,
        shape: (p.direction === "bullish"
          ? "arrowUp"
          : p.direction === "bearish"
            ? "arrowDown"
            : "circle") as Marker["shape"],
        text: p.code,
        size: 1,
      })),
    ].sort((a, b) => a.time - b.time);
    if (markers.length > 0) {
      createSeriesMarkers(
        priceSeries as Parameters<typeof createSeriesMarkers>[0],
        markers as Parameters<typeof createSeriesMarkers>[1],
      );
    }

    chart.timeScale().fitContent();

    if (apiRef) {
      apiRef.current = {
        screenshot: () => chartRef.current?.takeScreenshot() ?? null,
      };
    }

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry)
        chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      priceSeriesRef.current = null;
    };
  }, [
    bars,
    eventMarkers,
    indicators,
    indicatorSeries,
    chartType,
    logScale,
    showCurve,
    curve,
    patterns,
    apiRef,
  ]);

  // Live tick → update the forming (last) bar without recreating the chart.
  useEffect(() => {
    const series = priceSeriesRef.current;
    const last = lastBarRef.current;
    if (series === null || last === null || livePrice === null) return;
    if (!Number.isFinite(livePrice)) return;

    if (isOhlcType(chartType)) {
      const updated: OhlcPoint = {
        time: last.time,
        open: last.open,
        high: Math.max(last.high, livePrice),
        low: Math.min(last.low, livePrice),
        close: livePrice,
      };
      lastBarRef.current = updated;
      series.update(updated as Parameters<typeof series.update>[0]);
    } else {
      series.update({
        time: last.time,
        value: livePrice,
      } as Parameters<typeof series.update>[0]);
    }
  }, [livePrice, chartType]);

  return <div ref={containerRef} className="w-full h-full" />;
}
