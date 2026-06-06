import type { EnsembleData } from "@/app/(app)/signals/types";
import { ConfidenceBar } from "@/components/ConfidenceBar";

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

  const dir = direction.toLowerCase();
  const dirColor =
    dir === "bullish"
      ? "text-up"
      : dir === "bearish"
        ? "text-down"
        : "text-ink-2";
  const arrow = dir === "bullish" ? "▲" : dir === "bearish" ? "▼" : "◆";
  const label = dir.charAt(0).toUpperCase() + dir.slice(1);

  const moveColor =
    expected_pct == null
      ? "text-ink-3"
      : expected_pct >= 0
        ? "text-up"
        : "text-down";

  const diversityColor =
    agreement.input_diversity === "high"
      ? "text-up"
      : agreement.input_diversity === "medium"
        ? "text-conf-medium"
        : "text-ink-4";

  return (
    <div className="card-interactive border border-line-1 bg-surface-1 px-5 py-4">
      {/* ── Hero: the call leads ─────────────────────────────────────── */}
      <div className="flex items-center gap-x-8 gap-y-3 flex-wrap">
        {/* Direction — the visual anchor */}
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Ensemble signal · 1-day
          </span>
          <span
            className={`font-serif font-light text-[40px] leading-none tracking-[-0.02em] ${dirColor}`}
            style={{ fontVariationSettings: '"opsz" 72, "SOFT" 40' }}
          >
            <span className="text-[26px] align-middle mr-1.5">{arrow}</span>
            {label}
          </span>
        </div>

        {/* Expected move */}
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Expected move
          </span>
          {expected_pct !== null && expected_pct !== undefined ? (
            <>
              <span
                className={`font-mono font-medium tabular-nums text-2xl leading-none ${moveColor}`}
              >
                {expected_pct >= 0 ? "+" : ""}
                {(expected_pct * 100).toFixed(2)}%
              </span>
              {range && (
                <span className="font-mono text-[10px] text-ink-4 tabular-nums mt-0.5">
                  range {(range.low_pct * 100).toFixed(2)}% –{" "}
                  {(range.high_pct * 100).toFixed(2)}%
                </span>
              )}
            </>
          ) : (
            <span className="font-mono text-sm text-ink-4">— no range</span>
          )}
        </div>

        {/* Confidence */}
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Confidence
          </span>
          <div className="flex items-center gap-2">
            <ConfidenceBar confidence={confidence} />
            <span className="font-mono text-xs uppercase tracking-widest text-ink-2">
              {confidence}
            </span>
          </div>
          {vol_regime && (
            <span className="font-mono text-[10px] uppercase tracking-widest text-ink-4">
              {vol_regime} regime
            </span>
          )}
        </div>

        {/* Agreement — right-aligned support */}
        <div className="ml-auto flex flex-col items-end gap-1 text-right">
          <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-4">
            Model agreement
          </span>
          <span className="font-mono text-sm tabular-nums text-ink-2">
            <span className="text-up">{agreement.bullish}▲</span>{" "}
            <span className="text-down">{agreement.bearish}▼</span>{" "}
            <span className="text-ink-3">{agreement.neutral}◆</span>
            <span className="text-ink-4"> of {agreement.total}</span>
          </span>
          <span className="font-mono text-[10px] text-ink-4">
            input diversity:{" "}
            <span className={diversityColor}>{agreement.input_diversity}</span>
          </span>
        </div>
      </div>

      {/* ── Supporting: rationale + caveats ──────────────────────────── */}
      {(confidence_rationale.length > 0 || caveats.length > 0) && (
        <div className="mt-3 pt-3 border-t border-line-1 flex flex-col gap-0.5">
          {confidence_rationale.map((r, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
            <p key={`r${i}`} className="text-xs text-ink-3 font-mono">
              · {r}
            </p>
          ))}
          {caveats.map((c, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
            <p key={`c${i}`} className="text-xs text-conf-low font-mono">
              ⚠ {c}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
