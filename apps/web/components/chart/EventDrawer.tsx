import type { EventMarkerData } from "@/app/(app)/chart/types";
import { EventMarker } from "@/components/EventMarker";

interface Props {
  events: EventMarkerData[];
  open: boolean;
  onToggle: () => void;
}

function formatDate(isoString: string): string {
  try {
    return isoString.split("T")[0];
  } catch {
    return isoString;
  }
}

export function EventDrawer({ events, open, onToggle }: Props) {
  if (!open) {
    return (
      <div className="bg-surface-1 border-l border-line-1 flex items-center justify-center w-8 h-full">
        <button
          type="button"
          onClick={onToggle}
          className="text-ink-4 hover:text-ink-1 text-xs"
          aria-label="Open events drawer"
        >
          ◁
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 border-l border-line-1 bg-surface-1 flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-line-1">
        <span className="text-xs text-ink-3 uppercase tracking-widest">
          Events
        </span>
        <button
          type="button"
          onClick={onToggle}
          className="text-ink-4 hover:text-ink-1 text-xs"
          aria-label="Close events drawer"
        >
          ▷
        </button>
      </div>
      {events.length === 0 ? (
        <p className="text-ink-4 text-xs font-mono p-3">No events in range.</p>
      ) : (
        <div className="flex-1 overflow-auto divide-y divide-line-1">
          {events.map((m, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
            <div key={i} className="px-3 py-2">
              <span className="text-ink-4 text-xs font-mono block mb-1">
                {formatDate(m.ts)}
              </span>
              <EventMarker
                event={{
                  headline: m.label,
                  category: m.kind,
                  impact_score: Math.abs(m.delta) / 100,
                  published_at: m.ts,
                }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
