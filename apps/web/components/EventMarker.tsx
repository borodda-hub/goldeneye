interface EventData {
  headline: string;
  category: string;
  impact_score?: number | null;
  published_at: string;
}

interface Props {
  event: EventData;
}

const CATEGORY_ICON: Record<string, string> = {
  weather: "🌤",
  storage: "🗄",
  production: "⛽",
  demand: "📈",
  regulation: "📋",
  geopolitical: "🌍",
};

function getCategoryIcon(category: string): string {
  return CATEGORY_ICON[category.toLowerCase()] ?? category.charAt(0).toUpperCase();
}

export function EventMarker({ event }: Props) {
  const impactWidth =
    event.impact_score != null
      ? `${Math.min(Math.max(event.impact_score * 100, 0), 100)}%`
      : "0%";

  return (
    <div className="flex items-center gap-2 text-ink-2 text-sm">
      <span className="w-5 shrink-0 text-center text-base leading-none">
        {getCategoryIcon(event.category)}
      </span>
      <span className="flex-1 truncate">{event.headline}</span>
      {event.impact_score != null && (
        <div className="w-16 h-1.5 bg-surface-2 rounded-sm shrink-0 overflow-hidden">
          <div
            className="h-full bg-accent rounded-sm"
            style={{ width: impactWidth }}
            aria-label={`Impact: ${event.impact_score}`}
          />
        </div>
      )}
    </div>
  );
}
