import type { SafetyEnvelope } from "@/app/(app)/signals/types";
import { HelpTip } from "@/components/HelpTip";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";

interface Props {
  explanation: string | null;
  safety: SafetyEnvelope;
}

export function ExplanationPanel({ explanation, safety }: Props) {
  return (
    <div className="border border-line-1 bg-surface-1 p-4 flex flex-col gap-4 h-full">
      <div className="text-[10px] font-mono text-ink-3 uppercase tracking-widest">
        Explanation
        <HelpTip k="explanation" className="ml-1" />
      </div>
      {explanation ? (
        <p className="text-sm text-ink-2 leading-relaxed">{explanation}</p>
      ) : (
        <p className="text-sm text-ink-4 italic">
          Explanation unavailable — see per-model factors above.
        </p>
      )}
      <SafetyEnvelopeNote envelope={safety} defaultOpen={true} />
    </div>
  );
}
