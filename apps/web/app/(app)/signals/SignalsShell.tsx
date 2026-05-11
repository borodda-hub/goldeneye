"use client";

import { useCurrentSignal } from "@/lib/queries";
import { useChannel } from "@/lib/realtime";
import { EnsembleHeader } from "@/components/signals/EnsembleHeader";
import { ModelGrid } from "@/components/signals/ModelGrid";
import { ExplanationPanel } from "@/components/signals/ExplanationPanel";
import { HistoryTable } from "@/components/signals/HistoryTable";
import type { CurrentSignal } from "./types";

interface Props {
  initialSignal: CurrentSignal | null;
}

export function SignalsShell({ initialSignal }: Props) {
  const { data: fetchedData } = useCurrentSignal("NG");
  const signal = (fetchedData as CurrentSignal | undefined) ?? initialSignal;

  useChannel<{ direction: string; confidence: string }>("signal.NG");

  if (!signal) {
    return (
      <div className="flex flex-col gap-4 h-full">
        <div className="border border-line-1 bg-surface-1 h-24 animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="border border-line-1 bg-surface-1 h-44 animate-pulse" />
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
    <div className="flex flex-col gap-4 h-full">
      {/* Row 1: Ensemble headline */}
      <EnsembleHeader ensemble={signal.ensemble} />

      {/* Row 2: Model cards */}
      <ModelGrid models={signal.models} />

      {/* Row 3: Explanation + History */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-[3] min-h-0">
          <ExplanationPanel explanation={signal.explanation} safety={signal.safety} />
        </div>
        <div className="flex-[2] min-h-0">
          <HistoryTable symbol="NG" />
        </div>
      </div>
    </div>
  );
}
