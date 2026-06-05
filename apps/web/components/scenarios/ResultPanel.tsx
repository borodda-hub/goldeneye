import type { ScenarioResult } from "@/app/(app)/scenarios/types";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { DirectionChip } from "@/components/DirectionChip";
import { HelpTip } from "@/components/HelpTip";
import { SafetyEnvelopeNote } from "@/components/SafetyEnvelopeNote";

interface Props {
  result: ScenarioResult;
  name: string;
  /** Persisted run_id — required to enable PDF export. */
  runId?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function pdfDownloadUrl(runId: string): string {
  return `${API_BASE}/v1/scenarios/runs/${encodeURIComponent(runId)}/export.pdf`;
}

function NumberedList({
  items,
  empty,
}: {
  items: string[];
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs text-ink-4 italic">{empty}</p>;
  }
  return (
    <ol className="space-y-1.5">
      {items.map((item, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: static render-only list, no stable id
        <li key={i} className="text-xs text-ink-3 leading-relaxed flex gap-2">
          <span className="font-mono text-ink-4 tabular-nums">{i + 1}.</span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  );
}

export function ResultPanel({ result, name, runId }: Props) {
  return (
    <div className="border border-line-1 bg-surface-1 p-4 flex flex-col gap-4">
      {/* Header: name + direction + confidence + timeframe + export */}
      <div className="flex items-start gap-6 flex-wrap">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Result
            <HelpTip k="scenarioResult" className="ml-1" />
          </span>
          <span className="font-mono text-sm text-ink-2 truncate">{name}</span>
        </div>

        <div className="flex items-center gap-3">
          <DirectionChip direction={result.directional_pressure} />
          <ConfidenceBar confidence={result.confidence} />
        </div>

        <div className="flex flex-col gap-1">
          <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Timeframe
          </span>
          <span className="font-mono text-xs text-ink-2">
            {result.affected_timeframe}
          </span>
        </div>

        <div className="flex flex-col gap-1 ml-auto">
          <span className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Expected range
          </span>
          <span className="font-mono tabular-nums text-xs text-ink-2">
            {(result.expected_pct_range.low * 100).toFixed(2)}% –{" "}
            {(result.expected_pct_range.high * 100).toFixed(2)}%
          </span>
        </div>

        {runId ? (
          <a
            href={pdfDownloadUrl(runId)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] uppercase tracking-widest border border-line-1 px-2 py-1 text-ink-2 hover:bg-surface-2 hover:text-ink-1 self-start"
            data-testid="export-pdf-link"
            aria-label="Export this scenario as a PDF report"
          >
            ↓ Export PDF
          </a>
        ) : null}
      </div>

      {/* Three columns: assumptions, counterarguments, data needed */}
      <div className="grid grid-cols-3 gap-6 border-t border-line-1 pt-4">
        <div className="flex flex-col gap-2">
          <h3 className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Assumptions
            <HelpTip k="assumptions" className="ml-1" />
          </h3>
          <NumberedList items={result.assumptions} empty="No assumptions." />
        </div>
        <div className="flex flex-col gap-2">
          <h3 className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Counterarguments
            <HelpTip k="counterarguments" className="ml-1" />
          </h3>
          <NumberedList
            items={result.counterarguments}
            empty="No counterarguments."
          />
        </div>
        <div className="flex flex-col gap-2">
          <h3 className="font-mono text-[10px] text-accent uppercase tracking-widest">
            Data needed to validate
            <HelpTip k="dataNeeded" className="ml-1" />
          </h3>
          <NumberedList
            items={result.data_needed_to_validate}
            empty="No validation signals listed."
          />
        </div>
      </div>

      {/* Narrative */}
      <div className="flex flex-col gap-2 border-t border-line-1 pt-4">
        <h3 className="font-mono text-[10px] text-accent uppercase tracking-widest">
          Narrative
        </h3>
        {result.narrative ? (
          <p className="text-sm text-ink-2 leading-relaxed whitespace-pre-wrap">
            {result.narrative}
          </p>
        ) : (
          <p className="text-sm text-ink-4 italic">
            Narrative unavailable — see structural fields above.
          </p>
        )}
      </div>

      {/* Safety envelope */}
      <SafetyEnvelopeNote envelope={result.safety} defaultOpen={true} />
    </div>
  );
}
