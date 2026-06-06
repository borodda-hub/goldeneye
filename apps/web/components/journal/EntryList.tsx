"use client";

import { NotebookPen } from "lucide-react";
import type { JournalEntry } from "../../app/(app)/journal/types";
import { ConfidenceBar } from "../ConfidenceBar";
import { resolutionLabel, resolutionStripeClass } from "./resolutionStyles";

interface Props {
  entries: JournalEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function fmtDate(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

function bandFromPct(pct: number): "low" | "medium" | "high" {
  if (pct <= 33) return "low";
  if (pct <= 66) return "medium";
  return "high";
}

export function EntryList({ entries, selectedId, onSelect }: Props) {
  if (entries.length === 0) {
    return (
      <div className="border border-line-1 bg-surface-1 p-4">
        <div className="flex flex-col items-center gap-1.5 py-6 text-ink-4">
          <NotebookPen size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px]">No journal entries yet</span>
          <span className="text-[10px] text-ink-4/70">
            Create one to get started.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {entries.map((entry) => {
        const selected = selectedId === entry.id;
        const hasReview = entry.llm_review !== null;
        const stripe = resolutionStripeClass(entry.resolved_direction);
        return (
          <button
            key={entry.id}
            type="button"
            onClick={() => onSelect(entry.id)}
            className={`card-interactive text-left border bg-surface-1 p-3 flex flex-col gap-2 hover:bg-surface-2 ${
              selected ? "border-accent" : "border-line-1"
            } ${stripe}`}
            data-testid="journal-entry-card"
            data-resolved={entry.resolved_direction ?? "null"}
            aria-label={`Journal entry — ${resolutionLabel(entry.resolved_direction)}`}
          >
            <p className="text-sm text-ink-1 line-clamp-2 leading-relaxed">
              {entry.hypothesis}
            </p>
            <div className="flex items-center gap-3">
              <ConfidenceBar confidence={bandFromPct(entry.confidence_pct)} />
              <span className="font-mono text-[10px] text-ink-3 tabular-nums">
                {entry.confidence_pct}%
              </span>
              <span className="font-mono text-[10px] text-ink-4 tabular-nums ml-auto">
                {fmtDate(entry.created_at)}
              </span>
              <span
                aria-label={hasReview ? "Review present" : "Review pending"}
                className={`inline-block h-2 w-2 rounded-full ${
                  hasReview ? "bg-accent" : "bg-surface-2 border border-line-2"
                }`}
                data-testid="review-dot"
                data-has-review={hasReview}
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}
