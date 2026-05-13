"use client";

import { useWalkthrough } from "./WalkthroughProvider";

interface Props {
  className?: string;
}

/**
 * Small top-bar button that launches the dashboard walkthrough.  Renders
 * as a faded mono pill that brightens to gold on hover, consistent with
 * the chrome's other affordances.
 */
export function WalkthroughButton({ className = "" }: Props) {
  const { start } = useWalkthrough();
  return (
    <button
      type="button"
      onClick={start}
      aria-label="Start onboarding walkthrough"
      className={`inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2 py-1 text-ink-3 hover:bg-surface-2 hover:text-accent hover:border-accent transition-colors ${className}`}
      data-testid="walkthrough-button"
    >
      <span aria-hidden="true">◎</span> Tour
    </button>
  );
}
