"use client";

import { useWalkthrough } from "./WalkthroughProvider";

interface Props {
  className?: string;
}

/**
 * Top-bar button that launches the onboarding tutorial.  Styled with the
 * gold accent border to be findable in the chrome without dominating —
 * matches the "primary affordance" look used by Enter Terminal on the
 * landing page.
 */
export function WalkthroughButton({ className = "" }: Props) {
  const { start } = useWalkthrough();
  return (
    <button
      type="button"
      onClick={start}
      aria-label="Start onboarding tutorial"
      className={`inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-2.5 py-1 text-accent-bright hover:bg-accent hover:text-bg transition-colors ${className}`}
      data-testid="walkthrough-button"
    >
      <span aria-hidden="true">◎</span> Tutorial
    </button>
  );
}
