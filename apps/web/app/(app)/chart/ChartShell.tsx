"use client";

import { ChartContextMenu } from "@/components/chart/ChartContextMenu";
import { ChartFooter } from "@/components/chart/ChartFooter";
import { ChartSettingsModal } from "@/components/chart/ChartSettingsModal";
import { ChartToolbar } from "@/components/chart/ChartToolbar";
import { DrawingToolbar } from "@/components/chart/DrawingToolbar";
import { EventDrawer } from "@/components/chart/EventDrawer";
import { IndicatorPicker } from "@/components/chart/IndicatorPicker";
import type { CandlestickPattern, InstrumentRow } from "@/lib/api";
import {
  type ChartStyle,
  DEFAULT_CHART_STYLE,
  loadChartStyle,
  saveChartStyle,
} from "@/lib/chart/chartStyle";
import {
  type Drawing,
  type DrawingTool,
  loadDrawings,
  saveDrawings,
} from "@/lib/chart/drawings";
import {
  type IndicatorSpec,
  specsToQueryParam,
  storageKey,
} from "@/lib/chart/indicatorRegistry";
import {
  useChartAutoTa,
  useChartBars,
  useChartCurve,
  useChartIndicators,
  useChartPatterns,
  useChartSeasonality,
  useInstruments,
} from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  Bar,
  ChartApi,
  ChartBarsResponse,
  ChartType,
  CurvePoint,
  RangePreset,
  Resolution,
} from "./types";

const PriceChart = dynamic(
  () =>
    import("@/components/chart/PriceChart").then((m) => ({
      default: m.PriceChart,
    })),
  { ssr: false },
);

const SeasonalityChart = dynamic(
  () =>
    import("@/components/chart/SeasonalityChart").then((m) => ({
      default: m.SeasonalityChart,
    })),
  { ssr: false },
);

interface Props {
  initialBars: ChartBarsResponse | null;
  initialCurve: CurvePoint[] | null;
  /** Front-month contract resolved server-side from the curve endpoint. */
  contractCode?: string;
  initialSymbol?: string;
}

// Stable empty array — reused so "no data yet" props keep the same reference
// across renders and don't churn PriceChart's structural build effect.
const EMPTY: never[] = [];

const DEFAULT_CONTRACT = "NGM26";
const FRONT_MONTH_FALLBACK_BY_SYMBOL: Record<string, string> = {
  NG: "NGM26",
  CL: "CLN26",
};

const RANGE_DAYS: Record<RangePreset, number> = {
  "3M": 90,
  "6M": 182,
  "1Y": 365,
  "2Y": 730,
  "5Y": 1825,
  All: 3650,
};

// Global chart preferences (apply across symbols).
function getPref<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(key) as T) || fallback;
  } catch {
    return fallback;
  }
}
function setPref(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function LoadingPlaceholder() {
  return (
    <div className="w-full h-full flex items-center justify-center text-ink-4 text-xs font-mono">
      Loading chart…
    </div>
  );
}

function loadIndicators(symbol: string): IndicatorSpec[] {
  try {
    const raw = localStorage.getItem(storageKey(symbol));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as IndicatorSpec[];
  } catch {
    return [];
  }
}

function saveIndicators(symbol: string, specs: IndicatorSpec[]): void {
  try {
    localStorage.setItem(storageKey(symbol), JSON.stringify(specs));
  } catch {
    // ignore — localStorage may be unavailable (incognito, quota, etc).
  }
}

export function ChartShell({
  initialBars,
  contractCode: initialContractCode = DEFAULT_CONTRACT,
  initialSymbol = "NG",
}: Props) {
  const { activeSymbol } = useActiveInstrument();
  const [resolution, setResolution] = useState<Resolution>("1d");
  const [chartType, setChartType] = useState<ChartType>("candlestick");
  const [logScale, setLogScale] = useState(false);
  const [showCurve, setShowCurve] = useState(false);
  const [showPatterns, setShowPatterns] = useState(false);
  const [showAutoTa, setShowAutoTa] = useState(false);
  const [showSeasonality, setShowSeasonality] = useState(false);
  const [range, setRange] = useState<RangePreset>("2Y");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [style, setStyle] = useState<ChartStyle>(DEFAULT_CHART_STYLE);
  const [menuPos, setMenuPos] = useState<{ x: number; y: number } | null>(null);
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [activeTool, setActiveTool] = useState<DrawingTool>("cursor");
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(
    null,
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const chartApiRef = useRef<ChartApi | null>(null);

  // Hydrate global chart prefs after mount (SSR-safe defaults first paint).
  useEffect(() => {
    setResolution(getPref<Resolution>("goldeneye:chart:resolution", "1d"));
    setChartType(getPref<ChartType>("goldeneye:chart:type", "candlestick"));
    setLogScale(getPref<string>("goldeneye:chart:logscale", "0") === "1");
    setShowCurve(getPref<string>("goldeneye:chart:curve", "0") === "1");
    setShowPatterns(getPref<string>("goldeneye:chart:patterns", "0") === "1");
    setShowAutoTa(getPref<string>("goldeneye:chart:autota", "0") === "1");
    setShowSeasonality(getPref<string>("goldeneye:chart:season", "0") === "1");
    setRange(getPref<RangePreset>("goldeneye:chart:range", "2Y"));
    setStyle(loadChartStyle());
  }, []);

  const changeStyle = useCallback((s: ChartStyle) => {
    setStyle(s);
    saveChartStyle(s);
  }, []);

  // Indicator state: re-keyed per-symbol so each instrument has its own set.
  const [indicators, setIndicators] = useState<IndicatorSpec[]>([]);
  useEffect(() => {
    setIndicators(loadIndicators(activeSymbol));
    setDrawings(loadDrawings(activeSymbol));
    setSelectedDrawingId(null);
  }, [activeSymbol]);

  const changeDrawings = useCallback(
    (next: Drawing[]) => {
      setDrawings(next);
      saveDrawings(activeSymbol, next);
    },
    [activeSymbol],
  );

  const today = new Date().toISOString().split("T")[0];
  const from = new Date(Date.now() - RANGE_DAYS[range] * 86400_000)
    .toISOString()
    .split("T")[0];

  // Resolve front-month contract (see Phase 14 notes): instruments endpoint is
  // the source of truth; curve endpoint is the live fallback.
  const { data: instruments } = useInstruments();
  type InstrumentsResp = { instruments?: InstrumentRow[] };
  const dbFrontCode = (
    instruments as InstrumentsResp | undefined
  )?.instruments?.find((i) => i.symbol === activeSymbol)?.quote
    ?.front_month_code;

  const { data: curve } = useChartCurve(activeSymbol, today);
  type CurveItem = { contract_code: string; expiry: string; mid: number };
  type CurveData = { curve?: CurveItem[] };
  const curveItems = (curve as CurveData | undefined)?.curve ?? EMPTY;
  const liveFrontCode = curveItems[0]?.contract_code;
  const contractCode =
    dbFrontCode ??
    liveFrontCode ??
    (activeSymbol === initialSymbol
      ? initialContractCode
      : (FRONT_MONTH_FALLBACK_BY_SYMBOL[activeSymbol] ?? DEFAULT_CONTRACT));

  const curvePoints = useMemo<CurvePoint[]>(
    () =>
      curveItems.map((c) => ({
        contract_code: c.contract_code,
        expiry: c.expiry,
        mid: c.mid,
      })),
    [curveItems],
  );

  const { data: fetchedBars } = useChartBars(
    contractCode,
    resolution,
    from,
    today,
  );

  // Live forming candle — drive the last bar's close from the front-month tick.
  const { data: tick } = useChannel<{ price?: number | null }>(
    `price.${activeSymbol}.front`,
  );
  const livePrice =
    typeof tick?.price === "number" && Number.isFinite(tick.price)
      ? tick.price
      : null;

  const barsData =
    (fetchedBars as ChartBarsResponse | undefined) ?? initialBars;

  // Candlestick patterns — only fetched while the toggle is on.
  const { data: patternsResp } = useChartPatterns(
    contractCode,
    resolution,
    from,
    today,
    showPatterns,
  );
  const patterns: CandlestickPattern[] = showPatterns
    ? (patternsResp?.patterns ?? EMPTY)
    : EMPTY;

  // Auto-TA (support/resistance, trendlines, chart patterns).
  const { data: autoTaResp } = useChartAutoTa(
    contractCode,
    resolution,
    from,
    today,
    showAutoTa,
  );
  const autoTa = showAutoTa ? (autoTaResp ?? null) : null;

  // Seasonality view (per-year overlay) — fetched only while toggled on.
  const { data: seasonalityResp } = useChartSeasonality(
    contractCode,
    6,
    showSeasonality,
  );

  const specQuery = specsToQueryParam(indicators);
  const { data: indicatorsData } = useChartIndicators(activeSymbol, specQuery);

  const persistAndSet = useCallback(
    (next: IndicatorSpec[]) => {
      setIndicators(next);
      saveIndicators(activeSymbol, next);
    },
    [activeSymbol],
  );

  const handleAdd = useCallback(
    (spec: IndicatorSpec) => persistAndSet([...indicators, spec]),
    [indicators, persistAndSet],
  );
  const handleUpdate = useCallback(
    (spec: IndicatorSpec) =>
      persistAndSet(indicators.map((i) => (i.id === spec.id ? spec : i))),
    [indicators, persistAndSet],
  );
  const handleDelete = useCallback(
    (id: string) => persistAndSet(indicators.filter((i) => i.id !== id)),
    [indicators, persistAndSet],
  );
  const handleToggleVisible = useCallback(
    (id: string) =>
      persistAndSet(
        indicators.map((i) =>
          i.id === id ? { ...i, visible: !i.visible } : i,
        ),
      ),
    [indicators, persistAndSet],
  );

  // ── Pref-changing handlers (persist globally) ────────────────────────────
  const changeResolution = useCallback((r: Resolution) => {
    setResolution(r);
    setPref("goldeneye:chart:resolution", r);
  }, []);
  const changeChartType = useCallback((t: ChartType) => {
    setChartType(t);
    setPref("goldeneye:chart:type", t);
  }, []);
  const changeRange = useCallback((r: RangePreset) => {
    setRange(r);
    setPref("goldeneye:chart:range", r);
  }, []);
  const toggleLog = useCallback(() => {
    setLogScale((v) => {
      setPref("goldeneye:chart:logscale", v ? "0" : "1");
      return !v;
    });
  }, []);
  const toggleCurve = useCallback(() => {
    setShowCurve((v) => {
      setPref("goldeneye:chart:curve", v ? "0" : "1");
      return !v;
    });
  }, []);
  const togglePatterns = useCallback(() => {
    setShowPatterns((v) => {
      setPref("goldeneye:chart:patterns", v ? "0" : "1");
      return !v;
    });
  }, []);
  const toggleAutoTa = useCallback(() => {
    setShowAutoTa((v) => {
      setPref("goldeneye:chart:autota", v ? "0" : "1");
      return !v;
    });
  }, []);
  const toggleSeasonality = useCallback(() => {
    setShowSeasonality((v) => {
      setPref("goldeneye:chart:season", v ? "0" : "1");
      return !v;
    });
  }, []);

  const handleScreenshot = useCallback(() => {
    const canvas = chartApiRef.current?.screenshot();
    if (!canvas) return;
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = `goldeneye-${contractCode}-${resolution}.png`;
    a.click();
  }, [contractCode, resolution]);

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void el.requestFullscreen?.();
    }
  }, []);

  return (
    <div ref={containerRef} className="flex flex-col h-full bg-surface-0">
      <ChartToolbar
        resolution={resolution}
        onResolutionChange={changeResolution}
        chartType={chartType}
        onChartTypeChange={changeChartType}
        range={range}
        onRangeChange={changeRange}
        logScale={logScale}
        onToggleLog={toggleLog}
        showCurve={showCurve}
        onToggleCurve={toggleCurve}
        showPatterns={showPatterns}
        onTogglePatterns={togglePatterns}
        patternCount={patterns.length}
        showAutoTa={showAutoTa}
        onToggleAutoTa={toggleAutoTa}
        showSeasonality={showSeasonality}
        onToggleSeasonality={toggleSeasonality}
        indicatorCount={indicators.filter((i) => i.visible).length}
        onOpenIndicators={() => setPickerOpen(true)}
        onClearIndicators={() => persistAndSet([])}
        onScreenshot={handleScreenshot}
        onFullscreen={toggleFullscreen}
        onOpenSettings={() => setSettingsOpen(true)}
        contractCode={contractCode}
      />
      <div className="flex flex-1 min-h-0 gap-0">
        {!showSeasonality && (
          <DrawingToolbar
            activeTool={activeTool}
            onToolChange={setActiveTool}
            onClearAll={() => changeDrawings([])}
            hasDrawings={drawings.length > 0}
          />
        )}
        <div
          className="flex-1 min-w-0"
          onContextMenu={(e) => {
            e.preventDefault();
            setMenuPos({ x: e.clientX, y: e.clientY });
          }}
        >
          {showSeasonality ? (
            seasonalityResp ? (
              <SeasonalityChart data={seasonalityResp} />
            ) : (
              <LoadingPlaceholder />
            )
          ) : barsData ? (
            <PriceChart
              bars={barsData.bars}
              eventMarkers={barsData.event_markers}
              indicators={indicators}
              indicatorSeries={indicatorsData?.indicators ?? EMPTY}
              chartType={chartType}
              logScale={logScale}
              showCurve={showCurve}
              curve={curvePoints}
              patterns={patterns}
              autoTa={autoTa}
              livePrice={livePrice}
              style={style}
              drawings={drawings}
              activeTool={activeTool}
              selectedDrawingId={selectedDrawingId}
              onDrawingsChange={changeDrawings}
              onSelectDrawing={setSelectedDrawingId}
              onToolChange={setActiveTool}
              apiRef={chartApiRef}
            />
          ) : (
            <LoadingPlaceholder />
          )}
        </div>
        <EventDrawer
          events={barsData?.event_markers ?? []}
          open={drawerOpen}
          onToggle={() => setDrawerOpen((o) => !o)}
        />
      </div>
      <ChartFooter
        contract={barsData?.contract ?? { code: contractCode, expiry: "—" }}
        resolution={resolution}
        asOf={barsData?.bars.at(-1)?.ts ?? today}
      />
      <IndicatorPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        indicators={indicators}
        onAdd={handleAdd}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
        onToggleVisible={handleToggleVisible}
        onReplaceAll={persistAndSet}
      />
      <ChartSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        style={style}
        onChange={changeStyle}
      />
      {menuPos && (
        <ChartContextMenu
          x={menuPos.x}
          y={menuPos.y}
          onClose={() => setMenuPos(null)}
          items={[
            {
              label: "Appearance settings…",
              onClick: () => setSettingsOpen(true),
            },
            { label: "Add indicator…", onClick: () => setPickerOpen(true) },
            {
              label: "Reset zoom",
              onClick: () => chartApiRef.current?.fitContent(),
            },
            {
              label: logScale ? "Linear scale" : "Logarithmic scale",
              onClick: toggleLog,
            },
            { label: "Download PNG", onClick: handleScreenshot },
          ]}
        />
      )}
    </div>
  );
}
