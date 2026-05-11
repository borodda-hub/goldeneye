"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getAlerts,
  getChartBars,
  getChartCurve,
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
  chartBars: (
    contractCode: string,
    resolution: string,
    from: string,
    to: string,
  ) => ["chart", "bars", contractCode, resolution, from, to],
  chartCurve: (symbol: string, asOf: string) => ["chart", "curve", symbol, asOf],
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

export function useChartBars(
  contractCode: string,
  resolution: string,
  from: string,
  to: string,
) {
  return useQuery({
    queryKey: queryKeys.chartBars(contractCode, resolution, from, to),
    queryFn: () => getChartBars({ contract_code: contractCode, resolution, from, to }),
    staleTime: resolution === "1m" ? 0 : 60_000,
  });
}

export function useChartCurve(symbol: string, asOf: string) {
  return useQuery({
    queryKey: queryKeys.chartCurve(symbol, asOf),
    queryFn: () => getChartCurve(symbol, asOf),
    staleTime: 300_000,
  });
}
