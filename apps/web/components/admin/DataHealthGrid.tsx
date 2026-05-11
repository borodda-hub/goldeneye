import type { AdapterRollup } from "@/app/(app)/admin/types";

interface Props {
  adapters: AdapterRollup[];
}

function StatusPill({ status }: { status: AdapterRollup["status"] }) {
  const color =
    status === "ok"
      ? "text-up bg-up-soft"
      : status === "degraded"
        ? "text-conf-medium bg-surface-2"
        : "text-down bg-down-soft";
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-sm ${color}`}
    >
      {status}
    </span>
  );
}

function fmtLag(min: number | null): string {
  if (min === null) return "—";
  if (min < 60) return `${min.toFixed(0)}m`;
  if (min < 60 * 24) return `${(min / 60).toFixed(1)}h`;
  return `${(min / (60 * 24)).toFixed(1)}d`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function DataHealthGrid({ adapters }: Props) {
  if (adapters.length === 0) {
    return (
      <div className="text-xs text-ink-4 font-mono border border-line-1 p-3">
        No adapter runs recorded yet.
      </div>
    );
  }

  return (
    <div className="border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Adapter Health
        </span>
      </div>
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-line-1 text-ink-3 text-[10px] uppercase tracking-widest">
            <th className="text-left px-3 py-1.5">Adapter</th>
            <th className="text-left px-3 py-1.5">Status</th>
            <th className="text-left px-3 py-1.5">Last Success</th>
            <th className="text-right px-3 py-1.5">Lag</th>
            <th className="text-right px-3 py-1.5">Cadence</th>
            <th className="text-right px-3 py-1.5">Rows</th>
          </tr>
        </thead>
        <tbody>
          {adapters.map((a) => (
            <tr key={a.name} className="border-b border-line-1 last:border-b-0">
              <td className="px-3 py-1.5 text-ink-2">{a.name}</td>
              <td className="px-3 py-1.5">
                <StatusPill status={a.status} />
              </td>
              <td className="px-3 py-1.5 tabular-nums text-ink-3">
                {fmtTime(a.last_success)}
              </td>
              <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                {fmtLag(a.lag_minutes)}
              </td>
              <td className="px-3 py-1.5 tabular-nums text-right text-ink-4">
                {fmtLag(a.expected_cadence_minutes)}
              </td>
              <td className="px-3 py-1.5 tabular-nums text-right text-ink-3">
                {a.rows_ingested ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
