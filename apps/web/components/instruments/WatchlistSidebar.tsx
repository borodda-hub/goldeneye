"use client";

import { WatchlistSparkline } from "@/components/instruments/WatchlistSparkline";
import type { InstrumentRow } from "@/lib/api";
import { useInstruments } from "@/lib/queries";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { flashBgClass, usePriceFlash } from "@/lib/usePriceFlash";

interface Props {
  className?: string;
}

function fmtPrice(value: number | null): string {
  if (value === null) return "—";
  // NG trades in dollars to 3 decimals; CL in dollars to 2. Pick by magnitude.
  return value >= 20 ? value.toFixed(2) : value.toFixed(3);
}

function fmtChangeAbs(value: number | null): string {
  if (value === null) return "—";
  const abs = Math.abs(value);
  return abs >= 20 ? abs.toFixed(2) : abs.toFixed(3);
}

function fmtChangePct(value: number | null): string {
  if (value === null) return "—";
  const pct = Math.abs(value) * 100;
  return `${pct.toFixed(2)}%`;
}

function changeColor(value: number | null): string {
  if (value === null || value === 0) return "text-flat";
  return value > 0 ? "text-up" : "text-down";
}

function arrow(value: number | null): string {
  if (value === null || value === 0) return "·";
  return value > 0 ? "▲" : "▼";
}

function Row({
  row,
  rank,
  active,
  onSelect,
}: {
  row: InstrumentRow;
  rank: number;
  active: boolean;
  onSelect: (symbol: string) => void;
}) {
  const q = row.quote;
  const flash = usePriceFlash(q.last_price);
  const cc = changeColor(q.change_pct);
  return (
    <button
      type="button"
      onClick={() => onSelect(row.symbol)}
      aria-current={active ? "true" : undefined}
      className={`text-left w-full px-2.5 py-2 border-l-4 transition-colors duration-500 ${
        active
          ? "border-l-accent bg-surface-2"
          : "border-l-transparent hover:bg-surface-2/60 hover:border-l-line-2"
      } ${flashBgClass(flash)}`}
      data-symbol={row.symbol}
    >
      {/* Row 1: rank · symbol · sparkline (fluid) · pct */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] tabular-nums text-ink-4 w-3 text-right wl-rank">
          {rank}
        </span>
        <span
          className={`font-mono text-sm font-semibold wl-symbol ${
            active ? "text-accent-bright" : "text-ink-1"
          }`}
        >
          {row.symbol}
        </span>
        <WatchlistSparkline
          contractCode={q.front_month_code}
          changePct={q.change_pct}
        />
        <span className={`font-mono text-xs tabular-nums wl-pct ${cc}`}>
          {arrow(q.change_pct)} {fmtChangePct(q.change_pct)}
        </span>
      </div>
      {/* Row 2: name · last · net change abs */}
      <div className="flex items-baseline justify-between gap-2 mt-1 pl-5">
        <span className="text-[10px] text-ink-3 leading-tight truncate max-w-[80px] wl-name">
          {row.name}
        </span>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs tabular-nums text-ink-1 wl-price">
            {fmtPrice(q.last_price)}
          </span>
          <span className={`font-mono text-[10px] tabular-nums wl-abs ${cc}`}>
            {arrow(q.change_abs)} {fmtChangeAbs(q.change_abs)}
          </span>
        </div>
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
      className={`watchlist-cq flex flex-col border border-line-1 bg-surface-1 max-h-[calc(100vh-7rem)] ${className}`}
    >
      <div className="flex items-center justify-between px-3 pt-2 pb-1 border-b border-line-1 shrink-0">
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
        <div className="flex flex-col overflow-y-auto">
          {data.instruments.map((row, idx) => (
            <Row
              key={row.symbol}
              row={row}
              rank={idx + 1}
              active={row.symbol === activeSymbol}
              onSelect={setActiveSymbol}
            />
          ))}
        </div>
      )}
    </aside>
  );
}
