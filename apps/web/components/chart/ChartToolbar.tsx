import type { Resolution } from "@/app/(app)/chart/types";

const RESOLUTIONS: Resolution[] = ["1m", "5m", "15m", "1h", "1d"];

interface Props {
  resolution: Resolution;
  onResolutionChange: (r: Resolution) => void;
  indicatorCount: number;
  onOpenIndicators: () => void;
  onClearIndicators: () => void;
  contractCode: string;
}

export function ChartToolbar({
  resolution,
  onResolutionChange,
  indicatorCount,
  onOpenIndicators,
  onClearIndicators,
  contractCode,
}: Props) {
  return (
    <div
      className="flex items-center gap-4 px-0 py-2 border-b border-line-1 bg-surface-0 shrink-0"
      data-tour="chart-toolbar"
    >
      {/* Resolution segmented control */}
      <div className="flex rounded border border-line-2 overflow-hidden">
        {RESOLUTIONS.map((r, i) => (
          <button
            key={r}
            type="button"
            onClick={() => onResolutionChange(r)}
            className={`px-3 py-1 text-xs font-mono ${
              i < RESOLUTIONS.length - 1 ? "border-r border-line-2" : ""
            } ${
              resolution === r
                ? "bg-accent-soft text-accent"
                : "bg-surface-1 text-ink-3 hover:text-ink-1 hover:bg-surface-2"
            }`}
            aria-pressed={resolution === r}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Indicators button group */}
      <div className="flex rounded border border-line-2 overflow-hidden">
        <button
          type="button"
          onClick={onOpenIndicators}
          className="flex items-center gap-2 px-3 py-1 text-xs font-mono bg-surface-1 text-ink-2 hover:text-ink-1 hover:bg-surface-2"
          aria-label="Open indicators picker"
        >
          <span>Indicators</span>
          {indicatorCount > 0 ? (
            <span className="text-accent tabular-nums">({indicatorCount})</span>
          ) : null}
        </button>
        {indicatorCount > 0 ? (
          <button
            type="button"
            onClick={onClearIndicators}
            className="px-2 py-1 text-xs font-mono border-l border-line-2 bg-surface-1 text-ink-3 hover:text-down hover:bg-surface-2"
            aria-label="Clear all indicators"
            title="Clear all indicators"
          >
            ×
          </button>
        ) : null}
      </div>

      {/* Contract code */}
      <span className="font-mono text-xs text-ink-3 ml-auto">
        {contractCode}
      </span>
    </div>
  );
}
