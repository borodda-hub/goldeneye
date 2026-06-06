import type {
  DirectionalBias,
  SafetyEnvelope,
} from "@/app/(app)/dashboard/types";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { HelpTip } from "@/components/HelpTip";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";
import { Compass } from "lucide-react";

interface Props {
  bias: DirectionalBias;
  aiSummary: string;
  safety: SafetyEnvelope;
}

const DIRECTION_TONE: Record<DirectionalBias["direction"], string> = {
  bullish: "text-up",
  bearish: "text-down",
  neutral: "text-flat",
};

const DIRECTION_LABEL: Record<DirectionalBias["direction"], string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Neutral",
};

const DIRECTION_GLYPH: Record<DirectionalBias["direction"], string> = {
  bullish: "▲",
  bearish: "▼",
  neutral: "→",
};

export function DirectionalBiasCard({ bias, aiSummary, safety }: Props) {
  const tone = DIRECTION_TONE[bias.direction];
  return (
    <div className="card-interactive border border-line-1 rounded-md p-4 bg-surface-1 flex flex-col gap-4 h-full">
      <div className="flex items-baseline justify-between">
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          <Compass
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Directional Bias
          <HelpTip k="directionalBias" className="ml-1" />
        </span>
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          {bias.confidence} confidence
        </span>
      </div>

      {/* Hero direction — large serif so the verdict is unmistakable */}
      <div
        className={`font-serif font-semibold text-5xl leading-none tracking-tight ${tone}`}
      >
        <span className="mr-2 text-4xl align-baseline">
          {DIRECTION_GLYPH[bias.direction]}
        </span>
        {DIRECTION_LABEL[bias.direction]}
      </div>

      <div className="flex items-center gap-3">
        <ConfidenceBar confidence={bias.confidence} />
        <span className="text-xs text-ink-2 font-mono uppercase tracking-widest">
          {bias.confidence}
        </span>
      </div>

      <p className="text-sm text-ink-1-soft leading-relaxed">{aiSummary}</p>

      <div className="mt-auto">
        <SafetyEnvelopeNote envelope={safety} defaultOpen={true} />
      </div>
    </div>
  );
}
