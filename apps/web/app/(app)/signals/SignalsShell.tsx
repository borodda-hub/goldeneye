"use client";

import { HelpTip } from "@/components/HelpTip";
import { PageHeader } from "@/components/PageHeader";
import { Skeleton } from "@/components/Skeleton";
import { BacktestCard } from "@/components/signals/BacktestCard";
import { EnsembleHeader } from "@/components/signals/EnsembleHeader";
import { ExplanationPanel } from "@/components/signals/ExplanationPanel";
import { HistoryTable } from "@/components/signals/HistoryTable";
import { ModelGrid } from "@/components/signals/ModelGrid";
import { NewsFeedPanel } from "@/components/signals/NewsFeedPanel";
import { useCurrentSignal } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { Radar } from "lucide-react";
import type { CurrentSignal } from "./types";

const signalsHeader = (
  <PageHeader
    icon={Radar}
    title="Signal Lab"
    subtitle="Model ensemble · directional signal"
    right={<HelpTip k="ensemble" />}
  />
);

interface Props {
  initialSignal: CurrentSignal | null;
  initialSymbol?: string;
}

export function SignalsShell({ initialSignal, initialSymbol = "NG" }: Props) {
  const { activeSymbol } = useActiveInstrument();
  const { data: fetchedData } = useCurrentSignal(activeSymbol);
  const fromQuery = fetchedData as CurrentSignal | undefined;
  const signal =
    fromQuery ?? (activeSymbol === initialSymbol ? initialSignal : null);

  useChannel<{ direction: string; confidence: string }>(
    `signal.${activeSymbol}`,
  );

  if (!signal) {
    return (
      <div className="stagger flex flex-col gap-4 h-full">
        {signalsHeader}
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
        <div className="flex gap-4 flex-1 min-h-0">
          <Skeleton className="flex-[3]" />
          <Skeleton className="flex-[2]" />
        </div>
      </div>
    );
  }

  return (
    <div className="stagger flex flex-col gap-4">
      {signalsHeader}

      {/* Row 1: Ensemble headline */}
      <EnsembleHeader ensemble={signal.ensemble} />

      {/* Row 2: Model cards */}
      <ModelGrid models={signal.models} />

      {/* Row 2.5: Backtest performance — per-model hit rates from persisted
          backtest forecasts. Sits above explanation+history because it sets
          the credibility frame ("these are the hit rates against real
          historical prices") before the live explanation prose. */}
      <BacktestCard symbol={activeSymbol} />

      {/* Row 3: Explanation + History */}
      <div className="flex gap-4 min-h-0 h-[40vh]">
        <div className="flex-[3] min-h-0">
          <ExplanationPanel
            explanation={signal.explanation}
            safety={signal.safety}
          />
        </div>
        <div className="flex-[2] min-h-0">
          <HistoryTable symbol={activeSymbol} />
        </div>
      </div>

      {/* Row 4: Supporting news feed */}
      <div className="min-h-0 h-[32vh]">
        <NewsFeedPanel symbol={activeSymbol} />
      </div>
    </div>
  );
}
