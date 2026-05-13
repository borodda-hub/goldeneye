"use client";

import { useEffect, useState } from "react";
import type { StepSide, WalkthroughStep } from "./steps";

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const SPOTLIGHT_PAD = 8; // px around the target element
const TOOLTIP_GAP = 16; // px between spotlight and tooltip
const TOOLTIP_WIDTH = 380; // px

interface Props {
  steps: WalkthroughStep[];
  stepIndex: number;
  onNext: () => void;
  onPrev: () => void;
  onClose: () => void;
}

function getTargetRect(selector: string | null): Rect | null {
  if (!selector || typeof window === "undefined") return null;
  const el = document.querySelector(selector);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    top: Math.max(0, r.top - SPOTLIGHT_PAD),
    left: Math.max(0, r.left - SPOTLIGHT_PAD),
    width: r.width + SPOTLIGHT_PAD * 2,
    height: r.height + SPOTLIGHT_PAD * 2,
  };
}

function tooltipPosition(
  rect: Rect | null,
  side: StepSide,
  viewport: { w: number; h: number },
): { top: number; left: number } {
  // No target: centered modal.
  if (!rect) {
    return {
      top: Math.max(40, viewport.h / 2 - 140),
      left: Math.max(16, viewport.w / 2 - TOOLTIP_WIDTH / 2),
    };
  }

  // Try the requested side first; flip if it would overflow.
  let top = 0;
  let left = 0;

  switch (side) {
    case "bottom":
      top = rect.top + rect.height + TOOLTIP_GAP;
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2;
      break;
    case "top":
      top = rect.top - TOOLTIP_GAP - 220;
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2;
      break;
    case "right":
      top = rect.top + rect.height / 2 - 100;
      left = rect.left + rect.width + TOOLTIP_GAP;
      break;
    case "left":
      top = rect.top + rect.height / 2 - 100;
      left = rect.left - TOOLTIP_GAP - TOOLTIP_WIDTH;
      break;
    case "center":
    default:
      top = viewport.h / 2 - 140;
      left = viewport.w / 2 - TOOLTIP_WIDTH / 2;
  }

  // Clamp into viewport with 16 px margin.
  if (left < 16) left = 16;
  if (left + TOOLTIP_WIDTH > viewport.w - 16) {
    left = viewport.w - 16 - TOOLTIP_WIDTH;
  }
  if (top < 16) top = 16;
  if (top + 240 > viewport.h - 16) top = viewport.h - 16 - 240;

  return { top, left };
}

export function WalkthroughOverlay({
  steps,
  stepIndex,
  onNext,
  onPrev,
  onClose,
}: Props) {
  const step = steps[stepIndex];
  const isLast = stepIndex === steps.length - 1;
  const isFirst = stepIndex === 0;

  const [rect, setRect] = useState<Rect | null>(null);
  const [viewport, setViewport] = useState({
    w: typeof window !== "undefined" ? window.innerWidth : 1440,
    h: typeof window !== "undefined" ? window.innerHeight : 900,
  });

  // Re-measure on step change, scroll, or resize.  When a step is on a
  // different route from the previous one the target won't exist yet —
  // poll every 100 ms for up to ~4 s so the spotlight catches up after
  // the new page mounts.
  useEffect(() => {
    let cancelled = false;
    const recompute = () => {
      if (cancelled) return;
      setRect(getTargetRect(step.targetSelector));
      setViewport({ w: window.innerWidth, h: window.innerHeight });
    };
    recompute();
    const raf = requestAnimationFrame(recompute);

    // Poll until target appears or we hit the timeout.
    let pollId: number | undefined;
    if (step.targetSelector) {
      let elapsed = 0;
      pollId = window.setInterval(() => {
        if (cancelled) return;
        elapsed += 100;
        const next = getTargetRect(step.targetSelector);
        if (next) {
          setRect(next);
          if (pollId !== undefined) window.clearInterval(pollId);
        }
        if (elapsed >= 4000 && pollId !== undefined) {
          window.clearInterval(pollId);
        }
      }, 100);
    }

    window.addEventListener("resize", recompute);
    window.addEventListener("scroll", recompute, true);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      if (pollId !== undefined) window.clearInterval(pollId);
      window.removeEventListener("resize", recompute);
      window.removeEventListener("scroll", recompute, true);
    };
  }, [step.targetSelector]);

  // Keyboard: Esc closes, arrows navigate.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        if (isLast) onClose();
        else onNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        if (!isFirst) onPrev();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isFirst, isLast, onClose, onNext, onPrev]);

  const tooltip = tooltipPosition(rect, step.side, viewport);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Walkthrough — step ${stepIndex + 1} of ${steps.length}: ${step.title}`}
      className="fixed inset-0 z-[9999] pointer-events-none"
    >
      {/* Spotlight — a tiny element with a huge box-shadow creates the
          dimming around it without needing an SVG mask. Falls back to a
          plain backdrop when there's no target. */}
      {rect ? (
        <div
          aria-hidden="true"
          className="absolute pointer-events-auto"
          style={{
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            boxShadow: "0 0 0 9999px rgba(10, 10, 9, 0.78)",
            border: "1px solid var(--gold)",
            borderRadius: 4,
            transition:
              "top 220ms ease-out, left 220ms ease-out, width 220ms ease-out, height 220ms ease-out",
          }}
          onClick={onClose}
        />
      ) : (
        <div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-auto"
          style={{ background: "rgba(10, 10, 9, 0.78)" }}
          onClick={onClose}
        />
      )}

      {/* Tooltip card */}
      <div
        className="absolute pointer-events-auto border border-line-2 bg-surface-1 p-5 flex flex-col gap-3 shadow-2xl"
        style={{
          top: tooltip.top,
          left: tooltip.left,
          width: TOOLTIP_WIDTH,
        }}
        data-testid="walkthrough-tooltip"
      >
        <div className="flex items-baseline justify-between gap-3 border-b border-line-1 pb-2">
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
            ─── {step.id}
          </span>
          <span className="font-mono text-[10px] tabular-nums text-ink-3">
            {String(stepIndex + 1).padStart(2, "0")} / {String(steps.length).padStart(2, "0")}
          </span>
        </div>

        <h3 className="font-serif text-[22px] leading-tight text-ink-1 tracking-[-0.01em]">
          {step.title}
        </h3>

        <p className="text-sm text-ink-2 leading-relaxed">{step.body}</p>

        {/* Progress dots */}
        <div className="flex items-center gap-1.5 mt-1">
          {steps.map((_, i) => (
            <span
              key={i}
              className={`inline-block h-1 w-4 transition-colors ${
                i === stepIndex
                  ? "bg-accent"
                  : i < stepIndex
                  ? "bg-accent-deep"
                  : "bg-line-2"
              }`}
              aria-hidden="true"
            />
          ))}
        </div>

        <div className="flex items-center justify-between gap-2 mt-2">
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 hover:text-ink-1 transition-colors"
            aria-label="Skip walkthrough"
          >
            Skip tour
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onPrev}
              disabled={isFirst}
              className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2.5 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ← Back
            </button>
            <button
              type="button"
              onClick={isLast ? onClose : onNext}
              className="font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-3 py-1 text-accent-bright hover:bg-accent hover:text-bg"
            >
              {isLast ? "Done" : "Next →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
