import type { ScenarioTemplate, Shock } from "@/app/(app)/scenarios/types";
import { LayoutGrid } from "lucide-react";

interface Props {
  templates: ScenarioTemplate[];
  onSelect: (template: ScenarioTemplate) => void;
  selectedId?: string;
}

function summarizeShocks(shocks: Shock[]): string {
  const counts = new Map<string, number>();
  for (const s of shocks) {
    counts.set(s.type, (counts.get(s.type) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([type, n]) => `${n}× ${type.replace("_", " ")}`)
    .join(" · ");
}

export function TemplateGallery({ templates, onSelect, selectedId }: Props) {
  if (templates.length === 0) {
    return (
      <div className="border border-line-1 bg-surface-1 p-6">
        <div className="flex flex-col items-center gap-1.5 text-ink-4">
          <LayoutGrid size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px]">No scenario templates available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {templates.map((t) => {
        const selected = selectedId === t.id;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(t)}
            className={`card-interactive text-left border bg-surface-1 p-3 flex flex-col gap-2 ${
              selected ? "border-accent" : "border-line-1"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-mono text-xs text-ink-2 leading-tight">
                {t.name}
              </span>
              {selected && (
                <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
                  loaded
                </span>
              )}
            </div>
            <p className="text-xs text-ink-3 line-clamp-3 leading-relaxed">
              {t.description}
            </p>
            <span className="font-mono text-[10px] text-ink-4 mt-auto">
              {summarizeShocks(t.shocks)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
