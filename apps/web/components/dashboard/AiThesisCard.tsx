"use client";

import type { ReactNode } from "react";
import type { AiThesis, Instrument } from "@/app/(app)/dashboard/types";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";

interface Props {
  instrument: Instrument;
  thesis: AiThesis;
}

const CURVE_LABEL: Record<AiThesis["curve_shape"], string> = {
  contango: "Contango",
  backwardation: "Backwardation",
  mixed: "Mixed curve",
  unknown: "Curve —",
};

// Keyword groups for inline highlighting. Order matters when a substring
// of one word would also match another — we sort longest-first when building
// the regex so "backwardation" wins over "back" (hypothetical).
const HIGHLIGHT_GROUPS: { className: string; words: string[] }[] = [
  {
    className: "font-semibold text-up",
    words: [
      "bullish",
      "backwardation",
      "supportive",
      "supports",
      "tightness",
      "tight",
      "constructive",
      "deficit",
      "draws",
      "draw",
      "strengthens",
      "strengthening",
      "rally",
      "gains",
      "upside",
      "upward",
    ],
  },
  {
    className: "font-semibold text-down",
    words: [
      "bearish",
      "contango",
      "oversupply",
      "surplus",
      "glut",
      "ample",
      "weakness",
      "weakening",
      "contradicts",
      "contradicting",
      "build",
      "builds",
      "declines",
      "declining",
      "downside",
      "downward",
    ],
  },
  {
    className: "font-semibold text-accent-bright",
    words: [
      "volatility",
      "regime",
      "ensemble",
      "basis",
      "confidence",
      "elevated",
      "compressed",
      "medium confidence",
      "high confidence",
      "low confidence",
    ],
  },
];

function buildHighlightRegex(): RegExp {
  const all: string[] = [];
  for (const g of HIGHLIGHT_GROUPS) all.push(...g.words);
  // Longest first so multi-word phrases (e.g. "medium confidence") match
  // before their constituent single-word entries.
  all.sort((a, b) => b.length - a.length);
  const escaped = all.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
}

function classForToken(token: string): string | null {
  const lower = token.toLowerCase();
  for (const g of HIGHLIGHT_GROUPS) {
    if (g.words.includes(lower)) return g.className;
  }
  return null;
}

const HIGHLIGHT_RE = buildHighlightRegex();

function renderHighlighted(text: string): ReactNode {
  if (!text) return null;
  const parts = text.split(HIGHLIGHT_RE);
  return parts.map((part, idx) => {
    const cls = classForToken(part);
    if (cls) {
      return (
        <span key={idx} className={cls}>
          {part}
        </span>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

export function AiThesisCard({ instrument, thesis }: Props) {
  const hasThesis = thesis.thesis.length > 0;
  return (
    <section
      aria-label="AI thesis"
      className="border border-line-1 rounded-md bg-surface-1 px-4 py-3 flex flex-col gap-3"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          AI Thesis · {instrument.symbol}
        </span>
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          {CURVE_LABEL[thesis.curve_shape]}
        </span>
      </div>

      {hasThesis ? (
        <p className="text-sm text-ink-3 leading-relaxed">
          {renderHighlighted(thesis.thesis)}
        </p>
      ) : (
        <p className="text-sm text-ink-4 italic">
          Thesis unavailable for this snapshot.
        </p>
      )}

      {(thesis.drivers.length > 0 || thesis.watch.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="font-mono text-[10px] text-ink-3 uppercase tracking-widest mb-1.5">
              Key drivers
            </div>
            {thesis.drivers.length === 0 ? (
              <span className="text-[11px] text-ink-4 font-mono">—</span>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {thesis.drivers.map((d) => (
                  <li
                    key={d}
                    className="text-[12px] text-ink-2 leading-snug flex gap-1.5"
                  >
                    <span className="text-up shrink-0">+</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <div className="font-mono text-[10px] text-ink-3 uppercase tracking-widest mb-1.5">
              Watch
            </div>
            {thesis.watch.length === 0 ? (
              <span className="text-[11px] text-ink-4 font-mono">—</span>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {thesis.watch.map((w) => (
                  <li
                    key={w}
                    className="text-[12px] text-ink-2 leading-snug flex gap-1.5"
                  >
                    <span className="text-conf-medium shrink-0">◇</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <SafetyEnvelopeNote envelope={thesis.safety} defaultOpen={false} />
    </section>
  );
}
