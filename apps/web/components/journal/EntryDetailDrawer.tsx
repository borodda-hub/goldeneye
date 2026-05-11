"use client";

import { ConfidenceBar } from "../ConfidenceBar";
import { SafetyEnvelopeNote } from "../SafetyEnvelopeNote";
import type { JournalEntry } from "../../app/(app)/journal/types";

interface Props {
  entry: JournalEntry;
  onClose: () => void;
}

function bandFromPct(pct: number): "low" | "medium" | "high" {
  if (pct <= 33) return "low";
  if (pct <= 66) return "medium";
  return "high";
}

function splitToBullets(text: string): string[] {
  return text
    .split(/\n+/)
    .map((line) => line.replace(/^[-*\d.\s]+/, "").trim())
    .filter((line) => line.length > 0);
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
        {label}
      </span>
      {children}
    </div>
  );
}

export function EntryDetailDrawer({ entry, onClose }: Props) {
  const bullets = entry.llm_review
    ? splitToBullets(entry.llm_review.text)
    : [];

  return (
    <div
      className="border border-line-1 bg-surface-1 p-3 flex flex-col gap-3 max-h-[80vh] overflow-auto"
      data-testid="entry-detail-drawer"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Entry Detail
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close detail"
          className="font-mono text-xs text-ink-4 hover:text-ink-2"
        >
          ×
        </button>
      </div>

      <Section label="Hypothesis">
        <p className="text-sm text-ink-1 leading-relaxed whitespace-pre-wrap">
          {entry.hypothesis}
        </p>
      </Section>

      <Section label="Confidence">
        <div className="flex items-center gap-3">
          <ConfidenceBar confidence={bandFromPct(entry.confidence_pct)} />
          <span className="font-mono text-xs text-ink-2 tabular-nums">
            {entry.confidence_pct}%
          </span>
        </div>
      </Section>

      {entry.evidence.length > 0 && (
        <Section label="Evidence">
          <ul className="flex flex-col gap-1">
            {entry.evidence.map((ev, i) => (
              <li
                key={i}
                className="text-xs text-ink-2 leading-relaxed font-mono"
              >
                <span className="text-ink-4">[{ev.source}]</span> {ev.summary}{" "}
                <span className="text-ink-4 tabular-nums">
                  ({ev.weight.toFixed(2)})
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {entry.planned_action && (
        <Section label="Planned Action">
          <p className="text-xs text-ink-2 leading-relaxed whitespace-pre-wrap">
            {entry.planned_action}
          </p>
        </Section>
      )}

      {entry.risk_factors && entry.risk_factors.length > 0 && (
        <Section label="Risk Factors">
          <div className="flex flex-wrap gap-1">
            {entry.risk_factors.map((rf, i) => (
              <span
                key={i}
                className="font-mono text-[10px] text-ink-3 border border-line-1 px-1.5 py-0.5"
              >
                {rf}
              </span>
            ))}
          </div>
        </Section>
      )}

      {entry.invalidation_criteria && (
        <Section label="Invalidation Criteria">
          <p className="text-xs text-ink-2 leading-relaxed whitespace-pre-wrap">
            {entry.invalidation_criteria}
          </p>
        </Section>
      )}

      <div className="border-t border-line-1 pt-3 flex flex-col gap-2">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          LLM Review
        </span>
        {entry.llm_review ? (
          <>
            <ul
              className="list-disc list-inside space-y-1 text-xs text-ink-2 leading-relaxed"
              data-testid="llm-review-bullets"
            >
              {bullets.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
            <SafetyEnvelopeNote
              envelope={entry.llm_review.safety}
              defaultOpen={true}
            />
          </>
        ) : (
          <p className="text-xs text-ink-4 font-mono italic">
            Review pending…
          </p>
        )}
      </div>

      {(entry.outcome || entry.reflection) && (
        <div className="border-t border-line-1 pt-3 flex flex-col gap-2">
          {entry.outcome && (
            <Section label="Outcome">
              <p className="text-xs text-ink-2 leading-relaxed">
                {entry.outcome}
              </p>
            </Section>
          )}
          {entry.reflection && (
            <Section label="Reflection">
              <p className="text-xs text-ink-2 leading-relaxed whitespace-pre-wrap">
                {entry.reflection}
              </p>
            </Section>
          )}
        </div>
      )}
    </div>
  );
}
