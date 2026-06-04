"use client";

import type { EvidenceEntry } from "@/lib/api";
import { useState } from "react";

interface Props {
  label: string;
  items: EvidenceEntry[];
  onChange: (next: EvidenceEntry[]) => void;
  /** Color for the leading bullet — `up` for supporting, `down` for contradicting. */
  tone: "supporting" | "contradicting";
}

const TONE_DOT: Record<Props["tone"], string> = {
  supporting: "bg-up",
  contradicting: "bg-down",
};

export function EvidenceList({ label, items, onChange, tone }: Props) {
  const [newFactor, setNewFactor] = useState("");

  function addItem() {
    const factor = newFactor.trim();
    if (!factor) return;
    onChange([...items, { factor, weight: null, note: "", source: null }]);
    setNewFactor("");
  }

  function removeAt(idx: number) {
    onChange(items.filter((_, i) => i !== idx));
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          {label}
        </span>
        <span className="font-mono text-[10px] tabular-nums text-ink-4">
          {items.length}
        </span>
      </div>
      <ul className="flex flex-col gap-1.5 min-h-[40px]">
        {items.length === 0 ? (
          <li className="text-xs text-ink-4 italic">None.</li>
        ) : (
          items.map((item, i) => (
            <li
              key={`${item.factor}-${i}`}
              className="flex items-start gap-2 text-xs text-ink-2 leading-relaxed"
            >
              <span
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${TONE_DOT[tone]}`}
                aria-hidden="true"
              />
              <div className="flex-1 min-w-0">
                <span className="font-medium text-ink-1">{item.factor}</span>
                {item.note ? (
                  <span className="text-ink-3"> — {item.note}</span>
                ) : null}
                {item.source ? (
                  <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4 ml-2">
                    {item.source}
                  </span>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="text-ink-4 hover:text-down text-xs leading-none px-1"
                aria-label={`Remove ${item.factor}`}
              >
                ×
              </button>
            </li>
          ))
        )}
      </ul>
      <div className="flex gap-2">
        <input
          type="text"
          value={newFactor}
          onChange={(e) => setNewFactor(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addItem();
            }
          }}
          placeholder="Add a factor…"
          maxLength={200}
          className="flex-1 bg-surface-2 border border-line-1 px-2 py-1 text-xs text-ink-1 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
        <button
          type="button"
          onClick={addItem}
          disabled={!newFactor.trim() || items.length >= 20}
          className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>
    </div>
  );
}
