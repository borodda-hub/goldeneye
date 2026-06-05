"use client";

import type { HistoryRow, SignalHistory } from "@/app/(app)/signals/types";
import { HelpTip } from "@/components/HelpTip";
import { useSignalHistory } from "@/lib/queries";
import { useState } from "react";

function OutcomeGlyph({ outcome }: { outcome: HistoryRow["outcome"] }) {
  switch (outcome) {
    case "hit":
      return <span className="text-up">▲</span>;
    case "miss":
      return <span className="text-down">▼</span>;
    case "indeterminate":
      return <span className="text-flat">◇</span>;
    case "neutral":
      return <span className="text-flat">—</span>;
    case "pending":
      return <span className="text-ink-4">···</span>;
  }
}

function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}

function fmtDate(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

interface Props {
  symbol?: string;
  initialLimit?: number;
}

export function HistoryTable({ symbol = "NG", initialLimit = 25 }: Props) {
  const [showPending, setShowPending] = useState(false);
  const [limit, setLimit] = useState(initialLimit);

  const status = showPending ? "all" : "scored";
  const { data, isLoading } = useSignalHistory(symbol, limit, status);
  const rows = (data as SignalHistory | undefined)?.rows ?? [];

  return (
    <div className="border border-line-1 bg-surface-1 flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-line-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          History
          <HelpTip k="signalHistory" className="ml-1" />
        </span>
        <button
          type="button"
          onClick={() => setShowPending((p) => !p)}
          className={`font-mono text-[10px] uppercase tracking-widest ${
            showPending ? "text-accent" : "text-ink-4"
          }`}
        >
          {showPending ? "Hide Pending" : "Show Pending"}
        </button>
      </div>

      <div className="overflow-auto flex-1">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-line-1 text-ink-3 text-[10px] uppercase tracking-widest">
              <th className="text-left px-3 py-1.5">Horizon End</th>
              <th className="text-left px-3 py-1.5">Model</th>
              <th className="text-left px-3 py-1.5">Dir</th>
              <th className="text-left px-3 py-1.5">Conf</th>
              <th className="text-right px-3 py-1.5">Exp %</th>
              <th className="text-right px-3 py-1.5">Real %</th>
              <th className="text-right px-3 py-1.5">Δ</th>
              <th className="text-center px-3 py-1.5">Out</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={8} className="text-center text-ink-4 py-4">
                  Loading...
                </td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center text-ink-4 py-4">
                  No scored forecasts in range.
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-line-1 hover:bg-surface-2"
              >
                <td className="px-3 py-1.5 tabular-nums text-ink-3">
                  {fmtDate(row.horizon_end)}
                </td>
                <td className="px-3 py-1.5 text-ink-2">
                  {row.model_name.replace(/_/g, " ")}
                </td>
                <td
                  className={`px-3 py-1.5 ${
                    row.direction === "bullish"
                      ? "text-up"
                      : row.direction === "bearish"
                        ? "text-down"
                        : "text-flat"
                  }`}
                >
                  {row.direction.slice(0, 4)}
                </td>
                <td
                  className={`px-3 py-1.5 ${
                    row.confidence === "high"
                      ? "text-conf-high"
                      : row.confidence === "medium"
                        ? "text-conf-medium"
                        : "text-conf-low"
                  }`}
                >
                  {row.confidence}
                </td>
                <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                  {fmtPct(row.expected_pct)}
                </td>
                <td
                  className={`px-3 py-1.5 tabular-nums text-right ${
                    row.realized_pct === null
                      ? "text-ink-4"
                      : row.realized_pct >= 0
                        ? "text-up"
                        : "text-down"
                  }`}
                >
                  {fmtPct(row.realized_pct)}
                </td>
                <td
                  className={`px-3 py-1.5 tabular-nums text-right ${
                    row.delta_from_expected_pct === null
                      ? "text-ink-4"
                      : row.delta_from_expected_pct >= 0
                        ? "text-up"
                        : "text-down"
                  }`}
                >
                  {fmtPct(row.delta_from_expected_pct)}
                </td>
                <td className="px-3 py-1.5 text-center">
                  <OutcomeGlyph outcome={row.outcome} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {limit === 25 && rows.length >= 25 && (
        <div className="px-3 py-2 border-t border-line-1">
          <button
            type="button"
            onClick={() => setLimit(100)}
            className="text-accent text-[10px] font-mono uppercase tracking-widest"
          >
            Expand to 100
          </button>
        </div>
      )}
    </div>
  );
}
