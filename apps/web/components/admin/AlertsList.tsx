"use client";

import type { Alert } from "@/app/(app)/admin/types";
import { acknowledgeAlert } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface Props {
  alerts: Alert[];
}

function severityColor(severity: string): string {
  switch (severity) {
    case "critical":
    case "error":
      return "text-down";
    case "warning":
      return "text-conf-medium";
    default:
      return "text-ink-3";
  }
}

function fmtTime(iso: string): string {
  return iso.replace("T", " ").replace("Z", "").slice(0, 16);
}

export function AlertsList({ alerts }: Props) {
  const queryClient = useQueryClient();
  const ack = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "alerts"] });
    },
  });

  return (
    <div className="border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Alerts
        </span>
      </div>
      {alerts.length === 0 ? (
        <p className="text-xs text-ink-4 font-mono p-3">No active alerts.</p>
      ) : (
        <ul>
          {alerts.map((a) => (
            <li
              key={a.id}
              className="flex items-center gap-3 px-3 py-2 border-b border-line-1 last:border-b-0"
            >
              <span
                className={`font-mono text-[10px] uppercase tracking-widest w-16 ${severityColor(a.severity)}`}
              >
                {a.severity}
              </span>
              <span className="font-mono text-xs text-ink-2 flex-1 truncate">
                {a.kind}
              </span>
              <span className="font-mono text-[10px] text-ink-4 tabular-nums">
                {fmtTime(a.created_at)}
              </span>
              {!a.acknowledged && (
                <button
                  type="button"
                  onClick={() => ack.mutate(a.id)}
                  disabled={ack.isPending}
                  className="font-mono text-[10px] text-accent uppercase tracking-widest disabled:text-ink-4"
                >
                  Ack
                </button>
              )}
              {a.acknowledged && (
                <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
                  acked
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
