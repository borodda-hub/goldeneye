import type { Resolution } from "@/app/(app)/chart/types";

const RESOLUTIONS: Resolution[] = ["1m", "5m", "15m", "1h", "1d"];

interface Props {
  resolution: Resolution;
  onResolutionChange: (r: Resolution) => void;
  showSMA20: boolean;
  showEMA50: boolean;
  onToggleSMA20: () => void;
  onToggleEMA50: () => void;
  contractCode: string;
}

export function ChartToolbar({
  resolution,
  onResolutionChange,
  showSMA20,
  showEMA50,
  onToggleSMA20,
  onToggleEMA50,
  contractCode,
}: Props) {
  return (
    <div className="flex items-center gap-4 px-0 py-2 border-b border-line-1 bg-surface-0 shrink-0">
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

      {/* SMA 20 toggle */}
      <button
        type="button"
        onClick={onToggleSMA20}
        className="flex items-center gap-1.5 text-xs font-mono"
        aria-pressed={showSMA20}
      >
        <span
          className={`w-3 h-0.5 rounded-full ${showSMA20 ? "bg-accent" : "bg-line-2"}`}
        />
        <span className={showSMA20 ? "text-ink-3" : "text-ink-4"}>SMA 20</span>
      </button>

      {/* EMA 50 toggle */}
      <button
        type="button"
        onClick={onToggleEMA50}
        className="flex items-center gap-1.5 text-xs font-mono"
        aria-pressed={showEMA50}
      >
        <span
          className={`w-3 h-0.5 rounded-full ${showEMA50 ? "bg-accent" : "bg-line-2"}`}
        />
        <span className={showEMA50 ? "text-ink-3" : "text-ink-4"}>EMA 50</span>
      </button>

      {/* Contract code */}
      <span className="font-mono text-xs text-ink-3 ml-auto">{contractCode}</span>
    </div>
  );
}
