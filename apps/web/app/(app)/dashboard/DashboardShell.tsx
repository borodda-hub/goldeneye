"use client";

import { useDashboardSummary } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { HeaderRow } from "@/components/dashboard/HeaderRow";
import { DirectionalBiasCard } from "@/components/dashboard/DirectionalBiasCard";
import { PriceMiniChart } from "@/components/dashboard/PriceMiniChart";
import { FuturesCurveCard } from "@/components/dashboard/FuturesCurveCard";
import { RecentEventsList } from "@/components/dashboard/RecentEventsList";
import { DashboardLiveBar } from "@/components/dashboard/DashboardLiveBar";
import type { DashboardSummary } from "./types";

interface Props {
  initialData: DashboardSummary | null;
}

function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`border border-line-1 rounded-md bg-surface-1 animate-pulse ${className}`}
    />
  );
}

export function DashboardShell({ initialData }: Props) {
  const { data: fetchedData } = useDashboardSummary("NG");
  const summary = (fetchedData as DashboardSummary | undefined) ?? initialData;

  const { data: tick, status } = useChannel<{
    ts: string;
    price: number;
    delayed?: boolean;
  }>("price.NG.front");
  const feedMode: "live" | "delayed" = tick?.delayed ? "delayed" : "live";

  if (!summary) {
    return (
      <div className="flex flex-col gap-4 h-full">
        {/* Header skeleton */}
        <SkeletonCard className="h-10" />
        {/* Main area skeleton */}
        <div className="flex gap-4 flex-1 min-h-0">
          <SkeletonCard className="flex-1 min-h-0" />
          <SkeletonCard className="w-72 shrink-0" />
        </div>
        {/* Bottom row skeleton */}
        <div className="flex gap-4 h-44">
          <SkeletonCard className="flex-1" />
          <SkeletonCard className="flex-1" />
        </div>
        {/* Live bar skeleton */}
        <SkeletonCard className="h-8" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Row 1: Header */}
      <HeaderRow
        instrument={summary.instrument}
        frontMonth={summary.front_month}
        volRegime={summary.vol_regime}
        livePrice={tick?.price}
        wsStatus={status}
        feedMode={feedMode}
      />

      {/* Row 2: Chart + Bias */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-1 min-h-0">
          <PriceMiniChart
            volRegime={summary.vol_regime}
            contractCode={summary.front_month.contract_code}
          />
        </div>
        <div className="w-72 shrink-0">
          <DirectionalBiasCard
            bias={summary.directional_bias}
            aiSummary={summary.ai_summary}
            safety={summary.safety}
          />
        </div>
      </div>

      {/* Row 3: Curve + Events */}
      <div className="flex gap-4 h-44">
        <div className="flex-1">
          <FuturesCurveCard curve={summary.futures_curve} />
        </div>
        <div className="flex-1">
          <RecentEventsList events={summary.recent_events} />
        </div>
      </div>

      {/* Row 4: Live bar */}
      <DashboardLiveBar />
    </div>
  );
}
