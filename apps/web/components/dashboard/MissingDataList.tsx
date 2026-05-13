"use client";

import { useState } from "react";

interface Props {
  items: string[];
  onChange: (next: string[]) => void;
}

export function MissingDataList({ items, onChange }: Props) {
  const [draft, setDraft] = useState("");

  function add() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    if (items.includes(trimmed)) {
      setDraft("");
      return;
    }
    onChange([...items, trimmed]);
    setDraft("");
  }

  function removeAt(idx: number) {
    onChange(items.filter((_, i) => i !== idx));
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
          Missing data
        </span>
        <span className="font-mono text-[10px] tabular-nums text-ink-4">
          {items.length}
        </span>
      </div>
      <ul className="flex flex-col gap-1 min-h-[40px]">
        {items.length === 0 ? (
          <li className="text-xs text-ink-4 italic">None.</li>
        ) : (
          items.map((item, i) => (
            <li
              key={`${item}-${i}`}
              className="flex items-start gap-2 text-xs text-ink-2 leading-relaxed"
            >
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-deep"
                aria-hidden="true"
              />
              <span className="flex-1 min-w-0">{item}</span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="text-ink-4 hover:text-down text-xs leading-none px-1"
                aria-label={`Remove ${item}`}
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
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="What data would invalidate or confirm…"
          maxLength={200}
          className="flex-1 bg-surface-2 border border-line-1 px-2 py-1 text-xs text-ink-1 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
        <button
          type="button"
          onClick={add}
          disabled={!draft.trim() || items.length >= 20}
          className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-2 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>
    </div>
  );
}
