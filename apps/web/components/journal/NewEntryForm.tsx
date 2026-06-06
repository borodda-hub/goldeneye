"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FilePlus2 } from "lucide-react";
import { useState } from "react";
import type { Evidence, JournalEntry } from "../../app/(app)/journal/types";
import { createJournalEntry } from "../../lib/api";
import { queryKeys } from "../../lib/queries";

interface Props {
  onCreated?: (id: string) => void;
}

interface FormState {
  hypothesis: string;
  evidence: Evidence[];
  confidence_pct: number;
  planned_action: string;
  risk_factors: string;
  invalidation_criteria: string;
}

const initial: FormState = {
  hypothesis: "",
  evidence: [],
  confidence_pct: 50,
  planned_action: "",
  risk_factors: "",
  invalidation_criteria: "",
};

export function NewEntryForm({ onCreated }: Props) {
  const [form, setForm] = useState<FormState>(initial);
  const queryClient = useQueryClient();

  const mutation = useMutation<JournalEntry, Error, void>({
    mutationFn: async () => {
      const body = {
        instrument: "NG",
        hypothesis: form.hypothesis.trim(),
        evidence: form.evidence,
        confidence_pct: form.confidence_pct,
        planned_action: form.planned_action.trim() || undefined,
        risk_factors: form.risk_factors
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        invalidation_criteria: form.invalidation_criteria.trim() || undefined,
      };
      return (await createJournalEntry(body)) as JournalEntry;
    },
    onSuccess: (entry) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journalEntries() });
      onCreated?.(entry.id);
      setForm(initial);
    },
  });

  const valid =
    form.hypothesis.trim().length > 0 &&
    form.confidence_pct >= 0 &&
    form.confidence_pct <= 100;

  const updateEvidence = (idx: number, patch: Partial<Evidence>) => {
    setForm((f) => ({
      ...f,
      evidence: f.evidence.map((e, i) => (i === idx ? { ...e, ...patch } : e)),
    }));
  };

  const addEvidence = () => {
    setForm((f) => ({
      ...f,
      evidence: [...f.evidence, { source: "", summary: "", weight: 0.5 }],
    }));
  };

  const removeEvidence = (idx: number) => {
    setForm((f) => ({
      ...f,
      evidence: f.evidence.filter((_, i) => i !== idx),
    }));
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid && !mutation.isPending) mutation.mutate();
      }}
      className="card-interactive border border-line-1 bg-surface-1 p-3 flex flex-col gap-3"
    >
      <h2 className="flex items-center gap-2 font-mono text-[10px] text-ink-3 uppercase tracking-widest">
        <FilePlus2
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        New Entry
      </h2>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Hypothesis
        </span>
        <textarea
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 min-h-[80px]"
          placeholder="What do you expect to happen and why?"
          value={form.hypothesis}
          onChange={(e) =>
            setForm((f) => ({ ...f, hypothesis: e.target.value }))
          }
        />
      </label>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
            Evidence
          </span>
          <button
            type="button"
            onClick={addEvidence}
            className="font-mono text-[10px] uppercase tracking-widest text-accent"
          >
            + Add
          </button>
        </div>
        {form.evidence.length === 0 && (
          <p className="text-[10px] text-ink-4 font-mono">No evidence rows.</p>
        )}
        {form.evidence.map((ev, idx) => (
          <div
            // biome-ignore lint/suspicious/noArrayIndexKey: form-managed render-only list, no stable id
            key={idx}
            className="flex items-center gap-2 border border-line-1 bg-surface-2 px-2 py-1.5"
          >
            <input
              className="bg-surface-1 border border-line-1 px-1 py-0.5 font-mono text-[11px] text-ink-2 w-20"
              placeholder="source"
              value={ev.source}
              onChange={(e) => updateEvidence(idx, { source: e.target.value })}
            />
            <input
              className="bg-surface-1 border border-line-1 px-1 py-0.5 font-mono text-[11px] text-ink-2 flex-1 min-w-0"
              placeholder="summary"
              value={ev.summary}
              onChange={(e) => updateEvidence(idx, { summary: e.target.value })}
            />
            <input
              type="number"
              step="0.1"
              min={0}
              max={1}
              className="bg-surface-1 border border-line-1 px-1 py-0.5 font-mono text-[11px] text-ink-2 w-12 tabular-nums"
              value={ev.weight}
              onChange={(e) =>
                updateEvidence(idx, { weight: Number(e.target.value) })
              }
            />
            <button
              type="button"
              onClick={() => removeEvidence(idx)}
              className="font-mono text-[10px] text-ink-4 hover:text-down uppercase"
              aria-label={`Remove evidence ${idx + 1}`}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <label className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
            Confidence
          </span>
          <span className="font-mono text-[10px] text-ink-2 tabular-nums">
            {form.confidence_pct}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={form.confidence_pct}
          onChange={(e) =>
            setForm((f) => ({ ...f, confidence_pct: Number(e.target.value) }))
          }
          aria-label="Confidence percentage"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Planned Action
        </span>
        <textarea
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 min-h-[48px]"
          placeholder="If thesis holds, what is the plan?"
          value={form.planned_action}
          onChange={(e) =>
            setForm((f) => ({ ...f, planned_action: e.target.value }))
          }
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Risk Factors (comma-separated)
        </span>
        <input
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2"
          placeholder="weather model error, LNG demand surprise"
          value={form.risk_factors}
          onChange={(e) =>
            setForm((f) => ({ ...f, risk_factors: e.target.value }))
          }
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Invalidation Criteria
        </span>
        <textarea
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 min-h-[48px]"
          placeholder="What would prove this hypothesis wrong?"
          value={form.invalidation_criteria}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              invalidation_criteria: e.target.value,
            }))
          }
        />
      </label>

      <button
        type="submit"
        disabled={!valid || mutation.isPending}
        className="border border-accent text-accent font-mono text-xs uppercase tracking-widest py-1.5 disabled:border-line-1 disabled:text-ink-4 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? "Submitting…" : "Submit Entry"}
      </button>

      {mutation.isError && (
        <p className="text-xs text-down font-mono">
          Submit failed: {mutation.error?.message ?? "unknown error"}
        </p>
      )}
    </form>
  );
}
