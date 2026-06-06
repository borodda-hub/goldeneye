"use client";

import { HelpTip } from "@/components/HelpTip";
import { Skeleton } from "@/components/Skeleton";
import type { FundamentalsResponse } from "@/lib/api";
import { useFundamentals } from "@/lib/queries";
import { Database } from "lucide-react";

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
      className="card-interactive border border-line-1 bg-surface-1 rounded-md px-3 py-2.5 flex flex-col gap-1 h-full"
      aria-label="Fundamentals"
    >
      <div className="flex items-baseline justify-between">
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          <Database
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          {f && f.kind !== "none" ? f.title : "Fundamentals"}
          <HelpTip k="fundamentals" className="ml-1" />
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {latest?.as_of ?? f?.unit ?? "—"}
        </span>
      </div>

      {isLoading || !f ? (
        <div className="flex flex-col gap-2 p-3">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      ) : !latest ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-1.5 p-3 text-ink-4">
          <Database size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-xs font-mono text-center">
            {f.empty_reason ?? "No fundamentals."}
          </span>
        </div>
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
