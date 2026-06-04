"use client";

import type { EvidenceEntry, Thesis, ThesisSeed } from "@/lib/api";
import { useEffect, useRef, useState } from "react";
import { ConvictionSlider } from "./ConvictionSlider";
import { EvidenceList } from "./EvidenceList";
import { MissingDataList } from "./MissingDataList";

interface Props {
  open: boolean;
  /** Existing thesis (edit) or a draft seed (create). */
  initial: Thesis | ThesisSeed;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (next: {
    statement: string;
    supporting_evidence: EvidenceEntry[];
    contradicting_evidence: EvidenceEntry[];
    missing_data: string[];
    conviction_pct: number;
  }) => void;
}

export function ThesisEditModal({
  open,
  initial,
  saving,
  error,
  onClose,
  onSave,
}: Props) {
  const [statement, setStatement] = useState(initial.statement);
  const [supporting, setSupporting] = useState<EvidenceEntry[]>(
    initial.supporting_evidence,
  );
  const [contradicting, setContradicting] = useState<EvidenceEntry[]>(
    initial.contradicting_evidence,
  );
  const [missing, setMissing] = useState<string[]>(initial.missing_data);
  const [conviction, setConviction] = useState<number>(initial.conviction_pct);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Reset form when the dialog opens with a new initial value.
  useEffect(() => {
    if (!open) return;
    setStatement(initial.statement);
    setSupporting(initial.supporting_evidence);
    setContradicting(initial.contradicting_evidence);
    setMissing(initial.missing_data);
    setConviction(initial.conviction_pct);
  }, [open, initial]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const isExistingThesis = "id" in initial;
  const title = isExistingThesis
    ? "Edit Working Thesis"
    : "Draft Working Thesis";
  const canSave = statement.trim().length > 0 && !saving;

  return (
    // biome-ignore lint/a11y/useSemanticElements: custom backdrop modal; native <dialog> would change the click-outside backdrop and positioning model. Escape is handled via a window keydown listener.
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-bg/80 backdrop-blur-sm"
      style={{ background: "rgba(10, 10, 9, 0.82)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto border border-line-2 bg-surface-1 p-6 flex flex-col gap-5"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-line-1 pb-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
              ─── Working Thesis · NG
            </span>
            <h2 className="font-serif text-[28px] leading-none text-ink-1">
              {title}
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

        {/* Statement */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="thesis-statement"
            className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3"
          >
            Statement
          </label>
          <textarea
            id="thesis-statement"
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="What's your current view? Be specific and falsifiable."
            maxLength={2000}
            rows={4}
            className="bg-surface-2 border border-line-1 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-4 focus:border-accent focus:outline-none resize-none"
          />
          <span className="font-mono text-[10px] tabular-nums text-ink-4 self-end">
            {statement.length} / 2000
          </span>
        </div>

        {/* Conviction */}
        <ConvictionSlider value={conviction} onChange={setConviction} />

        {/* Evidence grid */}
        <div className="grid grid-cols-2 gap-5 border-t border-line-1 pt-4">
          <EvidenceList
            label="Supporting evidence"
            items={supporting}
            onChange={setSupporting}
            tone="supporting"
          />
          <EvidenceList
            label="Contradicting evidence"
            items={contradicting}
            onChange={setContradicting}
            tone="contradicting"
          />
        </div>

        {/* Missing data */}
        <div className="border-t border-line-1 pt-4">
          <MissingDataList items={missing} onChange={setMissing} />
        </div>

        {/* Error */}
        {error ? <p className="text-xs text-down font-mono">{error}</p> : null}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 border-t border-line-1 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-3 py-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink-1 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() =>
              onSave({
                statement: statement.trim(),
                supporting_evidence: supporting,
                contradicting_evidence: contradicting,
                missing_data: missing,
                conviction_pct: conviction,
              })
            }
            disabled={!canSave}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-3 py-1.5 text-accent-bright hover:bg-accent hover:text-bg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving…" : "Save thesis"}
          </button>
        </div>
      </div>
    </div>
  );
}
