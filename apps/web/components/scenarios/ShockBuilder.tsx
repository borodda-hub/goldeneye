"use client";

import type { Shock, ShockType } from "@/app/(app)/scenarios/types";
import { HelpTip } from "@/components/HelpTip";
import { leanArrow, leanColor, leanLabel, shockLean } from "@/lib/scenarioLean";
import { SlidersHorizontal, Zap } from "lucide-react";
import { useEffect, useState } from "react";

interface Props {
  shocks: Shock[];
  onChange: (shocks: Shock[]) => void;
  /** Which shock taxonomy to expose (gas vs crude). Defaults to NG. */
  instrument?: string;
}

const SHOCK_TYPES_BY_INSTRUMENT: Record<string, ShockType[]> = {
  NG: ["weather", "lng_export", "production", "storage"],
  BZ: ["opec_supply", "geopolitical_supply", "demand", "inventory"],
};

// B5: instruments without a defined shock taxonomy (ES/ZN and every non-energy
// asset class) return [] — the builder then renders an explicit "unsupported"
// state instead of silently falling back to NG's weather/storage shocks.
function shockTypesFor(instrument: string): ShockType[] {
  return SHOCK_TYPES_BY_INSTRUMENT[instrument] ?? [];
}

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
    case "opec_supply":
      return { type, delta_mbpd: -1.0, days: 90 };
    case "geopolitical_supply":
      return { type, region: "hormuz", delta_mbpd: -2.0, days: 14 };
    case "demand":
      return { type, region: "china", delta_mbpd: -1.5, days: 60 };
    case "inventory":
      return { type, delta_mmbbl: 50, days: 30 };
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
      <span className="font-mono text-xs text-ink-2 uppercase tracking-widest w-24 shrink-0">
        {shock.type.replace(/_/g, " ")}
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

      {(shock.type === "geopolitical_supply" || shock.type === "demand") && (
        <label className="flex items-center gap-1 text-xs text-ink-3">
          <span className="font-mono">region</span>
          <input
            className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-28"
            value={shock.region}
            onChange={(e) => onUpdate({ ...shock, region: e.target.value })}
          />
        </label>
      )}

      {(shock.type === "opec_supply" ||
        shock.type === "geopolitical_supply" ||
        shock.type === "demand") && (
        <label className="flex items-center gap-1 text-xs text-ink-3">
          <span className="font-mono">Δ Mb/d</span>
          <input
            type="number"
            step="0.1"
            min={-25}
            max={25}
            className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-20 tabular-nums"
            value={shock.delta_mbpd}
            onChange={(e) =>
              onUpdate({ ...shock, delta_mbpd: Number(e.target.value) })
            }
          />
        </label>
      )}

      {shock.type === "inventory" && (
        <label className="flex items-center gap-1 text-xs text-ink-3">
          <span className="font-mono">Δ MMbbl</span>
          <input
            type="number"
            step="1"
            min={-300}
            max={300}
            className="bg-surface-2 border border-line-1 px-1 py-0.5 font-mono text-xs text-ink-2 w-20 tabular-nums"
            value={shock.delta_mmbbl}
            onChange={(e) =>
              onUpdate({ ...shock, delta_mmbbl: Number(e.target.value) })
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
          max={
            shock.type === "opec_supply" ||
            shock.type === "geopolitical_supply" ||
            shock.type === "demand" ||
            shock.type === "inventory"
              ? 180
              : 60
          }
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

export function ShockBuilder({ shocks, onChange, instrument = "NG" }: Props) {
  const types = shockTypesFor(instrument);
  const [adding, setAdding] = useState<ShockType>(types[0]);

  // Keep the "add" selector valid when the instrument (taxonomy) changes.
  useEffect(() => {
    setAdding(types[0]);
  }, [types]);

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

  // B5 honest degradation: no shock taxonomy for this asset class (e.g. ES/ZN).
  // Show an explicit unsupported state rather than nonsensical NG shock controls.
  if (types.length === 0) {
    return (
      <div className="card-interactive border border-line-1 bg-surface-1 flex flex-col">
        <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2 font-mono text-[10px] text-accent uppercase tracking-widest">
          <SlidersHorizontal
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Shock Builder
        </div>
        <div className="flex flex-col items-center gap-1.5 px-4 py-8 text-center text-ink-4">
          <Zap size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px] text-ink-3">
            No scenario taxonomy for {instrument} yet
          </span>
          <span className="max-w-xs text-[10px] text-ink-4/70">
            Scenario shocks are defined for natural gas and crude only. This
            asset class has no shock model yet — the Scenario Lab is unavailable
            for it.
          </span>
        </div>
      </div>
    );
  }

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
          {types.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
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
