"use client";

import {
  FlaskConical,
  Gauge,
  LineChart,
  type LucideIcon,
  NotebookPen,
  Target,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

/**
 * First-session onboarding state — a gentle Welcome modal plus an auto-ticking
 * "Getting Started" checklist that mirrors Goldeneye's differentiated, human-in-
 * the-loop decision loop: frame a thesis → stress it with an AI-synthesized
 * scenario → log a decision and read the AI critique → practice a paper trade →
 * check your calibration.
 *
 * Storage + SSR-safe hydration + cross-tab sync follow the same pattern as
 * `lib/useChartColor.ts` and `lib/theme/ThemeProvider.tsx`. Same-tab updates are
 * propagated via a CustomEvent so the chip, card, and modal — separate hook
 * instances — stay in sync without a reload.
 */

export interface OnboardingStep {
  id: OnboardingStepId;
  label: string;
  /** One line naming the differentiated payoff of the step. */
  description: string;
  /** Where the row links to (the screen that hosts the action). */
  href: string;
  icon: LucideIcon;
}

export type OnboardingStepId =
  | "thesis"
  | "scenario"
  | "journal"
  | "paper"
  | "calibration";

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: "thesis",
    label: "Frame your Working Thesis",
    description:
      "The view you'll hold the AI accountable to — your conviction feeds calibration.",
    href: "/dashboard",
    icon: Target,
  },
  {
    id: "scenario",
    label: "Run an AI-synthesized scenario",
    description:
      "Shock the baseline; the AI narrates assumptions, the counterargument, and what would invalidate it.",
    href: "/scenarios",
    icon: FlaskConical,
  },
  {
    id: "journal",
    label: "Log a decision & get the AI critique",
    description:
      "The AI reviews decision quality — it never tells you to trade.",
    href: "/journal",
    icon: NotebookPen,
  },
  {
    id: "paper",
    label: "Practice with a paper trade",
    description: "Simulated round-trips — no real broker, no capital at risk.",
    href: "/paper",
    icon: LineChart,
  },
  {
    id: "calibration",
    label: "Check your calibration",
    description: "Conviction vs actual hit rate, with the DQ Coach.",
    href: "/calibration",
    icon: Gauge,
  },
];

const PREFIX = "goldeneye:onboarding";
const SEEN_KEY = `${PREFIX}:seen`;
const DISMISSED_KEY = `${PREFIX}:dismissed`;
const stepKey = (id: OnboardingStepId) => `${PREFIX}:step:${id}`;

/** Same-tab change signal (cross-tab uses the native `storage` event). */
export const ONBOARDING_EVENT = "goldeneye:onboarding";

function readFlag(key: string): boolean {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function writeFlag(key: string, value: boolean): void {
  try {
    if (value) localStorage.setItem(key, "1");
    else localStorage.removeItem(key);
  } catch {
    // localStorage unavailable (private mode, SSR) — in-memory state still updates.
  }
}

function emit(): void {
  try {
    window.dispatchEvent(new CustomEvent(ONBOARDING_EVENT));
  } catch {
    // no window (SSR) — nothing to notify.
  }
}

/** Mark a loop step done. No-op when already set, so repeated triggers (a chart
 *  re-mount, a second thesis edit) don't churn storage or spam the event. */
export function markStep(id: OnboardingStepId): void {
  const key = stepKey(id);
  if (readFlag(key)) return;
  writeFlag(key, true);
  emit();
}

export function markSeen(): void {
  if (readFlag(SEEN_KEY)) return;
  writeFlag(SEEN_KEY, true);
  emit();
}

export function setDismissed(value: boolean): void {
  writeFlag(DISMISSED_KEY, value);
  emit();
}

/** Clear all onboarding state (manual QA + tests). */
export function reset(): void {
  writeFlag(SEEN_KEY, false);
  writeFlag(DISMISSED_KEY, false);
  for (const step of ONBOARDING_STEPS) writeFlag(stepKey(step.id), false);
  emit();
}

export interface OnboardingState {
  steps: (OnboardingStep & { done: boolean })[];
  completedCount: number;
  seen: boolean;
  markSeen: () => void;
  dismissed: boolean;
  setDismissed: (value: boolean) => void;
  /** False until the first client-side read; gate UI on this to avoid SSR flash. */
  hydrated: boolean;
  reset: () => void;
}

export function useOnboarding(): OnboardingState {
  // Optimistic SSR defaults (see lib/useChartColor.ts): render the "nothing to
  // show" state first, then hydrate the real flags in an effect.
  const [seen, setSeen] = useState(false);
  const [dismissed, setDismissedState] = useState(false);
  const [done, setDone] = useState<Record<OnboardingStepId, boolean>>(
    () =>
      Object.fromEntries(ONBOARDING_STEPS.map((s) => [s.id, false])) as Record<
        OnboardingStepId,
        boolean
      >,
  );
  const [hydrated, setHydrated] = useState(false);

  const sync = useCallback(() => {
    setSeen(readFlag(SEEN_KEY));
    setDismissedState(readFlag(DISMISSED_KEY));
    setDone(
      Object.fromEntries(
        ONBOARDING_STEPS.map((s) => [s.id, readFlag(stepKey(s.id))]),
      ) as Record<OnboardingStepId, boolean>,
    );
  }, []);

  useEffect(() => {
    sync();
    setHydrated(true);
  }, [sync]);

  // Same-tab CustomEvent + cross-tab storage event (mirrors ThemeProvider).
  useEffect(() => {
    function onEvent() {
      sync();
    }
    function onStorage(e: StorageEvent) {
      if (e.key && !e.key.startsWith(PREFIX)) return;
      sync();
    }
    window.addEventListener(ONBOARDING_EVENT, onEvent);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(ONBOARDING_EVENT, onEvent);
      window.removeEventListener("storage", onStorage);
    };
  }, [sync]);

  const steps = ONBOARDING_STEPS.map((s) => ({ ...s, done: done[s.id] }));
  const completedCount = steps.filter((s) => s.done).length;

  return {
    steps,
    completedCount,
    seen,
    markSeen,
    dismissed,
    setDismissed,
    hydrated,
    reset,
  };
}
