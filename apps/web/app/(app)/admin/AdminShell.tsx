"use client";

import { useQuery } from "@tanstack/react-query";
import { getAlerts, getDataHealth } from "@/lib/api";
import { DataHealthGrid } from "@/components/admin/DataHealthGrid";
import { ModelHealthGrid } from "@/components/admin/ModelHealthGrid";
import { AlertsList } from "@/components/admin/AlertsList";
import { EnvironmentBlock } from "@/components/admin/EnvironmentBlock";
import type { AlertsResponse, DataHealth } from "./types";

interface Props {
  initialHealth: DataHealth | null;
  initialAlerts: AlertsResponse | null;
  envFlags: Record<string, boolean>;
  gitSha?: string;
  buildTime?: string;
}

export function AdminShell({
  initialHealth,
  initialAlerts,
  envFlags,
  gitSha,
  buildTime,
}: Props) {
  const { data: healthData } = useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => getDataHealth(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  const { data: alertsData } = useQuery({
    queryKey: ["admin", "alerts", false],
    queryFn: () => getAlerts({ unread: false }),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const health = (healthData as DataHealth | undefined) ?? initialHealth;
  const alerts = (alertsData as AlertsResponse | undefined) ?? initialAlerts;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-ink-1">Admin</h1>
        <span className="font-mono text-[10px] text-ink-4 uppercase tracking-widest">
          Data health · alerts · environment
        </span>
      </div>

      <DataHealthGrid adapters={health?.adapters ?? []} />
      <div className="grid grid-cols-2 gap-4">
        <ModelHealthGrid models={health?.models ?? []} />
        <EnvironmentBlock
          gitSha={gitSha}
          buildTime={buildTime}
          envFlags={envFlags}
        />
      </div>
      <AlertsList alerts={alerts?.alerts ?? []} />
    </div>
  );
}
