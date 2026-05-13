"use client";

import { useId } from "react";

interface Props {
  value: number;
  onChange: (next: number) => void;
  disabled?: boolean;
}

const BUCKET_TICKS = [0, 25, 50, 75, 100];

/** 0-100 conviction slider with bucketed tick marks at 25 % intervals. */
export function ConvictionSlider({ value, onChange, disabled }: Props) {
  const id = useId();
  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex items-center justify-between gap-3">
        <label
          htmlFor={id}
          className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3"
        >
          Conviction
        </label>
        <span className="font-mono tabular-nums text-sm text-accent-bright">
          {value}%
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={100}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Conviction percentage"
        className="w-full accent-accent"
      />
      <div className="flex justify-between font-mono text-[9px] tabular-nums text-ink-4">
        {BUCKET_TICKS.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
    </div>
  );
}
