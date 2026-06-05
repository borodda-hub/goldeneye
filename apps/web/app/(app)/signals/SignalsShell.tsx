"use client";

import { HelpTip } from "@/components/HelpTip";
import { BacktestCard } from "@/components/signals/BacktestCard";
import { EnsembleHeader } from "@/components/signals/EnsembleHeader";
import { ExplanationPanel } from "@/components/signals/ExplanationPanel";
import { HistoryTable } from "@/components/signals/HistoryTable";
import { ModelGrid } from "@/components/signals/ModelGrid";
import { NewsFeedPanel } from "@/components/signals/NewsFeedPanel";
import { useCurrentSignal } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import type { CurrentSignal } from "./types";

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
      <div className="flex flex-col gap-4 h-full">
        {/* Header — matches Scenario Lab */}
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-accent">
            Signal Lab
            <HelpTip k="ensemble" className="ml-2" />
          </h1>
          <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
            Multi-model forecast ensemble
          </span>
        </div>
        <div className="border border-line-1 bg-surface-1 h-24 animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="border border-line-1 bg-surface-1 h-44 animate-pulse"
            />
          ))}
        </div>
        <div className="flex gap-4 flex-1 min-h-0">
          <div className="flex-[3] border border-line-1 bg-surface-1 animate-pulse" />
          <div className="flex-[2] border border-line-1 bg-surface-1 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header — matches Scenario Lab */}
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-accent">
          Signal Lab
          <HelpTip k="ensemble" className="ml-2" />
        </h1>
        <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
          Multi-model forecast ensemble
        </span>
      </div>

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
