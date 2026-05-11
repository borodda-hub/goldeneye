"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getAlerts,
  getCurrentSignal,
  getDashboardSummary,
  getDataHealth,
  getScenarioTemplates,
  listJournalEntries,
  listPaperTrades,
} from "./api";

export const queryKeys = {
  dashboard: (symbol: string) => ["dashboard", symbol],
  signal: (symbol: string) => ["signal", symbol],
  scenarioTemplates: () => ["scenario", "templates"],
  scenarioRuns: () => ["scenario", "runs"],
  journalEntries: () => ["journal", "entries"],
  paperTrades: (status?: string) => ["paper", status],
  dataHealth: () => ["admin", "health"],
  alerts: (unread: boolean) => ["admin", "alerts", unread],
} as const;

export function useDashboardSummary(symbol = "NG") {
  return useQuery({
    queryKey: queryKeys.dashboard(symbol),
    queryFn: () => getDashboardSummary(symbol),
    staleTime: 5_000,
  });
}

export function useCurrentSignal(symbol = "NG") {
  return useQuery({
    queryKey: queryKeys.signal(symbol),
    queryFn: () => getCurrentSignal(symbol),
    staleTime: 30_000,
  });
}

export function useScenarioTemplates() {
  return useQuery({
    queryKey: queryKeys.scenarioTemplates(),
    queryFn: () => getScenarioTemplates(),
    staleTime: 30_000,
  });
}

export function useJournalEntries(limit?: number) {
  return useQuery({
    queryKey: queryKeys.journalEntries(),
    queryFn: () => listJournalEntries(limit),
    staleTime: 30_000,
  });
}

export function usePaperTrades(status?: string) {
  return useQuery({
    queryKey: queryKeys.paperTrades(status),
    queryFn: () => listPaperTrades(status ? { status } : undefined),
    staleTime: 30_000,
  });
}

export function useDataHealth() {
  return useQuery({
    queryKey: queryKeys.dataHealth(),
    queryFn: () => getDataHealth(),
    staleTime: 30_000,
  });
}

export function useAlerts(unread = false) {
  return useQuery({
    queryKey: queryKeys.alerts(unread),
    queryFn: () => getAlerts({ unread }),
    staleTime: 30_000,
  });
}
