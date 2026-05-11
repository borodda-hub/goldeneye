import { DirectionChip } from "@/components/DirectionChip";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import type { EnsembleData } from "@/app/(app)/signals/types";

interface Props {
  ensemble: EnsembleData;
}

export function EnsembleHeader({ ensemble }: Props) {
  const {
    direction,
    confidence,
    vol_regime,
    expected_pct,
    range,
    agreement,
    confidence_rationale,
    caveats,
  } = ensemble;

  const diversityColor =
    agreement.input_diversity === "high"
      ? "text-up"
      : agreement.input_diversity === "medium"
        ? "text-conf-medium"
        : "text-ink-4";

  return (
    <div className="border border-line-1 bg-surface-1 p-4">
      <div className="flex items-start gap-8">
        {/* Direction + confidence */}
        <div className="flex items-center gap-3">
          <DirectionChip direction={direction} />
          <ConfidenceBar confidence={confidence} />
        </div>

        {/* Vol regime + expected range */}
        <div className="flex flex-col gap-1">
          {vol_regime && (
            <span className="font-mono text-xs text-ink-3 uppercase tracking-widest">
              {vol_regime}
            </span>
          )}
          {expected_pct !== null && expected_pct !== undefined ? (
            <span className="font-mono tabular-nums text-sm text-ink-2">
              {expected_pct >= 0 ? "+" : ""}
              {(expected_pct * 100).toFixed(2)}%
              {range && (
                <span className="text-ink-4 text-xs ml-2">
                  [{(range.low_pct * 100).toFixed(2)}% –{" "}
                  {(range.high_pct * 100).toFixed(2)}%]
                </span>
              )}
            </span>
          ) : (
            <span className="font-mono text-xs text-ink-4">— no range</span>
          )}
        </div>

        {/* Agreement — right-aligned */}
        <div className="ml-auto flex flex-col items-end gap-1">
          <span className="font-mono text-xs text-ink-3">
            {agreement.bullish} bull · {agreement.bearish} bear ·{" "}
            {agreement.neutral} neutral of {agreement.total} · diversity:{" "}
            <span className={diversityColor}>{agreement.input_diversity}</span>
          </span>
        </div>
      </div>

      {/* Confidence rationale */}
      {confidence_rationale.length > 0 && (
        <ul className="mt-3 space-y-0.5">
          {confidence_rationale.map((r, i) => (
            <li key={i} className="text-xs text-ink-3 font-mono">
              · {r}
            </li>
          ))}
        </ul>
      )}

      {/* Caveats */}
      {caveats.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {caveats.map((c, i) => (
            <li key={i} className="text-xs text-conf-low font-mono">
              ⚠ {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
