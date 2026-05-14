"use client";

import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  type ThesisCreateBody,
  type ThesisPatchBody,
  createThesis,
  critiqueThesis,
  getAlerts,
  getBacktestSummary,
  getCalibration,
  getChartBars,
  getChartCurve,
  getChartIndicators,
  getCurrentSignal,
  getCurrentThesis,
  getDashboardSummary,
  getDataHealth,
  getDqCoaching,
  getInstruments,
  getJournalEntry,
  getPaperEquityCurve,
  getRecentNews,
  getScenarioRuns,
  getScenarioTemplates,
  getSignalHistory,
  getSignalQuality,
  getThesisSeed,
  getTickerQuotes,
  listJournalEntries,
  listPaperTrades,
  patchJournalEntry,
  patchThesis,
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
  chartCurve: (symbol: string, asOf: string) => [
    "chart",
    "curve",
    symbol,
    asOf,
  ],
  thesisCurrent: (instrument: string) => ["thesis", "current", instrument],
  thesisSeed: (instrument: string) => ["thesis", "seed", instrument],
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

export function useJournalEntries(limit?: number, symbol?: string) {
  return useQuery({
    queryKey: [...queryKeys.journalEntries(), symbol ?? "all"],
    queryFn: () => listJournalEntries(limit, symbol),
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

export function usePaperTrades(status?: string, symbol?: string) {
  return useQuery({
    queryKey: [...queryKeys.paperTrades(status), symbol ?? "all"],
    queryFn: () =>
      listPaperTrades(status || symbol ? { status, symbol } : undefined),
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
    queryFn: () =>
      getChartBars({ contract_code: contractCode, resolution, from, to }),
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

export function useChartIndicators(symbol: string, specQuery: string) {
  return useQuery({
    queryKey: ["chart", "indicators", symbol, specQuery],
    queryFn: () => getChartIndicators({ symbol, spec: specQuery }),
    // Disabled when no specs are active so we never hit the API with an
    // empty `spec=` (which would 422).
    enabled: Boolean(specQuery),
    // Backend Redis TTL is 5 min; match it on the client so a chart that
    // sits open doesn't keep re-fetching.
    staleTime: 5 * 60_000,
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
      qc.invalidateQueries({
        queryKey: ["backtest", "summary", symbol, horizon],
      });
      qc.invalidateQueries({ queryKey: ["signal", "history"] });
    },
  });
}

// ── Thesis ────────────────────────────────────────────────────────────────

export function useCurrentThesis(instrumentCode = "NG") {
  return useQuery({
    queryKey: queryKeys.thesisCurrent(instrumentCode),
    queryFn: () => getCurrentThesis(instrumentCode),
    staleTime: 30_000,
  });
}

export function useThesisSeed(instrumentCode = "NG", enabled = false) {
  return useQuery({
    queryKey: queryKeys.thesisSeed(instrumentCode),
    queryFn: () => getThesisSeed(instrumentCode),
    staleTime: 60_000,
    enabled,
  });
}

export function useCreateThesis(instrumentCode = "NG") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ThesisCreateBody) => createThesis(body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.thesisCurrent(instrumentCode),
      });
    },
  });
}

export function usePatchThesis(instrumentCode = "NG") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ThesisPatchBody }) =>
      patchThesis(id, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.thesisCurrent(instrumentCode),
      });
    },
  });
}

export function useCritiqueThesis() {
  return useMutation({
    mutationFn: (id: string) => critiqueThesis(id),
  });
}

// ── Signal Quality + Calibration (Phase 13) ───────────────────────────────

export function useSignalQuality(symbol = "NG") {
  return useQuery({
    queryKey: ["signal-quality", symbol],
    queryFn: () => getSignalQuality(symbol),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useCalibration(instrumentCode = "NG", bucketCount = 5) {
  return useQuery({
    queryKey: ["calibration", instrumentCode, bucketCount],
    queryFn: () => getCalibration(instrumentCode, bucketCount),
    staleTime: 30_000,
  });
}

export function useInstruments() {
  return useQuery({
    queryKey: ["instruments"],
    queryFn: () => getInstruments(),
    // Quotes change with each minute but the list barely moves. 30s lets the
    // sidebar prices update without thrashing the cache.
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useTickerQuotes() {
  return useQuery({
    queryKey: ["ticker", "quotes"],
    queryFn: () => getTickerQuotes(),
    // Backend caches Yahoo for 5 min — the chyron is decorative, not a
    // trading feed, so 5 min between client refetches is plenty.
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useDqCoaching(instrumentCode = "NG", bucketCount = 5) {
  return useQuery({
    queryKey: ["calibration", "coaching", instrumentCode, bucketCount],
    queryFn: () => getDqCoaching(instrumentCode, bucketCount),
    // Coaching is an LLM call — keep it fresh for 10 minutes to avoid
    // bouncing it on every dashboard re-mount.
    staleTime: 10 * 60_000,
    // Don't auto-refetch on focus/interval — manual re-run only.
    refetchOnWindowFocus: false,
  });
}

export function usePatchJournalEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: Parameters<typeof patchJournalEntry>[1];
    }) => patchJournalEntry(id, body),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.journalEntry(vars.id) });
      qc.invalidateQueries({ queryKey: queryKeys.journalEntries() });
      // Updating a resolution shifts a bucket in the calibration page,
      // so invalidate that too.
      qc.invalidateQueries({ queryKey: ["calibration"] });
    },
  });
}
