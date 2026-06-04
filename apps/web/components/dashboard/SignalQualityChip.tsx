"use client";

import type { SignalQualityGrade, SignalQualityResponse } from "@/lib/api";
import { useSignalQuality } from "@/lib/queries";
import { useEffect, useRef, useState } from "react";

const GRADE_STYLES: Record<SignalQualityGrade, string> = {
  "A+": "bg-up-soft text-up border-up/40",
  A: "bg-up-soft text-up border-up/40",
  B: "bg-accent-soft text-accent-bright border-accent/40",
  C: "bg-accent-soft text-conf-low border-accent-deep/40",
  D: "bg-down-soft text-down border-down/40",
};

const SUB_SCORE_LABELS: Record<
  keyof SignalQualityResponse["sub_scores"],
  string
> = {
  input_diversity: "Input diversity",
  model_agreement: "Model agreement",
  regime_stability: "Regime stability",
  time_to_decision: "Data freshness",
};

interface Props {
  symbol?: string;
}

function ScoreBar({
  label,
  score,
  max,
  detail,
}: {
  label: string;
  score: number;
  max: number;
  detail?: string;
}) {
  const pct = max > 0 ? Math.round((score / max) * 100) : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          {label}
        </span>
        <span className="font-mono tabular-nums text-xs text-ink-1">
          {score}
          <span className="text-ink-4">/{max}</span>
        </span>
      </div>
      <div className="h-1.5 w-full bg-surface-2">
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
      {detail ? <span className="text-[10px] text-ink-4">{detail}</span> : null}
    </div>
  );
}

function Popover({
  data,
  onClose,
}: {
  data: SignalQualityResponse;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const minutes = data.detail.minutes_since_freshness_adapter;
  return (
    <div
      ref={ref}
      // biome-ignore lint/a11y/useSemanticElements: anchored click-outside popup; native <dialog> would break absolute positioning and focus model
      role="dialog"
      aria-label="Signal Quality breakdown"
      className="absolute right-0 top-full mt-2 z-50 w-72 border border-line-2 bg-surface-1 p-4 flex flex-col gap-3 shadow-xl"
    >
      <div className="flex items-baseline justify-between border-b border-line-1 pb-2">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Signal Quality
        </span>
        <span className="font-serif text-2xl text-ink-1 leading-none">
          {data.grade}
        </span>
      </div>
      <ScoreBar
        label={SUB_SCORE_LABELS.input_diversity}
        score={data.sub_scores.input_diversity}
        max={data.sub_score_max.input_diversity}
        detail={`adapter coverage: ${data.detail.input_diversity}`}
      />
      <ScoreBar
        label={SUB_SCORE_LABELS.model_agreement}
        score={data.sub_scores.model_agreement}
        max={data.sub_score_max.model_agreement}
        detail={`${data.detail.model_agreement_max} of ${data.detail.model_agreement_total} models aligned`}
      />
      <ScoreBar
        label={SUB_SCORE_LABELS.regime_stability}
        score={data.sub_scores.regime_stability}
        max={data.sub_score_max.regime_stability}
        detail={`${data.detail.regime_stability} (${data.detail.distinct_regimes_14d} distinct regimes / 14d)`}
      />
      <ScoreBar
        label={SUB_SCORE_LABELS.time_to_decision}
        score={data.sub_scores.time_to_decision}
        max={data.sub_score_max.time_to_decision}
        detail={
          minutes === null
            ? "no recent adapter runs"
            : `latest run ${minutes}m ago (${data.detail.time_to_decision_bucket})`
        }
      />
      <div className="flex justify-between border-t border-line-1 pt-2">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          Total
        </span>
        <span className="font-mono tabular-nums text-sm text-accent-bright">
          {data.total_score}
          <span className="text-ink-4">/100</span>
        </span>
      </div>
    </div>
  );
}

export function SignalQualityChip({ symbol = "NG" }: Props) {
  const { data, isLoading } = useSignalQuality(symbol);
  const [open, setOpen] = useState(false);

  if (isLoading || !data) {
    return (
      <span className="rounded-full px-2 py-0.5 text-xs font-mono bg-surface-2 text-ink-4">
        SQ: …
      </span>
    );
  }

  const style = GRADE_STYLES[data.grade] ?? GRADE_STYLES.D;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Signal Quality ${data.grade}, total ${data.total_score} out of 100`}
        className={`rounded-full px-2 py-0.5 text-xs font-mono tabular-nums border ${style} hover:opacity-90`}
        data-testid="signal-quality-chip"
      >
        SQ: <span className="font-semibold">{data.grade}</span>
      </button>
      {open ? <Popover data={data} onClose={() => setOpen(false)} /> : null}
    </div>
  );
}
