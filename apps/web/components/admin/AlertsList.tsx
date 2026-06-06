"use client";

import type { Alert } from "@/app/(app)/admin/types";
import { acknowledgeAlert } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCircle2 } from "lucide-react";

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
    <div className="card-interactive border border-line-1 bg-surface-1">
      <div className="px-3 py-2 border-b border-line-1 flex items-center gap-2">
        <BellRing
          size={12}
          strokeWidth={1.5}
          aria-hidden="true"
          className="text-ink-4"
        />
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Alerts
        </span>
      </div>
      {alerts.length === 0 ? (
        <div className="flex flex-col items-center gap-1.5 py-6 text-ink-4">
          <CheckCircle2 size={18} strokeWidth={1.5} aria-hidden="true" />
          <span className="text-[11px]">No active alerts</span>
        </div>
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
