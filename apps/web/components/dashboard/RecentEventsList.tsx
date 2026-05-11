import type { RecentEvent } from "@/app/(app)/dashboard/types";
import { EventMarker } from "@/components/EventMarker";

interface Props {
  events: RecentEvent[];
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
          {events.map((ev) => (
            <div key={ev.id} className="px-3 py-2">
              <EventMarker
                event={{
                  headline: ev.headline,
                  category: ev.category,
                  impact_score: ev.impact_score,
                  published_at: ev.published_at,
                }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
