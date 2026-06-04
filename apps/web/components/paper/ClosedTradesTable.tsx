"use client";

import { useState } from "react";
import type { Trade } from "../../app/(app)/paper/types";

interface Props {
  trades: Trade[];
}

type SortKey =
  | "closed_at"
  | "side"
  | "size_contracts"
  | "entry_price"
  | "exit_price"
  | "outcome_pnl";

interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

function compare(a: Trade, b: Trade, key: SortKey): number {
  const av = a[key];
  const bv = b[key];
  if (av === null && bv === null) return 0;
  if (av === null) return 1;
  if (bv === null) return -1;
  if (typeof av === "number" && typeof bv === "number") return av - bv;
  return String(av).localeCompare(String(bv));
}

function buildCsv(trades: Trade[]): string {
  const headers = [
    "closed_at",
    "contract",
    "side",
    "size",
    "entry",
    "exit",
    "pnl",
  ];
  const rows = trades.map((t) => [
    t.closed_at ?? "",
    t.contract_id ?? "NG",
    t.side,
    t.size_contracts,
    t.entry_price,
    t.exit_price ?? "",
    t.outcome_pnl ?? "",
  ]);
  const lines = [
    headers.join(","),
    ...rows.map((r) => r.map((v) => JSON.stringify(v)).join(",")),
  ];
  return lines.join("\n");
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function ClosedTradesTable({ trades }: Props) {
  const [sort, setSort] = useState<SortState>({
    key: "closed_at",
    dir: "desc",
  });

  const sorted = [...trades].sort((a, b) => {
    const cmp = compare(a, b, sort.key);
    return sort.dir === "asc" ? cmp : -cmp;
  });

  const toggleSort = (key: SortKey) => {
    setSort((s) =>
      s.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "desc" },
    );
  };

  const onExport = () => {
    const csv = buildCsv(sorted);
    const today = new Date().toISOString().slice(0, 10);
    downloadCsv(`closed-trades-${today}.csv`, csv);
  };

  const sortIndicator = (key: SortKey) =>
    sort.key === key ? (sort.dir === "asc" ? " ▲" : " ▼") : "";

  return (
    <div className="border border-line-1 bg-surface-1 flex flex-col">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-3">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Closed Trades
        </span>
        <button
          type="button"
          onClick={onExport}
          disabled={trades.length === 0}
          className="ml-auto font-mono text-[10px] uppercase tracking-widest text-accent disabled:text-ink-4"
          data-testid="export-csv"
        >
          Export CSV
        </button>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-line-1 text-ink-3 text-[10px] uppercase tracking-widest">
              <th className="text-left px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("closed_at")}
                  className="w-full text-left uppercase tracking-widest cursor-pointer"
                >
                  Closed{sortIndicator("closed_at")}
                </button>
              </th>
              <th className="text-left px-3 py-1.5">Contract</th>
              <th className="text-left px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("side")}
                  className="w-full text-left uppercase tracking-widest cursor-pointer"
                >
                  Side{sortIndicator("side")}
                </button>
              </th>
              <th className="text-right px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("size_contracts")}
                  className="w-full text-right uppercase tracking-widest cursor-pointer"
                >
                  Size{sortIndicator("size_contracts")}
                </button>
              </th>
              <th className="text-right px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("entry_price")}
                  className="w-full text-right uppercase tracking-widest cursor-pointer"
                >
                  Entry{sortIndicator("entry_price")}
                </button>
              </th>
              <th className="text-right px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("exit_price")}
                  className="w-full text-right uppercase tracking-widest cursor-pointer"
                >
                  Exit{sortIndicator("exit_price")}
                </button>
              </th>
              <th className="text-right px-3 py-1.5 cursor-pointer">
                <button
                  type="button"
                  onClick={() => toggleSort("outcome_pnl")}
                  className="w-full text-right uppercase tracking-widest cursor-pointer"
                >
                  PnL{sortIndicator("outcome_pnl")}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center text-ink-4 py-4">
                  No closed trades.
                </td>
              </tr>
            )}
            {sorted.map((t) => {
              const pnl = t.outcome_pnl;
              const pnlClass =
                pnl === null
                  ? "text-ink-4"
                  : pnl > 0
                    ? "text-up"
                    : pnl < 0
                      ? "text-down"
                      : "text-flat";
              return (
                <tr
                  key={t.id}
                  className="border-b border-line-1 hover:bg-surface-2"
                  data-testid="closed-trade-row"
                >
                  <td className="px-3 py-1.5 tabular-nums text-ink-3">
                    {fmtDate(t.closed_at)}
                  </td>
                  <td className="px-3 py-1.5 text-ink-2">
                    {t.contract_id ? t.contract_id.slice(0, 8) : "NG"}
                  </td>
                  <td
                    className={`px-3 py-1.5 ${
                      t.side === "long" ? "text-up" : "text-down"
                    }`}
                  >
                    {t.side}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-2">
                    {t.size_contracts.toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-2">
                    {t.entry_price.toFixed(3)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-right text-ink-2">
                    {t.exit_price !== null ? t.exit_price.toFixed(3) : "—"}
                  </td>
                  <td
                    className={`px-3 py-1.5 tabular-nums text-right ${pnlClass}`}
                  >
                    {pnl === null
                      ? "—"
                      : `${pnl >= 0 ? "+" : "-"}$${Math.abs(pnl).toFixed(0)}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
