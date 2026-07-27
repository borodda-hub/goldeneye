"use client";

/**
 * Archive clocks (demo-polish sprint) — makes the "what's accumulating"
 * state visible. Three research re-entry gates run on wall-clock data
 * accumulation, not code: this card shows live vintage-day counts from
 * `GET /v1/validation` (the same numbers the Validation page proves) against
 * each gate's pre-registered target, so nobody has to remember what is
 * quietly compounding in prod. Targets are documented in
 * docs/MODEL_DILIGENCE.md + docs/BUILD_ROADMAP.md — counts here are live,
 * the targets are the pre-registered ones.
 */

import { useValidation } from "@/lib/queries";
import { Hourglass } from "lucide-react";

const CLOCKS = [
  {
    key: "weather",
    label: "Weather vintages",
    target: 180,
    gate: "Weather-feature probe · needs ≥180 real vintage days · ~Jan 2027",
  },
  {
    key: "curve",
    label: "Curve vintages",
    target: 730,
    gate: "Cross-sectional carry probe · needs ~2y of curve vintages · ~mid-2028",
  },
] as const;

function ClockRow({
  label,
  days,
  target,
  gate,
}: {
  label: string;
  days: number | null;
  target: number;
  gate: string;
}) {
  const pct =
    days === null ? 0 : Math.min(100, Math.round((days / target) * 100));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs text-ink-2">{label}</span>
        <span className="font-mono text-xs tabular-nums text-ink-1">
          {days === null ? "—" : days}
          <span className="text-ink-4"> / {target}d</span>
        </span>
      </div>
      <div
        className="h-1 w-full overflow-hidden bg-line-1"
        role="progressbar"
        aria-label={label}
        aria-valuenow={days ?? 0}
        aria-valuemin={0}
        aria-valuemax={target}
      >
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-ink-4">{gate}</span>
    </div>
  );
}

export function ArchiveClocksCard() {
  const { data } = useValidation();
  const days = {
    weather: data?.archives.weather_vintage_days ?? null,
    curve: data?.archives.curve_vintage_days ?? null,
  };
  return (
    <div className="card-interactive border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2">
        <Hourglass
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Archive clocks
        </span>
      </div>
      <div className="flex flex-col gap-3 p-3">
        {CLOCKS.map((c) => (
          <ClockRow
            key={c.key}
            label={c.label}
            days={days[c.key]}
            target={c.target}
            gate={c.gate}
          />
        ))}
        <div className="flex flex-col gap-1 border-t border-line-1 pt-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-xs text-ink-2">D1 vol-tilt re-run</span>
            <span className="font-mono text-xs text-ink-1">~Jul 2027</span>
          </div>
          <span className="font-mono text-[10px] text-ink-4">
            Original pre-registered gate re-run on ≥1y of new NG data · until
            then Layer 2 stays tested-not-crowned
          </span>
        </div>
      </div>
    </div>
  );
}
