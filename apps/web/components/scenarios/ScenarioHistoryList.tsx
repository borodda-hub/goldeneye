import type { RecentRun } from "@/app/(app)/scenarios/types";
import { HelpTip } from "@/components/HelpTip";

interface Props {
  runs: RecentRun[];
  onSelect?: (runId: string) => void;
}

function fmtDate(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function ScenarioHistoryList({ runs, onSelect }: Props) {
  return (
    <div className="border border-line-1 bg-surface-1 flex flex-col">
      <div className="px-3 py-2 border-b border-line-1">
        <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
          Recent Runs
          <HelpTip k="recentRuns" className="ml-1" />
        </span>
      </div>
      <div className="flex flex-col">
        {runs.length === 0 && (
          <p className="text-xs text-ink-4 px-3 py-4 text-center">
            No scenario runs in range.
          </p>
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
