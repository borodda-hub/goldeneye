"use client";

import {
  type IndicatorSpec,
  type LineWeight,
  type MAType,
  MA_LABEL,
  MA_TYPES,
  PERIOD_MAX,
  PERIOD_MIN,
  PRICE_SOURCES,
  type PriceSource,
  hasRibbon,
  isValidPeriod,
  newSpec,
  ribbonSpecs,
  specToLabel,
} from "@/lib/chart/indicatorRegistry";
import { colors } from "@/lib/colors";
import { useEffect, useState } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  indicators: IndicatorSpec[];
  onAdd: (spec: IndicatorSpec) => void;
  onUpdate: (spec: IndicatorSpec) => void;
  onDelete: (id: string) => void;
  onToggleVisible: (id: string) => void;
  /** Replace the active list — used by the Ribbon preset to bulk-add or bulk-remove. */
  onReplaceAll: (specs: IndicatorSpec[]) => void;
}

/** Palette of token-derived swatches the picker offers — no raw hex elsewhere. */
const COLOR_SWATCHES: { label: string; value: string }[] = [
  { label: "Gold", value: colors.accent },
  { label: "Gold bright", value: colors.accentBright },
  { label: "Gold deep", value: colors.accentDeep },
  { label: "Amber", value: colors.amber },
  { label: "Cyan", value: colors.cyan },
  { label: "Violet", value: colors.violet },
  { label: "Up", value: colors.up },
  { label: "Down", value: colors.down },
];

const WEIGHTS: LineWeight[] = [1, 2, 3];

interface FormState {
  type: MAType;
  period: number;
  periodText: string; // raw input so partial typing doesn't snap to bounds
  source: PriceSource;
  color: string;
  weight: LineWeight;
}

function freshForm(): FormState {
  const s = newSpec("ema");
  return {
    type: s.type,
    period: s.period,
    periodText: String(s.period),
    source: s.source,
    color: s.color,
    weight: s.weight,
  };
}

function formFromSpec(spec: IndicatorSpec): FormState {
  return {
    type: spec.type,
    period: spec.period,
    periodText: String(spec.period),
    source: spec.source,
    color: spec.color,
    weight: spec.weight,
  };
}

export function IndicatorPicker({
  open,
  onClose,
  indicators,
  onAdd,
  onUpdate,
  onDelete,
  onToggleVisible,
  onReplaceAll,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(freshForm);

  // Reset the form whenever the modal opens fresh.
  useEffect(() => {
    if (!open) return;
    setEditingId(null);
    setForm(freshForm());
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const periodValid = isValidPeriod(form.period);
  const canSubmit = periodValid;

  function startEdit(spec: IndicatorSpec) {
    setEditingId(spec.id);
    setForm(formFromSpec(spec));
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(freshForm());
  }

  function submit() {
    if (!canSubmit) return;
    if (editingId) {
      const existing = indicators.find((i) => i.id === editingId);
      if (!existing) return;
      onUpdate({
        ...existing,
        type: form.type,
        period: form.period,
        source: form.source,
        color: form.color,
        weight: form.weight,
      });
      setEditingId(null);
    } else {
      const fresh = newSpec(form.type, {
        period: form.period,
        source: form.source,
        color: form.color,
        weight: form.weight,
      });
      onAdd(fresh);
    }
    setForm(freshForm());
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Indicators"
      className="fixed inset-0 z-[1000] flex items-center justify-center"
      style={{ background: "rgba(10, 10, 9, 0.82)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-line-2 bg-surface-1 p-6 flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-line-1 pb-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
              ─── Chart · Indicators
            </span>
            <h2 className="font-serif text-[24px] leading-none text-ink-1">
              {editingId ? "Edit indicator" : "Add indicator"}
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

        {/* Presets */}
        <div className="flex items-center gap-3 border-b border-line-1 pb-3">
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
            Presets
          </span>
          {hasRibbon(indicators) ? (
            <button
              type="button"
              onClick={() =>
                onReplaceAll(indicators.filter((i) => i.tag !== "ribbon"))
              }
              className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-3 py-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink-1"
              aria-label="Remove ribbon preset"
            >
              Remove Ribbon
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onReplaceAll([...indicators, ...ribbonSpecs()])}
              className="font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-3 py-1.5 text-accent-bright hover:bg-accent hover:text-bg"
              aria-label="Add ribbon preset"
            >
              Add Ribbon (12 EMAs)
            </button>
          )}
          <span className="font-mono text-[10px] text-ink-4 ml-auto">
            5 · 8 · 13 · 21 · 34 · 55 · 89 · 100 · 144 · 200 · 233 · 377
          </span>
        </div>

        {/* Form */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Type">
            <select
              aria-label="Indicator type"
              value={form.type}
              onChange={(e) =>
                setForm({ ...form, type: e.target.value as MAType })
              }
              className="bg-surface-2 border border-line-1 px-2 py-1 text-sm text-ink-1 focus:border-accent focus:outline-none"
            >
              {MA_TYPES.map((t) => (
                <option key={t} value={t}>
                  {MA_LABEL[t]}
                </option>
              ))}
            </select>
          </Field>

          <Field label={`Period (${PERIOD_MIN}–${PERIOD_MAX})`}>
            <input
              aria-label="Period"
              type="number"
              inputMode="numeric"
              min={PERIOD_MIN}
              max={PERIOD_MAX}
              value={form.periodText}
              onChange={(e) => {
                const raw = e.target.value;
                const n = Number.parseInt(raw, 10);
                setForm({
                  ...form,
                  periodText: raw,
                  period: Number.isFinite(n) ? n : Number.NaN,
                });
              }}
              className={`bg-surface-2 border px-2 py-1 text-sm text-ink-1 focus:outline-none ${
                periodValid
                  ? "border-line-1 focus:border-accent"
                  : "border-down focus:border-down"
              }`}
            />
          </Field>

          <Field label="Source">
            <select
              aria-label="Source"
              value={form.source}
              onChange={(e) =>
                setForm({ ...form, source: e.target.value as PriceSource })
              }
              className="bg-surface-2 border border-line-1 px-2 py-1 text-sm text-ink-1 focus:border-accent focus:outline-none"
            >
              {PRICE_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Weight">
            <div className="flex gap-1">
              {WEIGHTS.map((w) => (
                <button
                  key={w}
                  type="button"
                  onClick={() => setForm({ ...form, weight: w })}
                  aria-pressed={form.weight === w}
                  aria-label={`Weight ${w}`}
                  className={`px-3 py-1 text-xs font-mono border ${
                    form.weight === w
                      ? "border-accent text-accent bg-accent-soft"
                      : "border-line-1 text-ink-3 hover:text-ink-1"
                  }`}
                >
                  {w}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Color" span={2}>
            <div className="flex flex-wrap gap-2">
              {COLOR_SWATCHES.map((sw) => (
                <button
                  key={sw.value}
                  type="button"
                  onClick={() => setForm({ ...form, color: sw.value })}
                  aria-label={`Color ${sw.label}`}
                  aria-pressed={form.color === sw.value}
                  className={`w-7 h-7 border-2 ${
                    form.color === sw.value
                      ? "border-ink-1"
                      : "border-transparent hover:border-line-2"
                  }`}
                  style={{ backgroundColor: sw.value }}
                />
              ))}
            </div>
          </Field>
        </div>

        {/* Form actions */}
        <div className="flex items-center justify-end gap-3 border-t border-line-1 pt-3">
          {editingId ? (
            <button
              type="button"
              onClick={cancelEdit}
              className="font-mono text-[10px] uppercase tracking-eyebrow border border-line-1 px-3 py-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink-1"
            >
              Cancel edit
            </button>
          ) : null}
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit}
            className="font-mono text-[10px] uppercase tracking-eyebrow border border-accent bg-accent-soft px-3 py-1.5 text-accent-bright hover:bg-accent hover:text-bg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {editingId ? "Save changes" : "Add"}
          </button>
        </div>

        {/* Current indicators */}
        <div className="flex flex-col gap-2 border-t border-line-1 pt-4">
          <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
            Active ({indicators.length})
          </span>
          {indicators.length === 0 ? (
            <span className="text-xs text-ink-4 font-mono py-2">
              No indicators yet — add one above.
            </span>
          ) : (
            <ul className="flex flex-col">
              {indicators.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center gap-3 py-1.5 border-b border-line-1 last:border-b-0"
                >
                  <span
                    className="w-4 h-0.5 rounded-full shrink-0"
                    style={{ backgroundColor: s.color }}
                  />
                  <span
                    className={`font-mono text-xs flex-1 ${s.visible ? "text-ink-1" : "text-ink-4 line-through"}`}
                  >
                    {specToLabel(s)}{" "}
                    <span className="text-ink-4">· {s.source}</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => onToggleVisible(s.id)}
                    className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 hover:text-ink-1 px-1"
                    aria-label={s.visible ? "Hide" : "Show"}
                  >
                    {s.visible ? "Hide" : "Show"}
                  </button>
                  <button
                    type="button"
                    onClick={() => startEdit(s)}
                    className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3 hover:text-ink-1 px-1"
                    aria-label={`Edit ${specToLabel(s)}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s.id)}
                    className="font-mono text-[10px] uppercase tracking-eyebrow text-down hover:text-ink-1 px-1"
                    aria-label={`Delete ${specToLabel(s)}`}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  span = 1,
  children,
}: {
  label: string;
  span?: 1 | 2;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex flex-col gap-1 ${span === 2 ? "col-span-2" : ""}`}>
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
        {label}
      </span>
      {children}
    </div>
  );
}
