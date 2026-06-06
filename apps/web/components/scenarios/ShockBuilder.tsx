"use client";

import type { Shock, ShockType } from "@/app/(app)/scenarios/types";
import { HelpTip } from "@/components/HelpTip";
import { leanArrow, leanColor, leanLabel, shockLean } from "@/lib/scenarioLean";
import { SlidersHorizontal, Zap } from "lucide-react";
import { useState } from "react";

interface Props {
  shocks: Shock[];
  onChange: (shocks: Shock[]) => void;
}

const SHOCK_TYPES: ShockType[] = [
  "weather",
  "lng_export",
  "production",
  "storage",
];

function defaultShock(type: ShockType): Shock {
  switch (type) {
    case "weather":
      return { type, region: "northeast", delta_temp_f: -8, days: 10 };
    case "lng_export":
      return { type, delta_bcfd: -1.5, days: 14 };
    case "production":
      return { type, delta_bcfd: -2, days: 7 };
    case "storage":
      return { type, delta_bcf: -20, days: 7 };
  }
}

function ShockRow({
  shock,
  onUpdate,
  onRemove,
}: {
  shock: Shock;
  onUpdate: (next: Shock) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-3 border border-line-1 bg-surface-1 px-3 py-2">
      <span className="font-mono text-xs text-ink-2 uppercase tracking-widest w-24">
        {shock.type.replace("_", " ")}
      </span>
      <span
        className={`font-mono text-[10px] w-20 ${leanColor(shockLean(shock))}`}
        title="Directional lean from this shock's sign"
      >
        {leanArrow(shockLean(shock))} {leanLabel(shockLean(shock))}
      </span>

      {shock.type === "weather" && (
        <>
          <label className="flex items-center gap-1 text-xs text-ink-3">
            <span className="font-mono">region</span>
            <input
              className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-28"
              value={shock.region}
              onChange={(e) => onUpdate({ ...shock, region: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-1 text-xs text-ink-3">
            <span className="font-mono">Δ°F</span>
            <input
              type="number"
              step="0.5"
              min={-50}
              max={50}
              className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-16 tabular-nums"
              value={shock.delta_temp_f}
              onChange={(e) =>
                onUpdate({ ...shock, delta_temp_f: Number(e.target.value) })
              }
            />
          </label>
        </>
      )}

      {(shock.type === "lng_export" || shock.type === "production") && (
        <label className="flex items-center gap-1 text-xs text-ink-3">
          <span className="font-mono">Δ Bcf/d</span>
          <input
            type="number"
            step="0.1"
            min={-15}
            max={15}
            className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-20 tabular-nums"
            value={shock.delta_bcfd}
            onChange={(e) =>
              onUpdate({ ...shock, delta_bcfd: Number(e.target.value) })
            }
          />
        </label>
      )}

      {shock.type === "storage" && (
        <label className="flex items-center gap-1 text-xs text-ink-3">
          <span className="font-mono">Δ Bcf</span>
          <input
            type="number"
            step="1"
            min={-500}
            max={500}
            className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-20 tabular-nums"
            value={shock.delta_bcf}
            onChange={(e) =>
              onUpdate({ ...shock, delta_bcf: Number(e.target.value) })
            }
          />
        </label>
      )}

      <label className="flex items-center gap-1 text-xs text-ink-3">
        <span className="font-mono">days</span>
        <input
          type="number"
          step="1"
          min={1}
          max={60}
          className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-14 tabular-nums"
          value={shock.days}
          onChange={(e) => onUpdate({ ...shock, days: Number(e.target.value) })}
        />
      </label>

      <button
        type="button"
        onClick={onRemove}
        className="ml-auto font-mono text-[10px] text-ink-4 hover:text-down uppercase tracking-widest"
      >
        Remove
      </button>
    </div>
  );
}

export function ShockBuilder({ shocks, onChange }: Props) {
  const [adding, setAdding] = useState<ShockType>("weather");

  const update = (idx: number, next: Shock) => {
    const copy = [...shocks];
    copy[idx] = next;
    onChange(copy);
  };

  const remove = (idx: number) => {
    onChange(shocks.filter((_, i) => i !== idx));
  };

  const add = () => {
    if (shocks.length >= 10) return;
    onChange([...shocks, defaultShock(adding)]);
  };

  return (
    <div className="card-interactive border border-line-1 bg-surface-1 flex flex-col">
      <div className="px-3 py-2 border-b border-line-1 flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] text-accent uppercase tracking-widest">
          <SlidersHorizontal
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Shock Builder
          <HelpTip k="shockBuilder" className="ml-1" />
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {shocks.length} / 10
        </span>
      </div>

      <div className="flex flex-col gap-2 p-3">
        {shocks.length === 0 && (
          <div className="flex flex-col items-center gap-1.5 py-6 text-ink-4">
            <Zap size={18} strokeWidth={1.5} aria-hidden="true" />
            <span className="text-[11px]">No shocks</span>
            <span className="text-[10px] text-ink-4/70">
              Add one below or load a template.
            </span>
          </div>
        )}
        {shocks.map((s, i) => (
          <ShockRow
            // biome-ignore lint/suspicious/noArrayIndexKey: form-managed render-only list, no stable id
            key={i}
            shock={s}
            onUpdate={(next) => update(i, next)}
            onRemove={() => remove(i)}
          />
        ))}
      </div>

      <div className="px-3 py-2 border-t border-line-1 flex items-center gap-2">
        <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
          Add shock:
        </span>
        <select
          className="bg-surface-2 border border-line-1 px-2 py-0.5 font-mono text-xs text-ink-2"
          value={adding}
          onChange={(e) => setAdding(e.target.value as ShockType)}
        >
          {SHOCK_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace("_", " ")}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={add}
          disabled={shocks.length >= 10}
          className="font-mono text-[10px] uppercase tracking-widest text-accent disabled:text-ink-4 disabled:cursor-not-allowed"
        >
          + Add
        </button>
      </div>
    </div>
  );
}
