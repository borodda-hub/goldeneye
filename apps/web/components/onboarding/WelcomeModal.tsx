"use client";

import { useOnboarding } from "@/lib/onboarding";
import { useEffect } from "react";
import { useWalkthrough } from "./WalkthroughProvider";

/**
 * Gentle first-run welcome. Unlike the old forced spotlight, this mounts only
 * after the dashboard has rendered (gated on `hydrated`) and never dims the page
 * behind a tour. It frames Goldeneye's human-in-the-loop value prop and offers
 * the opt-in tour or self-guided exploration. Modal chrome mirrors
 * components/chart/ChartSettingsModal.tsx.
 */
export function WelcomeModal() {
  const { hydrated, seen, markSeen } = useOnboarding();
  const { start } = useWalkthrough();
  const show = hydrated && !seen;

  useEffect(() => {
    if (!show) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") markSeen();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [show, markSeen]);

  if (!show) return null;

  const takeTour = () => {
    markSeen();
    start();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Dismiss welcome"
        className="absolute inset-0 bg-black/60"
        onClick={markSeen}
      />
      {/* biome-ignore lint/a11y/useSemanticElements: custom overlay modal; matches ChartSettingsModal/WalkthroughOverlay which manage their own backdrop + Escape. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Welcome to Goldeneye"
        className="fade-up relative w-full max-w-lg rounded-md border border-line-2 bg-surface-1 p-6 shadow-2xl"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent-deep">
          Welcome
        </span>
        <h2
          className="mt-1 font-serif text-[26px] font-light leading-tight tracking-[-0.02em] text-ink-1"
          style={{ fontVariationSettings: '"opsz" 72, "SOFT" 30' }}
        >
          Goldeneye is a human-in-the-loop research terminal.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-ink-2">
          You bring the thesis. Goldeneye synthesizes scenarios and signals —
          with explicit uncertainty and the counterargument, never a
          recommendation — and scores your judgment over time. You're viewing
          seeded demo data.
        </p>

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={markSeen}
            className="order-2 inline-flex items-center justify-center border border-line-1 px-4 py-2 font-mono text-[11px] uppercase tracking-widest text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink-1 sm:order-1"
            data-testid="welcome-explore"
          >
            Explore on my own
          </button>
          <button
            type="button"
            onClick={takeTour}
            className="order-1 inline-flex items-center justify-center border border-accent bg-accent-soft px-4 py-2 font-mono text-[11px] uppercase tracking-widest text-accent-bright transition-colors hover:bg-accent hover:text-bg sm:order-2"
            data-testid="welcome-take-tour"
          >
            Take the 2-min tour
          </button>
        </div>
      </div>
    </div>
  );
}
