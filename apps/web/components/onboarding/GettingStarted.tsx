"use client";

import { useOnboarding } from "@/lib/onboarding";
import { Check } from "lucide-react";
import Link from "next/link";

/**
 * Auto-ticking activation checklist — the differentiated decision loop, in order.
 * Steps check off as the user actually performs the action (see markStep call
 * sites). Floats bottom-right, dismissible, and disappears once the loop is
 * complete. Gated on `hydrated` so it never flashes before the dashboard paints.
 */
export function GettingStarted() {
  const { hydrated, seen, dismissed, steps, completedCount, setDismissed } =
    useOnboarding();

  if (!hydrated || !seen || dismissed || completedCount >= steps.length) {
    return null;
  }

  return (
    <aside
      aria-label="Getting started checklist"
      className="fade-up fixed bottom-4 right-4 z-40 w-80 rounded-md border border-line-2 bg-surface-1 shadow-2xl"
    >
      <div className="flex items-center gap-2 border-b border-line-1 px-4 py-2.5">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Your first decision loop
        </span>
        <span className="ml-auto font-mono text-[11px] tabular-nums text-ink-2">
          {completedCount} / {steps.length}
        </span>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss checklist"
          className="text-ink-4 transition-colors hover:text-ink-1"
        >
          ✕
        </button>
      </div>

      <ol className="flex flex-col">
        {steps.map((step) => {
          const Icon = step.icon;
          const body = (
            <>
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                  step.done
                    ? "border-up bg-up-soft text-up"
                    : "border-line-1 text-ink-4"
                }`}
                aria-hidden="true"
              >
                {step.done ? (
                  <Check size={12} strokeWidth={2.5} />
                ) : (
                  <Icon size={12} strokeWidth={1.75} />
                )}
              </span>
              <span className="flex flex-col gap-0.5">
                <span
                  className={`text-[13px] leading-snug ${
                    step.done ? "text-ink-3 line-through" : "text-ink-1"
                  }`}
                >
                  {step.label}
                </span>
                <span className="text-[11px] leading-snug text-ink-3">
                  {step.description}
                </span>
              </span>
            </>
          );

          return (
            <li
              key={step.id}
              className="border-t border-line-1 first:border-t-0"
            >
              {step.done ? (
                <div className="flex gap-3 px-4 py-2.5">{body}</div>
              ) : (
                <Link
                  href={step.href}
                  className="flex gap-3 px-4 py-2.5 transition-colors hover:bg-surface-2"
                >
                  {body}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
