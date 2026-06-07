"use client";

import { HelpTip } from "@/components/HelpTip";
import { PageHeader } from "@/components/PageHeader";
import { Skeleton } from "@/components/Skeleton";
import { BacktestCard } from "@/components/signals/BacktestCard";
import { EnsembleHeader } from "@/components/signals/EnsembleHeader";
import { ExpectedRangeCard } from "@/components/signals/ExpectedRangeCard";
import { ExplanationPanel } from "@/components/signals/ExplanationPanel";
import { HistoryTable } from "@/components/signals/HistoryTable";
import { ModelCalibrationCard } from "@/components/signals/ModelCalibrationCard";
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

      {/* Row 1 — THE CALL (hero): direction, confidence, expected move. */}
      <EnsembleHeader ensemble={signal.ensemble} />

      {/* Row 1b — THE RANGE (how far): calibrated volatility band. Complements the
          directional call above; this is the forecast the system can stand behind. */}
      <ExpectedRangeCard symbol={activeSymbol} />

      {/* Row 2 — THE EVIDENCE: the per-model ensemble vote. */}
      <ModelGrid models={signal.models} />

      {/* Row 3 — THE TRACK RECORD (side by side): "did it work?" (backtest
          hit-rates) + "is its confidence honest?" (calibration + Brier). Paired
          so the credibility story reads as one, and to use the horizontal space
          instead of two stacked full-width bands. */}
      <div className="grid grid-cols-1 xl:grid-cols-[2fr_3fr] gap-4 items-start">
        <BacktestCard symbol={activeSymbol} />
        <ModelCalibrationCard symbol={activeSymbol} />
      </div>

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
