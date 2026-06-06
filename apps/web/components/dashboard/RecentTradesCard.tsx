"use client";

import type { Trade, TradesResponse } from "@/app/(app)/paper/types";
import { usePaperTrades } from "@/lib/queries";
import { History } from "lucide-react";

type Status = Trade["status"];

const STATUS_LABEL: Record<Status, string> = {
  open: "Open",
  closed: "Closed",
  cancelled: "Canceled",
};

const STATUS_CHIP: Record<Status, string> = {
  open: "bg-conf-low/20 text-conf-low border-conf-low/40",
  closed: "bg-up-soft text-up border-up/40",
  cancelled: "bg-down-soft text-down border-down/40",
};

function StatusChip({ status }: { status: Status }) {
  return (
    <span
      className={`inline-block px-1.5 py-px text-[9px] font-mono uppercase tracking-widest border rounded-sm ${STATUS_CHIP[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

function fmtPnl(v: number | null): string {
  if (v === null) return "—";
  const abs = Math.abs(v);
  const sign = v >= 0 ? "+" : "-";
  return `${sign}$${abs.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function pnlTone(v: number | null): string {
  if (v === null || v === 0) return "text-ink-4";
  return v > 0 ? "text-up" : "text-down";
}

function mergeAndSort(...lists: Trade[][]): Trade[] {
  const seen = new Set<string>();
  const out: Trade[] = [];
  for (const l of lists) {
    for (const t of l) {
      if (seen.has(t.id)) continue;
      seen.add(t.id);
      out.push(t);
    }
  }
  return out.sort((a, b) => {
    const ka = a.closed_at ?? a.opened_at;
    const kb = b.closed_at ?? b.opened_at;
    return kb.localeCompare(ka);
  });
}

export function RecentTradesCard() {
  // Pull both open and closed; merge and show the most recent 8.
  const openQ = usePaperTrades("open");
  const closedQ = usePaperTrades("closed");
  const open = ((openQ.data as TradesResponse | undefined)?.trades ??
    []) as Trade[];
  const closed = ((closedQ.data as TradesResponse | undefined)?.trades ??
    []) as Trade[];
  const recent = mergeAndSort(open, closed).slice(0, 8);

  return (
    <div
      className="card-interactive border border-line-1 bg-surface-1 rounded-md flex flex-col"
      aria-label="Recent paper trades"
    >
      <div className="flex items-baseline justify-between px-3 pt-2 pb-1.5 border-b border-line-1">
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent uppercase tracking-eyebrow">
          <History
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Recent
        </span>
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {recent.length}
        </span>
      </div>

      {recent.length === 0 ? (
        <div className="flex flex-col items-center gap-1.5 px-3 py-4 text-center text-ink-4">
          <History size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px] font-mono">No paper trades yet.</span>
        </div>
      ) : (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-ink-4 text-[9px] uppercase tracking-widest">
              <th className="text-left px-3 py-1">Symbol</th>
              <th className="text-left px-3 py-1">Status</th>
              <th className="text-left px-3 py-1">Side</th>
              <th className="text-right px-3 py-1">P/L</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((t) => (
              <tr
                key={t.id}
                className="border-t border-line-1/60"
                data-testid="dash-recent-row"
              >
                <td className="px-3 py-1.5 text-ink-1">
                  {t.contract_id ? t.contract_id.slice(0, 6) : "NG"}
                </td>
                <td className="px-3 py-1.5">
                  <StatusChip status={t.status} />
                </td>
                <td
                  className={`px-3 py-1.5 text-[10px] uppercase ${
                    t.side === "long" ? "text-up" : "text-down"
                  }`}
                >
                  {t.side}
                </td>
                <td
                  className={`px-3 py-1.5 text-right tabular-nums ${pnlTone(t.outcome_pnl)}`}
                >
                  {t.status === "open" ? "—" : fmtPnl(t.outcome_pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
