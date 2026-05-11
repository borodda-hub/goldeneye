import { DirectionChip } from "@/components/DirectionChip";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import type { ModelResult } from "@/app/(app)/signals/types";

interface Props {
  model: ModelResult;
}

export function ModelCard({ model }: Props) {
  const topSupporting = model.supporting[0] ?? null;
  const topContradicting = model.contradicting[0] ?? null;
  const dimmed = model.direction === "neutral" && model.confidence === "low";

  return (
    <div
      className={`border border-line-1 bg-surface-1 p-3 flex flex-col gap-2 ${dimmed ? "opacity-60" : ""}`}
    >
      {/* Header: model name + horizon */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-ink-2">
          {model.model_name.replace(/_/g, " ")}
        </span>
        <span className="font-mono text-xs text-ink-4 border border-line-1 px-1">
          {model.horizon}
        </span>
      </div>

      {/* Direction + confidence + expected pct */}
      <div className="flex items-center gap-2">
        <DirectionChip direction={model.direction} />
        <ConfidenceBar confidence={model.confidence} />
        {model.expected_pct !== null && model.expected_pct !== undefined && (
          <span
            className={`font-mono tabular-nums text-xs ml-auto ${
              model.expected_pct >= 0 ? "text-up" : "text-down"
            }`}
          >
            {model.expected_pct >= 0 ? "+" : ""}
            {(model.expected_pct * 100).toFixed(2)}%
          </span>
        )}
      </div>

      {/* Inputs used tags */}
      <div className="flex flex-wrap gap-1">
        {model.inputs_used.map((inp) => (
          <span
            key={inp}
            className="font-mono text-[10px] text-ink-4 border border-line-1 px-1"
          >
            {inp.replace("latest_", "")}
          </span>
        ))}
      </div>

      {/* Top supporting factor */}
      {topSupporting && (
        <div className="border-l-2 border-up pl-2">
          <div className="font-mono text-xs text-ink-2 truncate">
            {topSupporting.factor}
          </div>
          <div className="text-xs text-ink-3 line-clamp-2">{topSupporting.note}</div>
        </div>
      )}

      {/* Top contradicting factor */}
      {topContradicting && (
        <div className="border-l-2 border-down pl-2">
          <div className="font-mono text-xs text-ink-2 truncate">
            {topContradicting.factor}
          </div>
          <div className="text-xs text-ink-3 line-clamp-2">{topContradicting.note}</div>
        </div>
      )}
    </div>
  );
}
