import type { DirectionalBias, SafetyEnvelope } from "@/app/(app)/dashboard/types";
import { DirectionChip } from "@/components/DirectionChip";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";

interface Props {
  bias: DirectionalBias;
  aiSummary: string;
  safety: SafetyEnvelope;
}

export function DirectionalBiasCard({ bias, aiSummary, safety }: Props) {
  return (
    <div className="border border-line-1 rounded-md p-3 bg-surface-1 flex flex-col gap-3 h-full">
      <div className="text-ink-3 text-xs uppercase tracking-widest">
        Directional Bias
      </div>
      <div className="flex items-center gap-3">
        <DirectionChip direction={bias.direction} />
        <ConfidenceBar confidence={bias.confidence} />
        <span className="text-xs text-ink-3 font-mono">{bias.confidence}</span>
      </div>
      <p className="text-xs text-ink-2 leading-relaxed">{aiSummary}</p>
      <SafetyEnvelopeNote envelope={safety} defaultOpen={true} />
    </div>
  );
}
