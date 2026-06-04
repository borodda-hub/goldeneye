import type { ModelResult } from "@/app/(app)/signals/types";
import { ModelCard } from "./ModelCard";

interface Props {
  models: ModelResult[];
}

export function ModelGrid({ models }: Props) {
  if (models.length === 0) {
    return (
      <div className="text-xs text-ink-4 font-mono border border-line-1 p-3">
        No model results available.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-4">
      {models.map((model) => (
        <ModelCard key={model.model_name} model={model} />
      ))}
    </div>
  );
}
