import type { SafetyEnvelope } from "@/app/(app)/signals/types";
import { HelpTip } from "@/components/HelpTip";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";
import { FileText } from "lucide-react";

interface Props {
  explanation: string | null;
  safety: SafetyEnvelope;
}

export function ExplanationPanel({ explanation, safety }: Props) {
  return (
    <div className="card-interactive border border-line-1 bg-surface-1 p-4 flex flex-col gap-4 h-full">
      <div className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-eyebrow text-accent">
        <FileText
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        Explanation
        <HelpTip k="explanation" className="ml-1" />
      </div>
      {explanation ? (
        <p className="min-h-0 flex-1 overflow-y-auto text-sm text-ink-2 leading-relaxed">
          {explanation}
        </p>
      ) : (
        <p className="text-sm text-ink-4 italic">
          Explanation unavailable — see per-model factors above.
        </p>
      )}
      <SafetyEnvelopeNote envelope={safety} defaultOpen={false} />
    </div>
  );
}
