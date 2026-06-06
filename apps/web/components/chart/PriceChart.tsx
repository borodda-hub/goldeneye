"use client";

import type {
  Bar,
  ChartApi,
  ChartType,
  CurvePoint,
  EventMarkerData,
} from "@/app/(app)/chart/types";
import type {
  AutoTaLevel,
  AutoTaPattern,
  AutoTaTrendline,
  CandlestickPattern,
  IndicatorSeriesDTO,
} from "@/lib/api";
import { DrawingPrimitive } from "@/lib/chart/DrawingPrimitive";
import type { ChartStyle } from "@/lib/chart/chartStyle";
import {
  type Drawing,
  type DrawingPoint,
  type DrawingTool,
  type DrawingType,
  POINTS_NEEDED,
  newDrawingId,
} from "@/lib/chart/drawings";
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
  type MouseEventParams,
  PriceScaleMode,
  type SeriesType,
  type Time,
  type UTCTimestamp,
  createChart,
  createSeriesMarkers,
} from "lightweight-charts";
import { type MutableRefObject, useEffect, useRef, useState } from "react";

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
  /** Auto-TA overlays (support/resistance, trendlines, chart patterns). */
  autoTa: {
    levels: AutoTaLevel[];
    trendlines: AutoTaTrendline[];
    patterns: AutoTaPattern[];
  } | null;
  /** Latest live price (from the front-month tick channel); updates the last bar. */
  livePrice: number | null;
  /** User chart-appearance settings (background, candle colors, grid, …). */
  style: ChartStyle;
  /** Manual drawings (trendlines, h-lines, …) for the active symbol. */
  drawings: Drawing[];
  /** Active drawing tool ("cursor" selects/pans; others place shapes). */
  activeTool: DrawingTool;
  /** Currently selected drawing id (shows handles), or null. */
  selectedDrawingId: string | null;
  onDrawingsChange: (drawings: Drawing[]) => void;
  onSelectDrawing: (id: string | null) => void;
  /** Reset the tool to "cursor" after a shape is finalized. */
  onToolChange: (tool: DrawingTool) => void;
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

/** A single Data-Window readout — OHLCV + change vs the prior close. */
type DataRow = {
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
  chg: number;
  pct: number;
};

function rowFor(bars: Bar[], idx: number): DataRow | null {
  const b = bars[idx];
  if (!b) return null;
  const prev = idx > 0 ? bars[idx - 1].c : b.o;
  const chg = b.c - prev;
  return {
    o: b.o,
    h: b.h,
    l: b.l,
    c: b.c,
    v: b.v,
    chg,
    pct: prev ? chg / prev : 0,
  };
}

function fmtPrice(v: number): string {
  return Math.abs(v) >= 1000 ? v.toFixed(2) : v.toFixed(3);
}

function fmtVol(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
}

type Marker = {
  time: UTCTimestamp;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "circle" | "arrowUp" | "arrowDown";
  text: string;
  size: number;
};

/** Event markers (above bars) + candlestick-pattern markers (below), sorted by
 *  time. Shared by the build effect (initial) and the data-update effect. */
function buildMarkers(
  eventMarkers: EventMarkerData[],
  patterns: CandlestickPattern[],
): Marker[] {
  return [
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
}

/** Price-series data + the last bar (for the live-tick effect), per chart type. */
function priceData(
  bars: Bar[],
  chartType: ChartType,
): { data: unknown[]; lastBar: OhlcPoint | null } {
  if (isOhlcType(chartType)) {
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
    return { data: clean, lastBar: clean.at(-1) ?? null };
  }
  const data = sortedUnique(
    bars.map((b) => ({ time: toUtcEpoch(b.ts), value: b.c })),
  );
  const last = bars.at(-1);
  return {
    data,
    lastBar: last
      ? {
          time: toUtcEpoch(last.ts),
          open: last.o,
          high: last.h,
          low: last.l,
          close: last.c,
        }
      : null,
  };
}

/** Volume histogram data (up/down colored). */
function volumeData(bars: Bar[]): unknown[] {
  return sortedUnique(
    bars.map((b) => ({
      time: toUtcEpoch(b.ts),
      value: b.v,
      color: b.c >= b.o ? colors.upSoft : colors.downSoft,
    })),
  );
}

/** Apply the user's appearance settings to a live chart via applyOptions —
 *  no rebuild, so color edits update instantly. Candle-color options only
 *  apply to candle/bar series; line/area types keep their accent styling. */
function applyChartStyle(
  chart: IChartApi,
  priceSeries: ISeriesApi<SeriesType> | null,
  chartType: ChartType,
  s: ChartStyle,
): void {
  chart.applyOptions({
    layout: {
      background: s.gradient
        ? {
            type: ColorType.VerticalGradient,
            topColor: s.background,
            bottomColor: s.backgroundBottom,
          }
        : { type: ColorType.Solid, color: s.background },
      textColor: s.textColor,
      fontSize: s.fontSize,
    },
    grid: {
      vertLines: { color: s.gridColor, visible: s.gridVisible },
      horzLines: { color: s.gridColor, visible: s.gridVisible },
    },
    crosshair: {
      mode: s.crosshairMagnet ? CrosshairMode.Magnet : CrosshairMode.Normal,
      vertLine: { color: s.crosshairColor, style: s.crosshairStyle },
      horzLine: { color: s.crosshairColor, style: s.crosshairStyle },
    },
    rightPriceScale: { borderColor: s.gridColor },
    timeScale: { borderColor: s.gridColor },
  });
  if (priceSeries === null) return;
  if (chartType === "candlestick" || chartType === "heikin-ashi") {
    priceSeries.applyOptions({
      upColor: s.hollowUp ? "rgba(0,0,0,0)" : s.upColor,
      downColor: s.downColor,
      borderVisible: s.borderVisible || s.hollowUp,
      borderUpColor: s.upColor,
      borderDownColor: s.downColor,
      wickUpColor: s.wickUpColor,
      wickDownColor: s.wickDownColor,
    } as Parameters<typeof priceSeries.applyOptions>[0]);
  } else if (chartType === "bars") {
    priceSeries.applyOptions({
      upColor: s.upColor,
      downColor: s.downColor,
    } as Parameters<typeof priceSeries.applyOptions>[0]);
  }
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
  autoTa,
  livePrice,
  style,
  drawings,
  activeTool,
  selectedDrawingId,
  onDrawingsChange,
  onSelectDrawing,
  onToolChange,
  apiRef,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  // Markers plugin handle (events + candlestick patterns); updated in place so a
  // bars/pattern refetch doesn't rebuild the chart.
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(
    null,
  );
  const lastBarRef = useRef<OhlcPoint | null>(null);
  // In-progress drawing being placed (1st point set, awaiting the 2nd) + its
  // live preview primitive. Persist across renders without retriggering effects.
  const inProgressRef = useRef<{
    type: DrawingTool;
    points: DrawingPoint[];
  } | null>(null);
  const previewRef = useRef<DrawingPrimitive | null>(null);
  // Latest props the pointer handlers read, so the handler effect can stay
  // subscribed across data refetches (it only re-runs when the chart rebuilds).
  const attachedRef = useRef<DrawingPrimitive[]>([]);
  const drawingsRef = useRef(drawings);
  drawingsRef.current = drawings;
  const activeToolRef = useRef(activeTool);
  activeToolRef.current = activeTool;
  const selectedIdRef = useRef(selectedDrawingId);
  selectedIdRef.current = selectedDrawingId;
  const onDrawingsChangeRef = useRef(onDrawingsChange);
  onDrawingsChangeRef.current = onDrawingsChange;
  const onSelectDrawingRef = useRef(onSelectDrawing);
  onSelectDrawingRef.current = onSelectDrawing;
  const onToolChangeRef = useRef(onToolChange);
  onToolChangeRef.current = onToolChange;
  // Latest style, read inside the build effect without making it a dep — live
  // style edits go through the dedicated applyOptions effect below (no rebuild).
  const styleRef = useRef(style);
  styleRef.current = style;
  // Latest bars + a time→index map, read by the crosshair handler so the Data
  // Window stays correct after a bars refetch (which no longer rebuilds the chart).
  const barsRef = useRef(bars);
  barsRef.current = bars;
  const timeToIdxRef = useRef<Map<number, number>>(new Map());
  // Data Window (OHLCV at the crosshair) + scroll-to-realtime affordance.
  const [hover, setHover] = useState<DataRow | null>(null);
  const [atRealtime, setAtRealtime] = useState(true);
  // Bumped whenever the chart is (re)built, so the drawings effect re-attaches
  // its primitives to the fresh series.
  const [chartVersion, setChartVersion] = useState(0);

  // Rebuild the chart only on structural change (chart type, indicator set,
  // overlays). `bars`/`eventMarkers`/`patterns`/`logScale` are intentionally NOT
  // deps — bars + markers update in place via the data effect, and logScale via
  // applyOptions, so a refetch or scale toggle no longer tears down the chart.
  // biome-ignore lint/correctness/useExhaustiveDependencies: see note above.
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
    // Paint the user's appearance settings over the just-created series/chart.
    applyChartStyle(chart, priceSeries, chartType, styleRef.current);

    // Initial price data — subsequent bars refetches update this in place via
    // the data effect below (no chart rebuild).
    const initial = priceData(bars, chartType);
    lastBarRef.current = initial.lastBar;
    priceSeries.setData(
      initial.data as Parameters<typeof priceSeries.setData>[0],
    );

    // ── Volume ─────────────────────────────────────────────────────────────
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: colors.line1,
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeriesRef.current = volumeSeries;
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volumeSeries.setData(
      volumeData(bars) as Parameters<typeof volumeSeries.setData>[0],
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

    // ── Auto-TA overlays: S/R levels, trendlines, chart-pattern outlines ────
    if (autoTa) {
      for (const lvl of autoTa.levels) {
        priceSeries.createPriceLine({
          price: lvl.price,
          color: lvl.kind === "support" ? colors.up : colors.down,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `${lvl.kind === "support" ? "S" : "R"} ·${lvl.touches}`,
        });
      }
      const segment = (
        pts: { ts: string; price: number }[],
        color: string,
        style: number,
      ) => {
        const data = sortedUnique(
          pts.map((p) => ({ time: toUtcEpoch(p.ts), value: p.price })),
        );
        if (data.length < 2) return;
        const line = chart.addSeries(LineSeries, {
          color,
          lineWidth: 1,
          lineStyle: style,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        line.setData(data as Parameters<typeof line.setData>[0]);
      };
      for (const t of autoTa.trendlines) {
        segment(
          [t.p1, t.p2],
          t.role === "support" ? colors.up : colors.down,
          0,
        );
      }
      for (const p of autoTa.patterns) {
        const color =
          p.direction === "bullish"
            ? colors.up
            : p.direction === "bearish"
              ? colors.down
              : colors.flat;
        segment(p.points, color, 0);
      }
    }

    // ── Markers: events (above) + candlestick patterns (below) ─────────────
    // Created once; the data effect updates them via setMarkers on refetch.
    markersRef.current = createSeriesMarkers(
      priceSeries as Parameters<typeof createSeriesMarkers>[0],
      buildMarkers(eventMarkers, patterns) as Parameters<
        typeof createSeriesMarkers
      >[1],
    );

    chart.timeScale().fitContent();

    // ── Data Window + scroll-to-realtime wiring ───────────────────────────
    // Reads bars/index via refs so refetches don't need a rebuild to stay live.
    timeToIdxRef.current = new Map();
    bars.forEach((b, i) => timeToIdxRef.current.set(toUtcEpoch(b.ts), i));
    setHover(rowFor(bars, bars.length - 1));
    chart.subscribeCrosshairMove((param) => {
      const cur = barsRef.current;
      const t = typeof param.time === "number" ? param.time : null;
      const idx =
        t !== null && timeToIdxRef.current.has(t)
          ? (timeToIdxRef.current.get(t) as number)
          : cur.length - 1;
      setHover(rowFor(cur, idx));
    });
    chart
      .timeScale()
      .subscribeVisibleLogicalRangeChange((range) =>
        setAtRealtime(range ? range.to >= barsRef.current.length - 1.5 : true),
      );

    if (apiRef) {
      apiRef.current = {
        screenshot: () => chartRef.current?.takeScreenshot() ?? null,
        fitContent: () => chartRef.current?.timeScale().fitContent(),
      };
    }

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry)
        chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    // Signal the drawings effect to (re)attach its primitives to this series.
    setChartVersion((v) => v + 1);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      priceSeriesRef.current = null;
      volumeSeriesRef.current = null;
      markersRef.current = null;
    };
  }, [
    indicators,
    indicatorSeries,
    chartType,
    showCurve,
    curve,
    autoTa,
    apiRef,
  ]);

  // ── Data update — bars/markers refetch updates series in place (no rebuild) ─
  useEffect(() => {
    const series = priceSeriesRef.current;
    const volume = volumeSeriesRef.current;
    if (series === null) return;
    const next = priceData(bars, chartType);
    lastBarRef.current = next.lastBar;
    try {
      series.setData(next.data as Parameters<typeof series.setData>[0]);
      volume?.setData(volumeData(bars) as Parameters<typeof series.setData>[0]);
    } catch {
      // series disposed mid-rebuild — the build effect re-seeds the fresh one.
    }
    timeToIdxRef.current = new Map();
    bars.forEach((b, i) => timeToIdxRef.current.set(toUtcEpoch(b.ts), i));
    markersRef.current?.setMarkers(
      buildMarkers(eventMarkers, patterns) as Parameters<
        NonNullable<typeof markersRef.current>["setMarkers"]
      >[0],
    );
  }, [bars, eventMarkers, patterns, chartType]);

  // ── Log/linear scale toggle — applied in place, no chart rebuild ──────────
  useEffect(() => {
    const chart = chartRef.current;
    if (chart === null) return;
    chart.priceScale("right").applyOptions({
      mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
    });
  }, [logScale]);

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

  // Live restyle — appearance edits apply via applyOptions, no chart rebuild.
  useEffect(() => {
    if (chartRef.current === null) return;
    applyChartStyle(chartRef.current, priceSeriesRef.current, chartType, style);
  }, [style, chartType]);

  // ── Drawings: (re)attach a primitive per drawing on data/selection/rebuild ─
  useEffect(() => {
    const series = priceSeriesRef.current;
    if (series === null) return;
    void chartVersion;
    const next: DrawingPrimitive[] = [];
    for (const d of drawings) {
      const prim = new DrawingPrimitive(d, d.id === selectedDrawingId);
      try {
        series.attachPrimitive(prim);
        next.push(prim);
      } catch {
        // series disposed mid-rebuild — re-attaches on the next chartVersion.
      }
    }
    attachedRef.current = next;
    return () => {
      for (const prim of next) {
        try {
          series.detachPrimitive(prim);
        } catch {
          // already disposed
        }
      }
      attachedRef.current = [];
    };
  }, [drawings, selectedDrawingId, chartVersion]);

  // ── Drawings: pointer/keyboard handlers — subscribed once per chart (re-run
  // only when the chart is rebuilt, i.e. chartVersion). State is read via refs
  // so prop changes don't re-subscribe. Data refetches no longer rebuild the
  // chart, so an in-progress placement is never interrupted mid-flight. ──────
  useEffect(() => {
    const chart = chartRef.current;
    const series = priceSeriesRef.current;
    if (chart === null || series === null) return;
    void chartVersion;
    const DRAW_COLOR = colors.accent;
    const DRAW_WIDTH = 2;

    const toPoint = (param: MouseEventParams<Time>): DrawingPoint | null => {
      if (!param.point) return null;
      try {
        const price = series.coordinateToPrice(param.point.y);
        const t =
          param.time ?? chart.timeScale().coordinateToTime(param.point.x);
        if (price === null || t === null || t === undefined) return null;
        return { time: Number(t), price: Number(price) };
      } catch {
        return null;
      }
    };

    const clearInProgress = () => {
      if (previewRef.current) {
        try {
          series.detachPrimitive(previewRef.current);
        } catch {
          // already disposed
        }
        previewRef.current = null;
      }
      inProgressRef.current = null;
    };

    const finalize = () => {
      const ip = inProgressRef.current;
      if (!ip || ip.type === "cursor" || ip.type === "measure") return;
      const type = ip.type;
      const d: Drawing = {
        id: newDrawingId(),
        type,
        points: ip.points.slice(0, POINTS_NEEDED[type]),
        color: DRAW_COLOR,
        width: DRAW_WIDTH,
      };
      clearInProgress();
      onDrawingsChangeRef.current([...drawingsRef.current, d]);
      onSelectDrawingRef.current(d.id);
      onToolChangeRef.current("cursor");
    };

    const onClick = (param: MouseEventParams<Time>) => {
      const tool = activeToolRef.current;
      if (tool === "cursor") {
        if (!param.point) return;
        let hit: string | null = null;
        for (const prim of attachedRef.current) {
          if (prim.hitTest(param.point.x, param.point.y)) {
            hit = prim.drawing.id;
            break;
          }
        }
        onSelectDrawingRef.current(hit);
        return;
      }
      if (tool === "measure") return; // T1.1b
      const pt = toPoint(param);
      if (!pt) return;
      const ip = inProgressRef.current;
      if (!ip) {
        inProgressRef.current = { type: tool, points: [pt] };
        if (POINTS_NEEDED[tool] === 1) {
          finalize();
          return;
        }
        const preview = new DrawingPrimitive(
          {
            id: "__preview__",
            type: tool,
            points: [pt, pt],
            color: DRAW_COLOR,
            width: DRAW_WIDTH,
          },
          false,
        );
        try {
          series.attachPrimitive(preview);
          previewRef.current = preview;
        } catch {
          // ignore
        }
      } else {
        ip.points.push(pt);
        if (ip.points.length >= POINTS_NEEDED[ip.type as DrawingType])
          finalize();
      }
    };

    const onMove = (param: MouseEventParams<Time>) => {
      const ip = inProgressRef.current;
      const preview = previewRef.current;
      if (!ip || !preview || POINTS_NEEDED[ip.type as DrawingType] !== 2)
        return;
      const pt = toPoint(param);
      if (!pt) return;
      preview.drawing.points = [ip.points[0], pt];
      preview.requestRedraw();
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        clearInProgress();
        onSelectDrawingRef.current(null);
      } else if (
        (e.key === "Delete" || e.key === "Backspace") &&
        selectedIdRef.current !== null
      ) {
        const sel = selectedIdRef.current;
        onDrawingsChangeRef.current(
          drawingsRef.current.filter((d) => d.id !== sel),
        );
        onSelectDrawingRef.current(null);
      }
    };

    chart.subscribeClick(onClick);
    chart.subscribeCrosshairMove(onMove);
    window.addEventListener("keydown", onKey);

    return () => {
      try {
        chart.unsubscribeClick(onClick);
      } catch {
        // chart disposed
      }
      try {
        chart.unsubscribeCrosshairMove(onMove);
      } catch {
        // chart disposed
      }
      window.removeEventListener("keydown", onKey);
      clearInProgress();
    };
  }, [chartVersion]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {hover && (
        <div
          className="pointer-events-none absolute left-2 top-1.5 z-10 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 font-mono text-[11px] tabular-nums"
          aria-label="Crosshair OHLCV"
        >
          <span style={{ color: style.textColor }}>O {fmtPrice(hover.o)}</span>
          <span style={{ color: style.textColor }}>H {fmtPrice(hover.h)}</span>
          <span style={{ color: style.textColor }}>L {fmtPrice(hover.l)}</span>
          <span style={{ color: style.textColor }}>C {fmtPrice(hover.c)}</span>
          <span
            style={{ color: hover.chg >= 0 ? style.upColor : style.downColor }}
          >
            {hover.chg >= 0 ? "▲" : "▼"} {fmtPrice(Math.abs(hover.chg))} (
            {(hover.pct * 100).toFixed(2)}%)
          </span>
          <span style={{ color: style.textColor }}>V {fmtVol(hover.v)}</span>
        </div>
      )}
      {!atRealtime && (
        <button
          type="button"
          onClick={() => chartRef.current?.timeScale().scrollToRealTime()}
          aria-label="Scroll to latest"
          title="Scroll to latest"
          className="absolute bottom-9 right-3 z-10 rounded-full border border-line-2 bg-surface-1/90 px-2.5 py-1 font-mono text-[11px] text-ink-2 hover:text-ink-1 hover:bg-surface-2 transition-colors"
        >
          »|
        </button>
      )}
    </div>
  );
}
