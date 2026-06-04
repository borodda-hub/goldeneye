import type {
  ChartType,
  RangePreset,
  Resolution,
} from "@/app/(app)/chart/types";

const RESOLUTIONS: Resolution[] = ["1m", "5m", "15m", "1h", "1d"];
const RANGES: RangePreset[] = ["3M", "6M", "1Y", "2Y", "5Y", "All"];
const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "candlestick", label: "Candles" },
  { value: "bars", label: "Bars" },
  { value: "heikin-ashi", label: "Heikin-Ashi" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
  { value: "baseline", label: "Baseline" },
];

interface Props {
  resolution: Resolution;
  onResolutionChange: (r: Resolution) => void;
  chartType: ChartType;
  onChartTypeChange: (t: ChartType) => void;
  range: RangePreset;
  onRangeChange: (r: RangePreset) => void;
  logScale: boolean;
  onToggleLog: () => void;
  showCurve: boolean;
  onToggleCurve: () => void;
  showPatterns: boolean;
  onTogglePatterns: () => void;
  patternCount: number;
  showAutoTa: boolean;
  onToggleAutoTa: () => void;
  indicatorCount: number;
  onOpenIndicators: () => void;
  onClearIndicators: () => void;
  onScreenshot: () => void;
  onFullscreen: () => void;
  contractCode: string;
}

const SEG_BASE = "px-2.5 py-1 text-xs font-mono";
const SEG_ON = "bg-accent-soft text-accent";
const SEG_OFF = "bg-surface-1 text-ink-3 hover:text-ink-1 hover:bg-surface-2";

function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div
      className="flex rounded border border-line-2 overflow-hidden"
      aria-label={label}
    >
      {options.map((o, i) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          aria-pressed={value === o}
          className={`${SEG_BASE} ${
            i < options.length - 1 ? "border-r border-line-2" : ""
          } ${value === o ? SEG_ON : SEG_OFF}`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

export function ChartToolbar({
  resolution,
  onResolutionChange,
  chartType,
  onChartTypeChange,
  range,
  onRangeChange,
  logScale,
  onToggleLog,
  showCurve,
  onToggleCurve,
  showPatterns,
  onTogglePatterns,
  patternCount,
  showAutoTa,
  onToggleAutoTa,
  indicatorCount,
  onOpenIndicators,
  onClearIndicators,
  onScreenshot,
  onFullscreen,
  contractCode,
}: Props) {
  return (
    <div
      className="flex flex-wrap items-center gap-2 px-0 py-2 border-b border-line-1 bg-surface-0 shrink-0"
      data-tour="chart-toolbar"
    >
      <Segmented
        options={RESOLUTIONS}
        value={resolution}
        onChange={onResolutionChange}
        label="Resolution"
      />
      <Segmented
        options={RANGES}
        value={range}
        onChange={onRangeChange}
        label="Date range"
      />

      {/* Chart type */}
      <select
        value={chartType}
        onChange={(e) => onChartTypeChange(e.target.value as ChartType)}
        aria-label="Chart type"
        className="rounded border border-line-2 bg-surface-1 text-ink-2 text-xs font-mono px-2 py-1 hover:bg-surface-2"
      >
        {CHART_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>

      {/* Log scale */}
      <button
        type="button"
        onClick={onToggleLog}
        aria-pressed={logScale}
        title="Logarithmic price scale"
        className={`rounded border border-line-2 ${SEG_BASE} ${
          logScale ? SEG_ON : SEG_OFF
        }`}
      >
        LOG
      </button>

      {/* Futures-curve overlay */}
      <button
        type="button"
        onClick={onToggleCurve}
        aria-pressed={showCurve}
        title="Overlay the forward futures curve"
        className={`rounded border border-line-2 ${SEG_BASE} ${
          showCurve ? SEG_ON : SEG_OFF
        }`}
      >
        Curve
      </button>

      {/* Candlestick patterns */}
      <button
        type="button"
        onClick={onTogglePatterns}
        aria-pressed={showPatterns}
        title="Detect candlestick patterns (descriptive, not signals)"
        className={`flex items-center gap-1.5 rounded border border-line-2 ${SEG_BASE} ${
          showPatterns ? SEG_ON : SEG_OFF
        }`}
      >
        <span>Patterns</span>
        {showPatterns && patternCount > 0 ? (
          <span className="text-accent tabular-nums">({patternCount})</span>
        ) : null}
      </button>

      {/* Auto-TA: support/resistance + trendlines + chart patterns */}
      <button
        type="button"
        onClick={onToggleAutoTa}
        aria-pressed={showAutoTa}
        title="Auto support/resistance, trendlines & chart patterns (descriptive)"
        className={`rounded border border-line-2 ${SEG_BASE} ${
          showAutoTa ? SEG_ON : SEG_OFF
        }`}
      >
        Auto-TA
      </button>

      {/* Indicators */}
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

      {/* Right side: export + fullscreen + contract */}
      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={onScreenshot}
          title="Download chart as PNG"
          aria-label="Download chart as PNG"
          className={`rounded border border-line-2 ${SEG_BASE} ${SEG_OFF}`}
        >
          PNG
        </button>
        <button
          type="button"
          onClick={onFullscreen}
          title="Toggle fullscreen"
          aria-label="Toggle fullscreen"
          className={`rounded border border-line-2 ${SEG_BASE} ${SEG_OFF}`}
        >
          ⛶
        </button>
        <span className="font-mono text-xs text-ink-3">{contractCode}</span>
      </div>
    </div>
  );
}
