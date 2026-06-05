"use client";

import type { RecentEvent } from "@/app/(app)/dashboard/types";
import { EventMarker } from "@/components/EventMarker";
import { HelpTip } from "@/components/HelpTip";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

interface Props {
  events: RecentEvent[];
}

function relativeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const mins = Math.floor((Date.now() - then) / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toISOString().slice(5, 10);
}

function EventPopup({
  event,
  onClose,
}: {
  event: RecentEvent;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const body = (event.body || "").trim();

  return (
    <div
      ref={ref}
      // biome-ignore lint/a11y/useSemanticElements: anchored click-outside popup; native <dialog> would break absolute positioning and focus model
      role="dialog"
      aria-label={event.headline}
      // Anchor to the events card's top-left, then shift up + left so the
      // popup straddles the corner where the 4 surrounding cards meet
      // (chart / bias / curve / events).
      className="absolute z-30 top-0 left-0 -translate-x-1/3 -translate-y-1/2 w-full max-w-[420px] border-2 border-accent rounded-md bg-surface-1 shadow-2xl shadow-black/60 flex flex-col"
    >
      <div className="flex items-start justify-between gap-3 px-3 pt-2.5 pb-2 border-b border-line-1">
        <div className="flex-1 min-w-0">
          <div className="font-mono text-[10px] text-accent uppercase tracking-eyebrow mb-1">
            {event.source ?? "News"} · {relativeAgo(event.published_at)}
          </div>
          <div className="text-sm font-semibold text-ink-1 leading-snug">
            {event.headline}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="font-mono text-sm leading-none text-ink-3 hover:text-ink-1 px-1.5 py-0.5 -mt-0.5 rounded-sm hover:bg-surface-2"
        >
          ×
        </button>
      </div>
      <div className="px-3 py-2.5 flex-1 min-h-0 overflow-auto">
        {body ? (
          <p className="text-[13px] text-ink-2 leading-relaxed">{body}</p>
        ) : (
          <p className="text-[12px] text-ink-4 italic font-mono">
            No summary available for this item.
          </p>
        )}
      </div>
      {event.url && (
        <div className="px-3 py-2 border-t border-line-1">
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-accent hover:text-accent-bright"
          >
            ↗ Open source
          </a>
        </div>
      )}
    </div>
  );
}

export function RecentEventsList({ events }: Props) {
  const [selected, setSelected] = useState<RecentEvent | null>(null);

  return (
    <div className="relative border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
      <div className="flex items-center justify-between px-3 pt-2 pb-1">
        <span className="text-xs text-ink-3 uppercase tracking-widest">
          Recent Events
          <HelpTip k="recentEvents" className="ml-1" />
        </span>
        <Link
          href="/signals"
          aria-label="Open Signal Lab"
          className="accent-pulse inline-flex items-center rounded-full border border-accent bg-accent-soft px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-eyebrow text-accent-bright hover:bg-accent hover:text-bg transition-colors"
        >
          Signal Lab →
        </Link>
      </div>
      {events.length === 0 ? (
        <p className="text-ink-4 text-xs font-mono p-3">No recent events.</p>
      ) : (
        <div className="flex flex-col divide-y divide-line-1 overflow-auto flex-1">
          {events.map((ev) => (
            <button
              key={ev.id}
              type="button"
              onClick={() => setSelected(ev)}
              className="text-left px-3 py-2 hover:bg-surface-2 transition-colors group"
              title={ev.source ? `${ev.source} · ${ev.headline}` : ev.headline}
            >
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <EventMarker
                    event={{
                      headline: ev.headline,
                      category: ev.category,
                      impact_score: ev.impact_score,
                      published_at: ev.published_at,
                    }}
                  />
                </div>
                <span className="font-mono text-[10px] text-ink-4 tabular-nums shrink-0">
                  {relativeAgo(ev.published_at)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
      {selected && (
        <EventPopup event={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
