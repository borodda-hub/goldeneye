interface Props {
  confidence: "low" | "medium" | "high";
}

const FILL_COUNT: Record<Props["confidence"], number> = {
  low: 1,
  medium: 2,
  high: 3,
};

const FILL_COLOR: Record<Props["confidence"], string> = {
  low: "bg-conf-low",
  medium: "bg-conf-medium",
  high: "bg-conf-high",
};

export function ConfidenceBar({ confidence }: Props) {
  const filled = FILL_COUNT[confidence];
  const color = FILL_COLOR[confidence];

  return (
    <div className="flex gap-1 items-center" aria-label={`Confidence: ${confidence}`}>
      {[1, 2, 3].map((seg) => (
        <div
          key={seg}
          className={`h-1.5 w-6 rounded-sm ${seg <= filled ? color : "bg-surface-2"}`}
          data-filled={seg <= filled}
        />
      ))}
    </div>
  );
}
