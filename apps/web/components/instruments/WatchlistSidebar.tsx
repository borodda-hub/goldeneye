"use client";

import type { InstrumentRow } from "@/lib/api";
import { useInstruments } from "@/lib/queries";
import { useActiveInstrument } from "@/lib/useActiveInstrument";

interface Props {
  className?: string;
}

function fmtPrice(value: number | null): string {
  if (value === null) return "—";
  // NG trades in dollars to 3 decimals; CL in dollars to 2. Pick by magnitude.
  return value >= 20 ? value.toFixed(2) : value.toFixed(3);
}

function fmtChangePct(value: number | null): string {
  if (value === null) return "—";
  const pct = value * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function changeColor(value: number | null): string {
  if (value === null || value === 0) return "text-flat";
  return value > 0 ? "text-up" : "text-down";
}

function Row({
  row,
  active,
  onSelect,
}: {
  row: InstrumentRow;
  active: boolean;
  onSelect: (symbol: string) => void;
}) {
  const q = row.quote;
  return (
    <button
      type="button"
      onClick={() => onSelect(row.symbol)}
      aria-current={active ? "true" : undefined}
      className={`text-left w-full px-3 py-2.5 border-l-4 transition-colors ${
        active
          ? "border-l-accent bg-surface-2"
          : "border-l-transparent hover:bg-surface-2/60 hover:border-l-line-2"
      }`}
      data-symbol={row.symbol}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span
          className={`font-mono text-sm font-semibold ${
            active ? "text-accent-bright" : "text-ink-1"
          }`}
        >
          {row.symbol}
        </span>
        <span
          className={`font-mono text-xs tabular-nums ${changeColor(q.change_pct)}`}
        >
          {fmtChangePct(q.change_pct)}
        </span>
      </div>
      <div className="flex items-baseline justify-between gap-2 mt-0.5">
        <span className="text-[10px] text-ink-3 leading-tight truncate max-w-[110px]">
          {row.name}
        </span>
        <span className="font-mono text-xs tabular-nums text-ink-2">
          {fmtPrice(q.last_price)}
        </span>
      </div>
    </button>
  );
}

export function WatchlistSidebar({ className = "" }: Props) {
  const { data, isLoading, error } = useInstruments();
  const { activeSymbol, setActiveSymbol } = useActiveInstrument();

  return (
    <aside
      aria-label="Watchlist"
      className={`flex flex-col border border-line-1 bg-surface-1 ${className}`}
    >
      <div className="flex items-center justify-between px-3 pt-2 pb-1 border-b border-line-1">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
          Watchlist
        </span>
        <span className="font-mono text-[10px] tabular-nums text-ink-4">
          {data?.instruments.length ?? 0}
        </span>
      </div>
      {isLoading ? (
        <p className="px-3 py-3 text-xs text-ink-4 font-mono">Loading…</p>
      ) : error || !data ? (
        <p className="px-3 py-3 text-xs text-down font-mono">
          Failed to load watchlist.
        </p>
      ) : (
        <div className="flex flex-col">
          {data.instruments.map((row) => (
            <Row
              key={row.symbol}
              row={row}
              active={row.symbol === activeSymbol}
              onSelect={setActiveSymbol}
            />
          ))}
        </div>
      )}
    </aside>
  );
}
