"use client";

import { ResizableColumn } from "@/components/ResizableColumn";
import { ResizableSplit } from "@/components/ResizableSplit";
import { AiThesisCard } from "@/components/dashboard/AiThesisCard";
import { DashboardLiveBar } from "@/components/dashboard/DashboardLiveBar";
import { DashboardTicker } from "@/components/dashboard/DashboardTicker";
import { DirectionalBiasCard } from "@/components/dashboard/DirectionalBiasCard";
import { FuturesCurveCard } from "@/components/dashboard/FuturesCurveCard";
import { HeaderRow } from "@/components/dashboard/HeaderRow";
import { OpenPositionsCard } from "@/components/dashboard/OpenPositionsCard";
import { PaperEquityCard } from "@/components/dashboard/PaperEquityCard";
import { RecentTradesCard } from "@/components/dashboard/RecentTradesCard";
import { PriceMiniChart } from "@/components/dashboard/PriceMiniChart";
import { RecentEventsList } from "@/components/dashboard/RecentEventsList";
import { WorkingThesisCard } from "@/components/dashboard/WorkingThesisCard";
import { WatchlistSidebar } from "@/components/instruments/WatchlistSidebar";
import { useDashboardSummary } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import type { DashboardSummary } from "./types";

interface Props {
  initialData: DashboardSummary | null;
  initialSymbol: string;
}

function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`border border-line-1 rounded-md bg-surface-1 animate-pulse ${className}`}
    />
  );
}

export function DashboardShell({ initialData, initialSymbol }: Props) {
  const { activeSymbol } = useActiveInstrument();
  // Use the URL-derived symbol if it matches the server-prefetched one;
  // otherwise the client-side query refetches with the new symbol.
  const symbol = activeSymbol;
  const { data: fetchedData } = useDashboardSummary(symbol);
  const fromQuery = fetchedData as DashboardSummary | undefined;
  // Initial SSR payload is for initialSymbol; only use it when nothing newer
  // has come back from the client-side hook.
  const summary = fromQuery ?? (symbol === initialSymbol ? initialData : null);

  const { data: tick, status } = useChannel<{
    ts: string;
    price: number;
    delayed?: boolean;
  }>(`price.${symbol}.front`);
  const feedMode: "live" | "delayed" = tick?.delayed ? "delayed" : "live";

  return (
    <div className="flex items-start">
      {/* Left rail: watchlist (sticky, resizable right edge) */}
      <ResizableColumn
        side="right"
        defaultWidth={240}
        minWidth={200}
        maxWidth={400}
        storageKey="goldeneye:dashboard:watchlist-width"
        className="sticky top-0 self-start"
      >
        <WatchlistSidebar className="pr-2" />
      </ResizableColumn>

      {/* Main column */}
      <div className="flex-1 min-w-0 flex flex-col gap-4 px-4">
        {!summary ? (
          <>
            <SkeletonCard className="h-10" />
            <SkeletonCard className="h-32" />
            <div className="flex gap-4 h-[42vh] min-h-[320px]">
              <SkeletonCard className="flex-1 min-h-0" />
              <SkeletonCard className="w-72 shrink-0" />
            </div>
            <div className="flex gap-4 h-[20vh] min-h-[160px]">
              <SkeletonCard className="flex-1" />
              <SkeletonCard className="flex-1" />
            </div>
            <SkeletonCard className="h-8" />
          </>
        ) : (
          <>
            {/* Row 1: Header */}
            <HeaderRow
              instrument={summary.instrument}
              frontMonth={summary.front_month}
              volRegime={summary.vol_regime}
              livePrice={tick?.price}
              wsStatus={status}
              feedMode={feedMode}
            />

            {/* Row 2a: AI Thesis (per-instrument synthesis). Tolerate older API
                payloads that predate the ai_thesis field by simply not rendering. */}
            {summary.ai_thesis && (
              <AiThesisCard
                instrument={summary.instrument}
                thesis={summary.ai_thesis}
              />
            )}

            {/* Row 2b: Working Thesis (user-authored) */}
            <WorkingThesisCard instrumentCode={summary.instrument.symbol} />

            {/* Row 3: Chart + Bias — drag the divider to resize. Width
                persists per-user via localStorage. */}
            <ResizableSplit
              className="h-[42vh] min-h-[320px]"
              storageKey="goldeneye:dashboard:bias-width"
              defaultRightWidth={288}
              rightMinWidth={240}
              leftMinWidth={320}
              left={
                <div className="h-full min-h-0 pr-2">
                  <PriceMiniChart
                    contractCode={summary.front_month.contract_code}
                    symbol={summary.instrument.symbol}
                  />
                </div>
              }
              right={
                <div className="h-full pl-2">
                  <DirectionalBiasCard
                    bias={summary.directional_bias}
                    aiSummary={summary.ai_summary}
                    safety={summary.safety}
                  />
                </div>
              }
            />

            {/* Row 4: Curve + Events — resizable divider, scales with viewport */}
            <ResizableSplit
              className="h-[20vh] min-h-[160px]"
              storageKey="goldeneye:dashboard:curve-events-width"
              defaultRightWidth={420}
              rightMinWidth={240}
              leftMinWidth={280}
              left={
                <div className="h-full pr-2">
                  <FuturesCurveCard curve={summary.futures_curve} />
                </div>
              }
              right={
                <div className="h-full pl-2">
                  <RecentEventsList events={summary.recent_events} />
                </div>
              }
            />

            {/* Row 5: Live bar */}
            <DashboardLiveBar />

            {/* Row 6: Macro chyron — indices + commodities + macro pairs */}
            <DashboardTicker />
          </>
        )}
      </div>

      {/* Right rail: paper equity + open positions + recent trades.
          Resizable left edge. */}
      <ResizableColumn
        side="left"
        defaultWidth={320}
        minWidth={260}
        maxWidth={480}
        storageKey="goldeneye:dashboard:rail-width"
        className="sticky top-0 self-start"
      >
        <aside
          aria-label="Paper trading rail"
          className="flex flex-col gap-3 pl-2"
        >
          <PaperEquityCard />
          <OpenPositionsCard />
          <RecentTradesCard />
        </aside>
      </ResizableColumn>
    </div>
  );
}
