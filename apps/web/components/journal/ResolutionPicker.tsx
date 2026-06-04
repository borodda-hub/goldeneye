"use client";

import type { ResolvedDirection } from "@/app/(app)/journal/types";
import { usePatchJournalEntry } from "@/lib/queries";
import { useState } from "react";

interface Props {
  entryId: string;
  value: ResolvedDirection | null;
}

interface OptionDef {
  key: ResolvedDirection | null;
  label: string;
  tone: "up" | "down" | "flat" | "ink";
}

const OPTIONS: OptionDef[] = [
  { key: null, label: "Unresolved", tone: "ink" },
  { key: "hit", label: "Hit", tone: "up" },
  { key: "miss", label: "Miss", tone: "down" },
  { key: "neutral", label: "Neutral", tone: "flat" },
];

const TONE_STYLES: Record<
  OptionDef["tone"],
  { active: string; inactive: string }
> = {
  up: {
    active: "bg-up-soft text-up border-up/40",
    inactive: "text-ink-3 border-line-1 hover:text-up hover:border-up/40",
  },
  down: {
    active: "bg-down-soft text-down border-down/40",
    inactive: "text-ink-3 border-line-1 hover:text-down hover:border-down/40",
  },
  flat: {
    active: "bg-surface-2 text-flat border-line-2",
    inactive: "text-ink-3 border-line-1 hover:text-flat hover:border-line-2",
  },
  ink: {
    active: "bg-surface-2 text-ink-2 border-line-2",
    inactive: "text-ink-4 border-line-1 hover:text-ink-2 hover:border-line-2",
  },
};

export function ResolutionPicker({ entryId, value }: Props) {
  const mutation = usePatchJournalEntry();
  // Optimistic local mirror so the active option flips immediately.
  const [optimistic, setOptimistic] = useState<ResolvedDirection | null>(value);

  function pick(next: ResolvedDirection | null) {
    if (next === optimistic) return;
    setOptimistic(next);
    mutation.mutate(
      { id: entryId, body: { resolved_direction: next } },
      {
        onError: () => {
          // Roll back optimistic update on server failure.
          setOptimistic(value);
        },
      },
    );
  }

  return (
    <div
      className="flex items-center gap-1.5"
      role="radiogroup"
      aria-label="Resolution"
    >
      {OPTIONS.map((opt) => {
        const isActive = (optimistic ?? null) === opt.key;
        const cls = isActive
          ? TONE_STYLES[opt.tone].active
          : TONE_STYLES[opt.tone].inactive;
        return (
          <button
            key={String(opt.key)}
            type="button"
            // biome-ignore lint/a11y/useSemanticElements: styled segmented toggle using the ARIA radio pattern; native <input type=radio> cannot carry this layout
            role="radio"
            aria-checked={isActive}
            disabled={mutation.isPending}
            onClick={() => pick(opt.key)}
            className={`font-mono text-[10px] uppercase tracking-eyebrow border px-2 py-1 transition-colors disabled:opacity-50 ${cls}`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
