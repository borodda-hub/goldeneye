import type { RecentRun } from "@/app/(app)/scenarios/types";
import { HelpTip } from "@/components/HelpTip";
import { History, Inbox } from "lucide-react";

interface Props {
  runs: RecentRun[];
  onSelect?: (runId: string) => void;
}

function fmtDate(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function ScenarioHistoryList({ runs, onSelect }: Props) {
  return (
    <div className="card-interactive border border-line-1 bg-surface-1 flex flex-col">
      <div className="px-3 py-2 border-b border-line-1">
        <span className="flex items-center gap-2 font-mono text-[10px] text-accent uppercase tracking-widest">
          <History
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="text-ink-4"
          />
          Recent Runs
          <HelpTip k="recentRuns" className="ml-1" />
        </span>
      </div>
      <div className="flex flex-col">
        {runs.length === 0 && (
          <div className="flex flex-col items-center gap-1.5 px-3 py-6 text-ink-4">
            <Inbox size={18} strokeWidth={1.5} aria-hidden="true" />
            <span className="text-[11px]">No scenario runs in range</span>
          </div>
        )}
        {runs.map((r) => (
          <button
            key={r.run_id}
            type="button"
            onClick={() => onSelect?.(r.run_id)}
            disabled={!onSelect}
            className="flex items-center gap-3 px-3 py-2 border-b border-line-1 last:border-b-0 text-left hover:bg-surface-2 disabled:hover:bg-transparent disabled:cursor-default"
          >
            <span className="font-mono text-[10px] text-ink-4 tabular-nums w-32 shrink-0">
              {fmtDate(r.created_at)}
            </span>
            <span className="font-mono text-xs text-ink-2 truncate">
              {r.name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
