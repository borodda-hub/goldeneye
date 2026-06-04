"use client";

import type { TickerItem } from "@/lib/api";
import { useTickerQuotes } from "@/lib/queries";

function fmtPrice(value: number | null): string {
  if (value === null) return "—";
  // Yields are tiny, indices are 4-5 digit; pick precision by magnitude.
  if (Math.abs(value) >= 1000) return value.toFixed(2);
  if (Math.abs(value) >= 100) return value.toFixed(2);
  if (Math.abs(value) >= 1) return value.toFixed(2);
  return value.toFixed(3);
}

function fmtChangePct(value: number | null): string {
  if (value === null) return "—";
  const pct = value * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function tone(value: number | null): string {
  if (value === null || value === 0) return "text-flat";
  return value > 0 ? "text-up" : "text-down";
}

function Cell({ item }: { item: TickerItem }) {
  return (
    <span
      className="inline-flex items-baseline gap-2 px-4 py-1.5 shrink-0"
      data-symbol={item.symbol}
    >
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-3">
        {item.label}
      </span>
      <span className="font-mono tabular-nums text-xs text-ink-1">
        {fmtPrice(item.last_price)}
      </span>
      <span
        className={`font-mono tabular-nums text-xs ${tone(item.change_pct)}`}
      >
        {fmtChangePct(item.change_pct)}
      </span>
      <span aria-hidden="true" className="text-ink-4">
        ·
      </span>
    </span>
  );
}

export function DashboardTicker() {
  const { data, isLoading, error } = useTickerQuotes();
  const items = data?.items ?? [];

  if (isLoading) {
    return (
      <div
        className="border-t border-line-1 bg-surface-1 h-8 flex items-center px-4"
        aria-label="Market ticker loading"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-4">
          Loading ticker…
        </span>
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div
        className="border-t border-line-1 bg-surface-1 h-8 flex items-center px-4"
        aria-label="Market ticker unavailable"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-down">
          Ticker unavailable
        </span>
      </div>
    );
  }

  return (
    <div
      className="border-t border-line-1 bg-surface-1 overflow-hidden h-8"
      aria-label="Market ticker"
      data-testid="dashboard-ticker"
    >
      <div className="ticker-track">
        {/* First copy */}
        {items.map((item) => (
          <Cell key={`a-${item.symbol}`} item={item} />
        ))}
        {/* Second copy — seamless loop via translateX(-50%) */}
        {items.map((item) => (
          <Cell key={`b-${item.symbol}`} item={item} />
        ))}
      </div>
    </div>
  );
}
