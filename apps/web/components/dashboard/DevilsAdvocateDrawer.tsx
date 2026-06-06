"use client";

import type { ThesisDevilsAdvocate } from "@/lib/api";
import { useEffect } from "react";

interface Props {
  open: boolean;
  loading: boolean;
  error: string | null;
  review: ThesisDevilsAdvocate | null;
  onClose: () => void;
}

function ListSection({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
}) {
  return (
    <div className="flex flex-col gap-2 border-t border-line-1 pt-4">
      <h3 className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-xs text-ink-4 italic">{emptyMessage}</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {items.map((item, i) => (
            <li
              // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
              key={`${title}-${i}`}
              className="flex gap-2.5 text-sm text-ink-2 leading-relaxed"
            >
              <span className="font-mono tabular-nums text-ink-4 shrink-0">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function DevilsAdvocateDrawer({
  open,
  loading,
  error,
  review,
  onClose,
}: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    // biome-ignore lint/a11y/useSemanticElements: custom backdrop drawer; native <dialog> would change the click-outside model. Escape handled via window keydown.
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Devil's advocate review"
      className="fixed inset-0 z-[1000] flex justify-end"
      style={{ background: "rgba(10, 10, 9, 0.82)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="w-full max-w-xl h-full overflow-y-auto border-l border-line-2 bg-surface-1 p-6 flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4 border-b border-line-1 pb-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
              ─── Devil's Advocate
            </span>
            <h2 className="font-serif text-[24px] leading-none text-ink-1">
              The{" "}
              <span className="italic" style={{ color: "var(--gold-bright)" }}>
                other side
              </span>{" "}
              of your thesis
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-3 hover:text-ink-1 text-lg leading-none -mt-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-ink-3 font-mono">
            Arguing the other side…
          </p>
        ) : error ? (
          <p className="text-sm text-down font-mono">{error}</p>
        ) : review ? (
          <>
            <div className="flex flex-col gap-2">
              <h3 className="font-mono text-[10px] uppercase tracking-eyebrow text-down">
                Steelmanned counter-case
              </h3>
              <p className="text-sm text-ink-1 leading-relaxed border-l-2 border-down pl-3">
                {review.counter_thesis || "No counter-case surfaced."}
              </p>
            </div>
            <ListSection
              title="Pre-mortem — how this fails"
              items={review.premortem}
              emptyMessage="No failure modes surfaced."
            />
            <ListSection
              title="What would change your mind"
              items={review.invalidation_signals}
              emptyMessage="No invalidation signals surfaced."
            />

            <div className="border-t border-line-1 pt-4 mt-auto flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
                Safety
              </span>
              <p className="text-xs text-ink-3 leading-relaxed">
                Confidence:{" "}
                <span className="text-ink-2">{review.safety.confidence}</span>
                {" · "}As of:{" "}
                <span className="text-ink-2 font-mono tabular-nums">
                  {new Date(review.safety.as_of).toISOString().slice(0, 16)}Z
                </span>
              </p>
              {review.safety.caveats.map((c, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
                <p key={i} className="text-xs text-ink-4 leading-relaxed">
                  • {c}
                </p>
              ))}
              <p className="text-xs text-ink-4 italic mt-1">
                {review.safety.disclaimer}
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
