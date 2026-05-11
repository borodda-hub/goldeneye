interface Props {
  direction: "bullish" | "bearish" | "neutral";
}

const STYLES: Record<Props["direction"], string> = {
  bullish: "bg-up-soft text-up",
  bearish: "bg-down-soft text-down",
  neutral: "bg-surface-2 text-flat",
};

const LABELS: Record<Props["direction"], string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Neutral",
};

export function DirectionChip({ direction }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[direction]}`}
    >
      {LABELS[direction]}
    </span>
  );
}
