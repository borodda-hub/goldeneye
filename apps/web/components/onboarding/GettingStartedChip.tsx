"use client";

import { useOnboarding } from "@/lib/onboarding";
import { ListChecks } from "lucide-react";

/**
 * TopBar entry that surfaces activation progress and re-opens a dismissed
 * checklist. Styled to match WalkthroughButton. Hidden once the loop is complete.
 */
export function GettingStartedChip({ className = "" }: { className?: string }) {
  const { hydrated, steps, completedCount, setDismissed } = useOnboarding();

  if (!hydrated || completedCount >= steps.length) return null;

  return (
    <button
      type="button"
      onClick={() => setDismissed(false)}
      aria-label="Open getting started checklist"
      className={`inline-flex items-center gap-1.5 border border-accent bg-accent-soft px-2.5 py-1 font-mono text-[10px] uppercase tracking-eyebrow text-accent-bright transition-colors hover:bg-accent hover:text-bg ${className}`}
      data-testid="getting-started-chip"
    >
      <ListChecks size={12} strokeWidth={1.75} aria-hidden="true" />
      Getting started · {completedCount}/{steps.length}
    </button>
  );
}
