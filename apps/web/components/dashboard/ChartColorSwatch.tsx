"use client";

import {
  CHART_COLOR_OPTIONS,
  type ChartColorKey,
} from "@/lib/useChartColor";

interface Props {
  value: ChartColorKey;
  onChange: (key: ChartColorKey) => void;
}

/** Horizontal row of small color swatches for selecting chart accent color. */
export function ChartColorSwatch({ value, onChange }: Props) {
  return (
    <div
      className="flex items-center gap-1.5"
      role="radiogroup"
      aria-label="Chart color"
    >
      {CHART_COLOR_OPTIONS.map((opt) => {
        const active = opt.key === value;
        return (
          <button
            key={opt.key}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={opt.label}
            title={opt.label}
            onClick={() => onChange(opt.key)}
            className={`h-3 w-3 rounded-full transition-all ${
              active
                ? "ring-1 ring-offset-2 ring-offset-surface-1 ring-ink-2 scale-110"
                : "opacity-50 hover:opacity-100 hover:scale-110"
            }`}
            style={{ backgroundColor: opt.stroke }}
          />
        );
      })}
    </div>
  );
}
