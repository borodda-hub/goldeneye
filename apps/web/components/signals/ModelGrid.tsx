import type { ModelResult } from "@/app/(app)/signals/types";
import { CpuIcon } from "lucide-react";
import { ModelCard } from "./ModelCard";

interface Props {
  models: ModelResult[];
}

export function ModelGrid({ models }: Props) {
  if (models.length === 0) {
    return (
      <div className="border border-line-1 bg-surface-1 p-6">
        <div className="flex flex-col items-center gap-1.5 text-ink-4">
          <CpuIcon size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px]">No model results available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      {models.map((model) => (
        <ModelCard key={model.model_name} model={model} />
      ))}
    </div>
  );
}
