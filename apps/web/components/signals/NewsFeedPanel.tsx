"use client";

import { useRecentNews } from "@/lib/queries";

interface NewsEvent {
  published_at: string;
  source: string;
  headline: string;
  body?: string | null;
  category?: string | null;
  impact_score?: number | null;
  url?: string | null;
}

interface NewsResponse {
  events: NewsEvent[];
  count: number;
}

const SOURCE_LABEL: Record<string, string> = {
  eia_today_in_energy: "EIA",
  yahoo_finance_ng: "Yahoo Finance",
};

const CATEGORY_COLOR: Record<string, string> = {
  storage: "text-conf-medium",
  weather: "text-accent",
  lng_export: "text-up",
  production: "text-ink-2",
  regulatory: "text-conf-low",
  geopolitical: "text-down",
  other: "text-ink-3",
};

function formatRelative(iso: string): string {
  try {
    const ts = new Date(iso).getTime();
    const deltaMin = Math.floor((Date.now() - ts) / 60_000);
    if (deltaMin < 1) return "just now";
    if (deltaMin < 60) return `${deltaMin}m ago`;
    const deltaH = Math.floor(deltaMin / 60);
    if (deltaH < 24) return `${deltaH}h ago`;
    const deltaD = Math.floor(deltaH / 24);
    return `${deltaD}d ago`;
  } catch {
    return iso;
  }
}

function NewsRow({ event }: { event: NewsEvent }) {
  const sourceLabel = SOURCE_LABEL[event.source] ?? event.source;
  const categoryColor =
    CATEGORY_COLOR[event.category ?? "other"] ?? CATEGORY_COLOR.other;
  const headline = (
    <span className="text-ink-1 text-sm leading-snug">{event.headline}</span>
  );
  return (
    <li className="flex flex-col gap-0.5 py-1.5 px-3 border-b border-line-1/60 hover:bg-surface-2/40">
      <div className="flex items-baseline gap-2">
        {event.url ? (
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline hover:text-accent flex-1 min-w-0"
          >
            {headline}
          </a>
        ) : (
          <span className="flex-1 min-w-0">{headline}</span>
        )}
        <span
          className={`font-mono text-[10px] uppercase tracking-widest shrink-0 ${categoryColor}`}
        >
          {event.category ?? "other"}
        </span>
      </div>
      <div className="flex items-center gap-2 font-mono text-[10px] text-ink-4">
        <span>{sourceLabel}</span>
        <span>·</span>
        <span>{formatRelative(event.published_at)}</span>
      </div>
    </li>
  );
}

interface NewsFeedPanelProps {
  symbol?: string;
}

export function NewsFeedPanel({ symbol = "NG" }: NewsFeedPanelProps = {}) {
  const { data, isLoading, isError } = useRecentNews(symbol, 15);
  const resp = data as NewsResponse | undefined;
  const events = resp?.events ?? [];

  return (
    <div
      className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full"
      data-testid="news-feed-panel"
    >
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <span className="text-xs text-ink-3 uppercase tracking-widest">
          Supporting News · Live
        </span>
        <span className="font-mono text-[10px] text-ink-4">
          {events.length > 0 ? `${events.length} items` : ""}
        </span>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-ink-4 text-xs font-mono">
          Loading news…
        </div>
      ) : isError ? (
        <div className="flex-1 flex items-center justify-center text-ink-4 text-xs font-mono">
          News feed unavailable.
        </div>
      ) : events.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-ink-4 text-xs font-mono">
          No recent NG-relevant items.
        </div>
      ) : (
        <ul className="flex-1 overflow-auto divide-y divide-line-1/60">
          {events.map((e, i) => (
            <NewsRow key={`${e.source}-${e.published_at}-${i}`} event={e} />
          ))}
        </ul>
      )}

      <div className="border-t border-line-1 px-3 py-1 text-[10px] font-mono text-ink-4">
        Sources: EIA &middot; Yahoo Finance &middot; filtered for NG-relevance &middot; auto-refresh 5m
      </div>
    </div>
  );
}
