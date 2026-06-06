import type { ModelRollup } from "@/app/(app)/admin/types";
import { BrainCircuit, Inbox } from "lucide-react";

interface Props {
  models: ModelRollup[];
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function ModelHealthGrid({ models }: Props) {
  if (models.length === 0) {
    return (
      <div className="card-interactive border border-line-1 bg-surface-1">
        <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2">
          <BrainCircuit
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
            Model Health
          </span>
        </div>
        <div className="flex flex-col items-center gap-1.5 py-6 text-ink-4">
          <Inbox size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px]">No forecasts in the last 7 days</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card-interactive border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2">
        <BrainCircuit
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Model Health
        </span>
      </div>
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-line-1 text-ink-3 text-[10px] uppercase tracking-widest">
            <th className="text-left px-3 py-1.5">Model</th>
            <th className="text-left px-3 py-1.5">Last Forecast</th>
            <th className="text-right px-3 py-1.5">Samples (7d)</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.name} className="border-b border-line-1 last:border-b-0">
              <td className="px-3 py-1.5 text-ink-2">{m.name}</td>
              <td className="px-3 py-1.5 tabular-nums text-ink-3">
                {fmtTime(m.last_forecast_at)}
              </td>
              <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                {m.sample_count_7d}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
