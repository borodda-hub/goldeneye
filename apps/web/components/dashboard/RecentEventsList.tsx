import type { RecentEvent } from "@/app/(app)/dashboard/types";
import { EventMarker } from "@/components/EventMarker";

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

export function RecentEventsList({ events }: Props) {
  return (
    <div className="border border-line-1 rounded-md bg-surface-1 flex flex-col h-full">
      <div className="px-3 pt-2 pb-1 text-xs text-ink-3 uppercase tracking-widest">
        Recent Events
      </div>
      {events.length === 0 ? (
        <p className="text-ink-4 text-xs font-mono p-3">No recent events.</p>
      ) : (
        <div className="flex flex-col divide-y divide-line-1 overflow-auto flex-1">
          {events.map((ev) => {
            const inner = (
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
            );
            if (ev.url) {
              return (
                <a
                  key={ev.id}
                  href={ev.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block px-3 py-2 hover:bg-surface-2 transition-colors group"
                  title={ev.source ? `${ev.source} · ${ev.headline}` : ev.headline}
                >
                  {inner}
                </a>
              );
            }
            return (
              <div key={ev.id} className="px-3 py-2">
                {inner}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
