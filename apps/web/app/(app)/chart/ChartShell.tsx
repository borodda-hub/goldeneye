"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useChartBars } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { ChartToolbar } from "@/components/chart/ChartToolbar";
import { EventDrawer } from "@/components/chart/EventDrawer";
import { ChartFooter } from "@/components/chart/ChartFooter";
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
}

const DEFAULT_CONTRACT = "NGM26";

function LoadingPlaceholder() {
  return (
    <div className="w-full h-full flex items-center justify-center text-ink-4 text-xs font-mono">
      Loading chart…
    </div>
  );
}

export function ChartShell({
  initialBars,
  contractCode = DEFAULT_CONTRACT,
}: Props) {
  const [resolution, setResolution] = useState<Resolution>("1d");
  const [showSMA20, setShowSMA20] = useState(true);
  const [showEMA50, setShowEMA50] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const today = new Date().toISOString().split("T")[0];
  const twoYearsAgo = new Date(Date.now() - 730 * 86400_000)
    .toISOString()
    .split("T")[0];

  const { data: fetchedBars } = useChartBars(
    contractCode,
    resolution,
    twoYearsAgo,
    today,
  );

  const { data: livebar } = useChannel<Bar>("price.NG.front.1m");
  void livebar; // live bar appending reserved for future enhancement

  const barsData = (fetchedBars as ChartBarsResponse | undefined) ?? initialBars;

  return (
    <div className="flex flex-col h-full">
      <ChartToolbar
        resolution={resolution}
        onResolutionChange={setResolution}
        showSMA20={showSMA20}
        showEMA50={showEMA50}
        onToggleSMA20={() => setShowSMA20((v) => !v)}
        onToggleEMA50={() => setShowEMA50((v) => !v)}
        contractCode={contractCode}
      />
      <div className="flex flex-1 min-h-0 gap-0">
        <div className="flex-1 min-w-0">
          {barsData ? (
            <PriceChart
              bars={barsData.bars}
              overlays={barsData.overlays}
              eventMarkers={barsData.event_markers}
              showSMA20={showSMA20}
              showEMA50={showEMA50}
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
    </div>
  );
}
