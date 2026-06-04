"use client";

import type { FundamentalsResponse } from "@/lib/api";
import { useFundamentals } from "@/lib/queries";

function fmtNum(v: number | null, withSign = false): string {
  if (v === null) return "—";
  const abs = Math.abs(v).toLocaleString("en-US", { maximumFractionDigits: 1 });
  if (!withSign) return abs;
  return v >= 0 ? `+${abs}` : `-${abs}`;
}

interface Props {
  symbol?: string;
}

export function FundamentalsCard({ symbol = "NG" }: Props) {
  const { data, isLoading } = useFundamentals(symbol);
  const f = data as FundamentalsResponse | undefined;
  const latest = f && f.kind !== "none" ? f.latest : null;

  const nc = latest?.net_change ?? null;
  const tone =
    nc === null
      ? "text-flat"
      : nc > 0
        ? "text-up"
        : nc < 0
          ? "text-down"
          : "text-flat";
  const arrow = nc === null || nc === 0 ? "·" : nc > 0 ? "▲" : "▼";

  return (
    <div
      className="border border-line-1 bg-surface-1 rounded-md px-3 py-2.5 flex flex-col gap-1 h-full"
      aria-label="Fundamentals"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          {f && f.kind !== "none" ? f.title : "Fundamentals"}
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {latest?.as_of ?? f?.unit ?? "—"}
        </span>
      </div>

      {isLoading || !f ? (
        <p className="text-ink-4 text-xs font-mono p-3">Loading…</p>
      ) : !latest ? (
        <p className="text-ink-4 text-xs font-mono p-3">
          {f.empty_reason ?? "No fundamentals."}
        </p>
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-3xl tabular-nums text-ink-1 leading-none">
              {fmtNum(latest.level)}
            </span>
            <span className="font-mono text-[11px] text-ink-3">{f.unit}</span>
          </div>
          <div
            className={`flex items-baseline gap-2 font-mono text-xs tabular-nums ${tone}`}
          >
            <span>{arrow}</span>
            <span>{fmtNum(nc, true)}</span>
            <span className="ml-auto text-[10px] text-ink-4 uppercase tracking-widest">
              wk Δ
            </span>
          </div>
          {(latest.surprise !== null || latest.five_year_avg !== null) && (
            <div className="flex items-baseline gap-4 font-mono text-[11px] text-ink-3 tabular-nums mt-0.5">
              {latest.surprise !== null && (
                <span>surprise {fmtNum(latest.surprise, true)}</span>
              )}
              {latest.five_year_avg !== null && (
                <span>5y avg {fmtNum(latest.five_year_avg)}</span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
