"use client";

import { PageHeader } from "@/components/PageHeader";
import { AlertsList } from "@/components/admin/AlertsList";
import { DataHealthGrid } from "@/components/admin/DataHealthGrid";
import { EnvironmentBlock } from "@/components/admin/EnvironmentBlock";
import { ModelHealthGrid } from "@/components/admin/ModelHealthGrid";
import { getAlerts, getDataHealth } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Server } from "lucide-react";
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
    <div className="stagger flex flex-col gap-4">
      <PageHeader icon={Server} title="Admin" subtitle="Data & model health" />

      <DataHealthGrid adapters={health?.adapters ?? []} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
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
