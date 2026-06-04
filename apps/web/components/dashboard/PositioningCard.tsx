"use client";

import type { PositioningResponse } from "@/lib/api";
import { usePositioning } from "@/lib/queries";

function fmtInt(v: number | null, withSign = false): string {
  if (v === null) return "—";
  const abs = Math.abs(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (!withSign) return abs;
  return v >= 0 ? `+${abs}` : `-${abs}`;
}

function tone(v: number | null): string {
  if (v === null || v === 0) return "text-flat";
  return v > 0 ? "text-up" : "text-down";
}

interface Props {
  symbol?: string;
}

export function PositioningCard({ symbol = "NG" }: Props) {
  const { data, isLoading } = usePositioning(symbol);
  const p = data as PositioningResponse | undefined;
  const available = p?.available ?? false;

  const net = available ? (p?.managed_money_net ?? null) : null;
  const delta = available ? (p?.mm_net_delta ?? null) : null;
  const deltaArrow =
    delta === null || delta === 0 ? "·" : delta > 0 ? "▲" : "▼";

  return (
    <div
      className="border border-line-1 bg-surface-1 rounded-md px-3 py-2.5 flex flex-col gap-1 h-full"
      aria-label="Positioning"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          Positioning · MM Net
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {available ? (p?.report_date ?? "") : "CFTC"}
        </span>
      </div>

      {isLoading || !p ? (
        <p className="text-ink-4 text-xs font-mono p-3">Loading…</p>
      ) : !available ? (
        <p className="text-ink-4 text-xs font-mono p-3">
          No CFTC positioning for this instrument.
        </p>
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            <span
              className={`font-mono text-3xl tabular-nums leading-none ${tone(net)}`}
            >
              {fmtInt(net, true)}
            </span>
            <span className="font-mono text-[11px] text-ink-3">contracts</span>
          </div>
          <div
            className={`flex items-baseline gap-2 font-mono text-xs tabular-nums ${tone(delta)}`}
          >
            <span>{deltaArrow}</span>
            <span>{fmtInt(delta, true)}</span>
            <span className="ml-auto text-[10px] text-ink-4 uppercase tracking-widest">
              wk Δ
            </span>
          </div>
          <div className="flex items-baseline gap-4 font-mono text-[11px] text-ink-3 tabular-nums mt-0.5">
            <span>OI {fmtInt(p.open_interest_total)}</span>
            {p.source && (
              <span className="ml-auto text-ink-4 uppercase tracking-widest text-[10px]">
                {p.source}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
