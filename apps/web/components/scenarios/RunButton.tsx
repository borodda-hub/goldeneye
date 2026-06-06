"use client";

import { Loader2, Play } from "lucide-react";

interface Props {
  disabled: boolean;
  running: boolean;
  onRun: () => void;
}

/** The Scenario Lab hero action. When ready it's a filled, glowing green CTA
 *  (theme `up` token, so it stays on-palette); muted when nothing to run. */
export function RunButton({ disabled, running, onRun }: Props) {
  const ready = !disabled && !running;

  const state = ready
    ? "border-up bg-up text-surface-0 hover:brightness-110 run-cta"
    : running
      ? "border-up/60 bg-up/15 text-up"
      : "border-line-1 text-ink-4 cursor-not-allowed";

  return (
    <button
      type="button"
      onClick={onRun}
      disabled={disabled || running}
      aria-busy={running}
      className={`flex items-center gap-2 rounded-sm border px-5 py-2.5 font-mono text-[13px] font-semibold uppercase tracking-widest transition-all ${state}`}
    >
      {running ? (
        <>
          <Loader2 size={15} strokeWidth={2.5} className="animate-spin" />
          Running…
        </>
      ) : (
        <>
          <Play size={15} strokeWidth={2.5} aria-hidden="true" />
          Run Scenario
        </>
      )}
    </button>
  );
}
