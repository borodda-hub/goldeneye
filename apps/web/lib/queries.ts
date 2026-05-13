"use client";

import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAlerts,
  getBacktestSummary,
  getChartBars,
  getChartCurve,
  getCurrentSignal,
  getDashboardSummary,
  getDataHealth,
  getJournalEntry,
  getPaperEquityCurve,
  getRecentNews,
  getScenarioRuns,
  getScenarioTemplates,
  getSignalHistory,
  listJournalEntries,
  listPaperTrades,
  runBacktest,
} from "./api";

export const queryKeys = {
  dashboard: (symbol: string) => ["dashboard", symbol],
  signal: (symbol: string) => ["signal", symbol],
  scenarioTemplates: () => ["scenario", "templates"],
  scenarioRuns: () => ["scenario", "runs"],
  journalEntries: () => ["journal", "entries"],
  journalEntry: (id: string) => ["journal", "entry", id],
  paperTrades: (status?: string) => ["paper", status],
  paperEquityCurve: (since?: string) => ["paper", "equity-curve", since ?? ""],
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

export function useJournalEntry(id: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.journalEntry(id ?? ""),
    queryFn: () => getJournalEntry(id as string),
    enabled: Boolean(id),
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

export function usePaperEquityCurve(since?: string) {
  return useQuery({
    queryKey: queryKeys.paperEquityCurve(since),
    queryFn: () => getPaperEquityCurve(since),
    staleTime: 60_000,
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

export function useScenarioRuns(limit = 20) {
  return useQuery({
    queryKey: ["scenario", "runs", limit],
    queryFn: () => getScenarioRuns(limit),
    staleTime: 30_000,
  });
}

export function useSignalHistory(symbol = "NG", limit = 25, status = "scored") {
  return useQuery({
    queryKey: ["signal", "history", symbol, limit, status],
    queryFn: () => getSignalHistory({ symbol, limit, status }),
    staleTime: 30_000,
  });
}

export function useChartCurve(symbol: string, asOf: string) {
  return useQuery({
    queryKey: queryKeys.chartCurve(symbol, asOf),
    queryFn: () => getChartCurve(symbol, asOf),
    staleTime: 300_000,
  });
}

export function useRecentNews(symbol = "NG", limit = 15) {
  return useQuery({
    queryKey: ["news", "recent", symbol, limit],
    queryFn: () => getRecentNews({ symbol, limit }),
    // RSS sources update every few hours at most; 5 min staleTime is plenty
    // and the backend caches for 10 min anyway.
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useBacktestSummary(symbol = "NG", horizon = "1d") {
  return useQuery({
    queryKey: ["backtest", "summary", symbol, horizon],
    queryFn: () => getBacktestSummary({ symbol, horizon }),
    // Aggregate is cheap; refresh every minute so re-runs reflect quickly.
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useRunBacktest(symbol = "NG", horizon = "1d") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (model: string) =>
      runBacktest({ model, symbol, horizon, persist: true }),
    onSuccess: () => {
      // Refresh the summary card + the Signal Lab history table — both
      // read from model_forecasts and will reflect the new persisted rows.
      qc.invalidateQueries({ queryKey: ["backtest", "summary", symbol, horizon] });
      qc.invalidateQueries({ queryKey: ["signal", "history"] });
    },
  });
}
