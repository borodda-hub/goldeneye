"use client";

import type { ThesisCritique } from "@/lib/api";
import { useEffect } from "react";

interface Props {
  open: boolean;
  loading: boolean;
  error: string | null;
  critique: ThesisCritique | null;
  onClose: () => void;
}

function Section({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
}) {
  return (
    <div className="flex flex-col gap-2 border-t border-line-1 pt-4 first:border-t-0 first:pt-0">
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

export function ThesisCritiqueDrawer({
  open,
  loading,
  error,
  critique,
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
    // biome-ignore lint/a11y/useSemanticElements: custom backdrop drawer; native <dialog> would change the click-outside backdrop and positioning model. Escape is handled via a window keydown listener.
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Thesis critique"
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
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-line-1 pb-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
              ─── Critique
            </span>
            <h2 className="font-serif text-[24px] leading-none text-ink-1">
              <span className="italic" style={{ color: "var(--gold-bright)" }}>
                Pushback
              </span>{" "}
              on your thesis
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
          <p className="text-sm text-ink-3 font-mono">Critiquing…</p>
        ) : error ? (
          <p className="text-sm text-down font-mono">{error}</p>
        ) : critique ? (
          <>
            <Section
              title="Missed risks"
              items={critique.missed_risks}
              emptyMessage="No additional risks surfaced."
            />
            <Section
              title="Blind spots"
              items={critique.blind_spots}
              emptyMessage="No blind spots flagged."
            />
            <Section
              title="Questions to answer"
              items={critique.questions}
              emptyMessage="No clarifying questions."
            />

            {/* Safety envelope */}
            <div className="border-t border-line-1 pt-4 mt-auto flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
                Safety
              </span>
              <p className="text-xs text-ink-3 leading-relaxed">
                Confidence:{" "}
                <span className="text-ink-2">{critique.safety.confidence}</span>
                {" · "}
                As of:{" "}
                <span className="text-ink-2 font-mono tabular-nums">
                  {new Date(critique.safety.as_of).toISOString().slice(0, 16)}Z
                </span>
              </p>
              {critique.safety.caveats.map((c, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
                <p key={i} className="text-xs text-ink-4 leading-relaxed">
                  • {c}
                </p>
              ))}
              <p className="text-xs text-ink-4 italic mt-1">
                {critique.safety.disclaimer}
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
