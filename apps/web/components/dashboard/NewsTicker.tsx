"use client";

import type { NewsTickerItem } from "@/lib/api";
import { useTickerNews } from "@/lib/queries";

function relativeAgo(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const mins = Math.floor((Date.now() - then) / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function Cell({ item }: { item: NewsTickerItem }) {
  const content = (
    <span className="inline-flex items-baseline gap-2 px-4 py-1.5 shrink-0 whitespace-nowrap">
      <span className="font-mono text-[10px] uppercase tracking-eyebrow text-accent">
        Bloomberg
      </span>
      <span className="text-xs text-ink-1 leading-none">{item.headline}</span>
      <span className="font-mono text-[10px] tabular-nums text-ink-4">
        {relativeAgo(item.published_at)}
      </span>
      <span aria-hidden="true" className="text-ink-4">
        ·
      </span>
    </span>
  );
  if (!item.url) return content;
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="hover:bg-surface-2 transition-colors"
      title={item.headline}
    >
      {content}
    </a>
  );
}

export function NewsTicker() {
  const { data, isLoading, error } = useTickerNews();
  const items = data?.items ?? [];

  if (isLoading) {
    return (
      <div
        className="border-t border-line-1 bg-surface-1 h-8 flex items-center px-4"
        aria-label="News ticker loading"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-4">
          Loading Bloomberg…
        </span>
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div
        className="border-t border-line-1 bg-surface-1 h-8 flex items-center px-4"
        aria-label="News ticker unavailable"
      >
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-down">
          News feed unavailable
        </span>
      </div>
    );
  }

  return (
    <div
      className="border-t border-line-1 bg-surface-1 overflow-hidden h-8"
      aria-label="Bloomberg news ticker"
      data-testid="dashboard-news-ticker"
    >
      <div className="ticker-track">
        {items.map((item, i) => (
          <Cell key={`a-${i}-${item.headline.slice(0, 24)}`} item={item} />
        ))}
        {items.map((item, i) => (
          <Cell key={`b-${i}-${item.headline.slice(0, 24)}`} item={item} />
        ))}
      </div>
    </div>
  );
}
