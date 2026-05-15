"use client";

import { ChartFooter } from "@/components/chart/ChartFooter";
import { ChartToolbar } from "@/components/chart/ChartToolbar";
import { EventDrawer } from "@/components/chart/EventDrawer";
import { IndicatorPicker } from "@/components/chart/IndicatorPicker";
import {
  type IndicatorSpec,
  specsToQueryParam,
  storageKey,
} from "@/lib/chart/indicatorRegistry";
import { useChartBars, useChartCurve, useChartIndicators } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import type { Bar, ChartBarsResponse, CurvePoint, Resolution } from "./types";

const PriceChart = dynamic(
  () =>
    import("@/components/chart/PriceChart").then((m) => ({
      default: m.PriceChart,
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

const DEFAULT_CONTRACT = "NGM26";
const FRONT_MONTH_FALLBACK_BY_SYMBOL: Record<string, string> = {
  NG: "NGM26",
  CL: "CLN26",
};

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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  // Indicator state: re-keyed per-symbol so each instrument has its own set.
  // Hydrated from localStorage in an effect so SSR and first-paint agree.
  const [indicators, setIndicators] = useState<IndicatorSpec[]>([]);
  useEffect(() => {
    setIndicators(loadIndicators(activeSymbol));
  }, [activeSymbol]);

  const today = new Date().toISOString().split("T")[0];
  const twoYearsAgo = new Date(Date.now() - 730 * 86400_000)
    .toISOString()
    .split("T")[0];

  // Resolve front-month contract live whenever activeSymbol changes. Falls
  // back to the SSR-provided initialContractCode (when it's for the active
  // symbol) and then to a symbol-specific default.
  const { data: curve } = useChartCurve(activeSymbol, today);
  type CurveItem = { contract_code: string };
  type CurveData = { curve?: CurveItem[] };
  const curveItems = (curve as CurveData | undefined)?.curve ?? [];
  const liveFrontCode = curveItems[0]?.contract_code;
  const contractCode =
    liveFrontCode ??
    (activeSymbol === initialSymbol
      ? initialContractCode
      : (FRONT_MONTH_FALLBACK_BY_SYMBOL[activeSymbol] ?? DEFAULT_CONTRACT));

  const { data: fetchedBars } = useChartBars(
    contractCode,
    resolution,
    twoYearsAgo,
    today,
  );

  const { data: livebar } = useChannel<Bar>(`price.${activeSymbol}.front.1m`);
  void livebar; // live bar appending reserved for future enhancement

  const barsData =
    (fetchedBars as ChartBarsResponse | undefined) ?? initialBars;

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

  return (
    <div className="flex flex-col h-full">
      <ChartToolbar
        resolution={resolution}
        onResolutionChange={setResolution}
        indicatorCount={indicators.filter((i) => i.visible).length}
        onOpenIndicators={() => setPickerOpen(true)}
        onClearIndicators={() => persistAndSet([])}
        contractCode={contractCode}
      />
      <div className="flex flex-1 min-h-0 gap-0">
        <div className="flex-1 min-w-0">
          {barsData ? (
            <PriceChart
              bars={barsData.bars}
              eventMarkers={barsData.event_markers}
              indicators={indicators}
              indicatorSeries={indicatorsData?.indicators ?? []}
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
    </div>
  );
}
