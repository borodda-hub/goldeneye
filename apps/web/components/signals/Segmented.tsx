"use client";

/**
 * Small segmented control, matching the chart toolbar idiom (token colors only).
 * Used by the Signal Lab view + estimator selectors (Phase 30d).
 */

const SEG_BASE = "px-2.5 py-1 text-xs font-mono transition-colors";
const SEG_ON = "bg-accent-soft text-accent";
const SEG_OFF = "bg-surface-1 text-ink-3 hover:text-ink-1 hover:bg-surface-2";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  /** Native title tooltip — used to carry each option's honest one-liner. */
  title?: string;
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: ReadonlyArray<SegmentedOption<T>>;
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div
      className="flex rounded border border-line-2 overflow-hidden"
      aria-label={label}
    >
      {options.map((o, i) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          title={o.title}
          className={`${SEG_BASE} ${
            i < options.length - 1 ? "border-r border-line-2" : ""
          } ${value === o.value ? SEG_ON : SEG_OFF}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
