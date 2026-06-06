const BASE_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Dashboard ──────────────────────────────────────────────────────────────
export async function getDashboardSummary(symbol = "NG"): Promise<unknown> {
  return apiFetch(`/v1/dashboard/summary?symbol=${encodeURIComponent(symbol)}`);
}

// ── Backtest ───────────────────────────────────────────────────────────────
export async function getBacktestSummary(params: {
  symbol?: string;
  horizon?: string;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.horizon) q.set("horizon", params.horizon);
  return apiFetch(`/v1/backtest/summary?${q.toString()}`);
}

export interface ModelReliabilityBucket {
  confidence: string;
  claimed_prob: number;
  actual_rate: number | null;
  n: number;
}
export interface ModelCalibration {
  name: string;
  brier: number | null;
  hit_rate: number | null;
  n: number;
  buckets: ModelReliabilityBucket[];
  by_regime?: Record<
    string,
    { brier: number | null; hit_rate: number | null; n: number }
  >;
}
export interface ModelCalibrationResponse {
  models: ModelCalibration[];
  confidence_prob: Record<string, number>;
}

export async function getModelCalibration(params: {
  symbol?: string;
  horizon?: string;
  byRegime?: boolean;
}): Promise<ModelCalibrationResponse> {
  const q = new URLSearchParams();
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.horizon) q.set("horizon", params.horizon);
  if (params.byRegime) q.set("by_regime", "true");
  return apiFetch(`/v1/backtest/calibration?${q.toString()}`);
}

export async function runBacktest(params: {
  model: string;
  symbol?: string;
  from?: string;
  to?: string;
  horizon?: string;
  persist?: boolean;
}): Promise<unknown> {
  const q = new URLSearchParams();
  q.set("model", params.model);
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.horizon) q.set("horizon", params.horizon);
  if (params.persist !== undefined) q.set("persist", String(params.persist));
  return apiFetch(`/v1/backtest?${q.toString()}`);
}

// ── News ───────────────────────────────────────────────────────────────────
export async function getRecentNews(params: {
  symbol?: string;
  limit?: number;
  category?: string;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  if (params.category) q.set("category", params.category);
  return apiFetch(`/v1/news/recent?${q.toString()}`);
}

// ── Chart ──────────────────────────────────────────────────────────────────
export async function getChartBars(params: {
  contract_code?: string;
  resolution?: string;
  from?: string;
  to?: string;
  limit?: number;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params.contract_code) q.set("contract_code", params.contract_code);
  if (params.resolution) q.set("resolution", params.resolution);
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  return apiFetch(`/v1/chart/bars?${q.toString()}`);
}

export async function getChartCurve(
  symbol: string,
  asOf: string,
): Promise<unknown> {
  return apiFetch(
    `/v1/chart/curve?symbol=${encodeURIComponent(symbol)}&as_of=${encodeURIComponent(asOf)}`,
  );
}

export interface IndicatorPointDTO {
  t: string;
  v: number | null;
}

export interface IndicatorLineDTO {
  role: string;
  points: IndicatorPointDTO[];
}

export interface IndicatorSeriesDTO {
  type: string;
  params: Record<string, unknown>;
  /** "price" overlay or "sub" (own pane below price). */
  pane: string;
  lines: IndicatorLineDTO[];
}

export interface GetIndicatorsResponseDTO {
  symbol: string;
  indicators: IndicatorSeriesDTO[];
}

export async function getChartIndicators(params: {
  symbol: string;
  spec: string;
  from?: string;
  to?: string;
}): Promise<GetIndicatorsResponseDTO> {
  const q = new URLSearchParams();
  q.set("symbol", params.symbol);
  q.set("spec", params.spec);
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  return apiFetch<GetIndicatorsResponseDTO>(
    `/v1/chart/indicators?${q.toString()}`,
  );
}

// ── Signals ────────────────────────────────────────────────────────────────
export async function getCurrentSignal(symbol = "NG"): Promise<unknown> {
  return apiFetch(`/v1/signals/current?symbol=${encodeURIComponent(symbol)}`);
}

export async function getSignalHistory(params: {
  symbol?: string;
  limit?: number;
  status?: string;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  if (params.status) q.set("status", params.status);
  return apiFetch(`/v1/signals/history?${q.toString()}`);
}

// ── Scenarios ──────────────────────────────────────────────────────────────
export async function runScenario(body: {
  instrument?: string;
  name: string;
  shocks: Array<Record<string, unknown>>;
}): Promise<unknown> {
  return apiFetch("/v1/scenarios/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getScenarioRun(runId: string): Promise<unknown> {
  return apiFetch(`/v1/scenarios/runs/${encodeURIComponent(runId)}`);
}

export async function getScenarioTemplates(): Promise<unknown> {
  return apiFetch("/v1/scenarios/templates");
}

export async function getScenarioRuns(limit?: number): Promise<unknown> {
  const q = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch(`/v1/scenarios/runs${q}`);
}

// ── Journal ────────────────────────────────────────────────────────────────
export interface JournalEvidenceItem {
  source: string;
  summary: string;
  weight: number;
}

export type PredictionDirection = "bullish" | "bearish" | "neutral";

export interface PredictionClaim {
  direction: PredictionDirection;
  horizon_days: number;
  threshold_pct: number;
  rationale?: string;
}

export interface JournalCreateBody {
  instrument?: string;
  hypothesis: string;
  evidence?: JournalEvidenceItem[];
  confidence_pct: number;
  planned_action?: string | null;
  risk_factors?: string[];
  invalidation_criteria?: string | null;
  // Phase 2 — the confirmed machine-resolvable claim (optional).
  predicted_direction?: PredictionDirection;
  horizon_days?: number;
  threshold_pct?: number;
}

export async function extractPrediction(
  hypothesis: string,
  instrument = "NG",
): Promise<{ prediction: PredictionClaim; anchor_price: number | null }> {
  return apiFetch("/v1/journal/extract-prediction", {
    method: "POST",
    body: JSON.stringify({ instrument, hypothesis }),
  });
}

export async function createJournalEntry(
  body: JournalCreateBody,
): Promise<unknown> {
  return apiFetch("/v1/journal", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listJournalEntries(
  limit?: number,
  symbol?: string,
): Promise<unknown> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (symbol) params.set("symbol", symbol);
  const qs = params.toString();
  return apiFetch(`/v1/journal${qs ? `?${qs}` : ""}`);
}

export async function getJournalEntry(id: string): Promise<unknown> {
  return apiFetch(`/v1/journal/${encodeURIComponent(id)}`);
}

export async function patchJournalEntry(
  id: string,
  body: Partial<{
    outcome: string | null;
    reflection: string | null;
    resolved_direction: "hit" | "miss" | "neutral" | "unresolved" | null;
  }>,
): Promise<unknown> {
  return apiFetch(`/v1/journal/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Paper Trading ──────────────────────────────────────────────────────────
export interface OpenPaperTradeBody {
  instrument?: string;
  contract_code?: string;
  side: "long" | "short";
  size_contracts: number;
  entry_price: number;
  stop_loss?: number | null;
  take_profit?: number | null;
  rationale?: string | null;
  journal_ref?: string | null;
}

export async function openPaperTrade(
  body: OpenPaperTradeBody,
): Promise<unknown> {
  return apiFetch("/v1/paper-trades/open", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function closePaperTrade(
  id: string,
  body: { exit_price?: number; reflection?: string },
): Promise<unknown> {
  return apiFetch(`/v1/paper-trades/${encodeURIComponent(id)}/close`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listPaperTrades(params?: {
  status?: string;
  limit?: number;
  symbol?: string;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  if (params?.symbol) q.set("symbol", params.symbol);
  const qs = q.toString();
  return apiFetch(`/v1/paper-trades${qs ? `?${qs}` : ""}`);
}

export async function getPaperTrade(id: string): Promise<unknown> {
  return apiFetch(`/v1/paper-trades/${encodeURIComponent(id)}`);
}

export async function getPaperEquityCurve(since?: string): Promise<unknown> {
  const q = since ? `?since=${encodeURIComponent(since)}` : "";
  return apiFetch(`/v1/paper-trades/equity-curve${q}`);
}

// ── Admin ──────────────────────────────────────────────────────────────────
export async function getDataHealth(): Promise<unknown> {
  return apiFetch("/v1/admin/health");
}

export async function getAlerts(params?: {
  unread?: boolean;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params?.unread !== undefined) q.set("unread", String(params.unread));
  const qs = q.toString();
  return apiFetch(`/v1/admin/alerts${qs ? `?${qs}` : ""}`);
}

export async function acknowledgeAlert(id: string): Promise<unknown> {
  return apiFetch(`/v1/admin/alerts/${encodeURIComponent(id)}/acknowledge`, {
    method: "POST",
  });
}

// ── Thesis ─────────────────────────────────────────────────────────────────
export interface EvidenceEntry {
  factor: string;
  weight: number | null;
  note: string;
  source: string | null;
}

export interface Thesis {
  id: string;
  instrument_code: string;
  statement: string;
  supporting_evidence: EvidenceEntry[];
  contradicting_evidence: EvidenceEntry[];
  missing_data: string[];
  conviction_pct: number;
  created_at: string;
  updated_at: string;
  active: boolean;
}

export interface ThesisSeed {
  instrument_code: string;
  statement: string;
  supporting_evidence: EvidenceEntry[];
  contradicting_evidence: EvidenceEntry[];
  missing_data: string[];
  conviction_pct: number;
}

export interface ThesisCritique {
  missed_risks: string[];
  blind_spots: string[];
  questions: string[];
  safety: {
    confidence: "low" | "medium" | "high";
    caveats: string[];
    as_of: string;
    disclaimer: string;
  };
}

export interface ThesisDevilsAdvocate {
  counter_thesis: string;
  premortem: string[];
  invalidation_signals: string[];
  safety: {
    confidence: "low" | "medium" | "high";
    caveats: string[];
    as_of: string;
    disclaimer: string;
  };
}

export async function devilsAdvocateThesis(
  id: string,
): Promise<ThesisDevilsAdvocate> {
  return apiFetch<ThesisDevilsAdvocate>(
    `/v1/thesis/${encodeURIComponent(id)}/devils-advocate`,
    { method: "POST" },
  );
}

export interface ThesisCreateBody {
  instrument_code?: string;
  statement: string;
  supporting_evidence: EvidenceEntry[];
  contradicting_evidence: EvidenceEntry[];
  missing_data: string[];
  conviction_pct: number;
}

export interface ThesisPatchBody {
  statement?: string;
  supporting_evidence?: EvidenceEntry[];
  contradicting_evidence?: EvidenceEntry[];
  missing_data?: string[];
  conviction_pct?: number;
}

export async function getCurrentThesis(
  instrumentCode = "NG",
): Promise<Thesis | null> {
  const res = await fetch(
    `${BASE_URL}/v1/thesis/current?instrument_code=${encodeURIComponent(instrumentCode)}`,
    { headers: { "Content-Type": "application/json" } },
  );
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return (await res.json()) as Thesis;
}

export async function getThesisSeed(
  instrumentCode = "NG",
): Promise<ThesisSeed> {
  return apiFetch<ThesisSeed>(
    `/v1/thesis/seed?instrument_code=${encodeURIComponent(instrumentCode)}`,
  );
}

export async function createThesis(body: ThesisCreateBody): Promise<Thesis> {
  return apiFetch<Thesis>("/v1/thesis", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchThesis(
  id: string,
  body: ThesisPatchBody,
): Promise<Thesis> {
  return apiFetch<Thesis>(`/v1/thesis/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function critiqueThesis(id: string): Promise<ThesisCritique> {
  return apiFetch<ThesisCritique>(
    `/v1/thesis/${encodeURIComponent(id)}/critique`,
    { method: "POST" },
  );
}

// ── Ticker (dashboard chyron) ──────────────────────────────────────────────
export interface TickerItem {
  symbol: string;
  label: string;
  last_price: number | null;
  change_pct: number | null;
}

export async function getTickerQuotes(): Promise<{
  items: TickerItem[];
  cached: boolean;
}> {
  return apiFetch("/v1/ticker/quotes");
}

export interface NewsTickerItem {
  headline: string;
  url: string | null;
  published_at: string | null;
}

export async function getTickerNews(): Promise<{
  items: NewsTickerItem[];
  source: string;
  cached: boolean;
  stale?: boolean;
}> {
  return apiFetch("/v1/ticker/news");
}

// ── Instruments ────────────────────────────────────────────────────────────
export interface InstrumentQuote {
  last_price: number | null;
  change_abs: number | null;
  change_pct: number | null;
  front_month_code: string | null;
  as_of: string | null;
}

export interface InstrumentRow {
  symbol: string;
  name: string;
  asset_class: string;
  currency: string;
  unit: string;
  metadata: Record<string, unknown>;
  quote: InstrumentQuote;
}

export async function getInstruments(): Promise<{
  instruments: InstrumentRow[];
}> {
  return apiFetch("/v1/instruments");
}

// ── Signal Quality ─────────────────────────────────────────────────────────
export type SignalQualityGrade = "A+" | "A" | "B" | "C" | "D";

export interface SignalQualityResponse {
  symbol: string;
  grade: SignalQualityGrade;
  total_score: number;
  sub_scores: {
    input_diversity: number;
    model_agreement: number;
    regime_stability: number;
    time_to_decision: number;
  };
  sub_score_max: {
    input_diversity: number;
    model_agreement: number;
    regime_stability: number;
    time_to_decision: number;
  };
  detail: {
    input_diversity: string;
    model_agreement_total: number;
    model_agreement_max: number;
    regime_stability: string;
    distinct_regimes_14d: number;
    time_to_decision_bucket: string;
    minutes_since_freshness_adapter: number | null;
  };
}

export async function getSignalQuality(
  symbol = "NG",
): Promise<SignalQualityResponse> {
  return apiFetch<SignalQualityResponse>(
    `/v1/signal-quality?symbol=${encodeURIComponent(symbol)}`,
  );
}

// ── Calibration ────────────────────────────────────────────────────────────
export interface CalibrationBucket {
  label: string;
  lower_pct: number;
  upper_pct: number;
  claimed_mean: number | null;
  total_count: number;
  resolved_count: number;
  hit_count: number;
  hit_rate: number | null;
}

export interface CalibrationResponse {
  instrument_code: string;
  buckets: CalibrationBucket[];
  total_entries: number;
  resolved_entries: number;
  unresolved_entries: number;
  summary: string | null;
}

export async function getCalibration(
  instrumentCode = "NG",
  bucketCount = 5,
): Promise<CalibrationResponse> {
  return apiFetch<CalibrationResponse>(
    `/v1/calibration?instrument_code=${encodeURIComponent(instrumentCode)}` +
      `&bucket_count=${bucketCount}`,
  );
}

export interface DqCoachingBucket {
  label: string;
  effective_patterns: string[];
  failure_patterns: string[];
  recommendation: string;
}

export interface DqCoachingResponse {
  instrument_code: string;
  buckets: DqCoachingBucket[];
  overall: {
    synthesis: string;
    top_recommendation: string;
  };
  safety: {
    confidence: "low" | "medium" | "high";
    caveats: string[];
    as_of: string;
    disclaimer: string;
  };
}

export async function getDqCoaching(
  instrumentCode = "NG",
  bucketCount = 5,
): Promise<DqCoachingResponse> {
  return apiFetch<DqCoachingResponse>(
    `/v1/calibration/coaching?instrument_code=${encodeURIComponent(instrumentCode)}` +
      `&bucket_count=${bucketCount}`,
  );
}

// ── LLM / Explain ──────────────────────────────────────────────────────────
export async function explainMarket(
  ctx?: Record<string, unknown>,
): Promise<unknown> {
  return apiFetch("/v1/llm/explain-market", {
    method: "POST",
    body: JSON.stringify(ctx ?? {}),
  });
}

export async function explainSignal(body: {
  symbol?: string;
  signal_id?: string;
}): Promise<unknown> {
  return apiFetch("/v1/llm/explain-signal", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function explainScenario(runId: string): Promise<unknown> {
  return apiFetch(`/v1/llm/explain-scenario/${encodeURIComponent(runId)}`);
}

export async function explainJournal(entryId: string): Promise<unknown> {
  return apiFetch(`/v1/llm/explain-journal/${encodeURIComponent(entryId)}`);
}

// ── Fundamentals (Phase 18) ──────────────────────────────────────────────────
export type FundamentalsKind = "gas_storage" | "petroleum_stocks" | "none";

export interface FundamentalsLatest {
  as_of: string | null;
  level: number | null;
  net_change: number | null;
  surprise: number | null;
  five_year_avg: number | null;
}

export interface FundamentalsResponse {
  symbol: string;
  kind: FundamentalsKind;
  title: string;
  unit: string | null;
  latest: FundamentalsLatest | null;
  source: string | null;
  empty_reason: string | null;
}

export async function getFundamentals(
  symbol: string,
): Promise<FundamentalsResponse> {
  return apiFetch(`/v1/fundamentals?symbol=${encodeURIComponent(symbol)}`);
}

// ── Positioning (Phase 18) ───────────────────────────────────────────────────
export interface PositioningResponse {
  symbol: string;
  available: boolean;
  report_date: string | null;
  release_date: string | null;
  managed_money_net: number | null;
  managed_money_long: number | null;
  managed_money_short: number | null;
  mm_net_delta: number | null;
  open_interest_total: number | null;
  source: string | null;
}

export async function getPositioning(
  symbol: string,
): Promise<PositioningResponse> {
  return apiFetch(`/v1/positioning?symbol=${encodeURIComponent(symbol)}`);
}

// ── Candlestick patterns (Phase 21) ──────────────────────────────────────────
export type PatternDirection = "bullish" | "bearish" | "neutral";

export interface CandlestickPattern {
  ts: string;
  code: string;
  name: string;
  direction: PatternDirection;
  strength: number;
  meaning: string;
}

export interface PatternsResponse {
  contract_code: string;
  resolution: string;
  patterns: CandlestickPattern[];
  safety: {
    confidence: string;
    caveats: string[];
    as_of: string;
    disclaimer: string;
  };
}

export async function getChartPatterns(params: {
  contract_code: string;
  resolution: string;
  from: string;
  to: string;
}): Promise<PatternsResponse> {
  const q = new URLSearchParams({
    contract_code: params.contract_code,
    resolution: params.resolution,
    from: params.from,
    to: params.to,
  });
  return apiFetch(`/v1/chart/patterns?${q.toString()}`);
}

// ── Auto-TA: support/resistance + trendlines + chart patterns (Phase 24) ──────
export interface AutoTaPoint {
  ts: string;
  price: number;
}

export interface AutoTaLevel {
  price: number;
  kind: "support" | "resistance";
  touches: number;
}

export interface AutoTaTrendline {
  role: "support" | "resistance";
  p1: AutoTaPoint;
  p2: AutoTaPoint;
}

export interface AutoTaPattern {
  name: string;
  direction: PatternDirection;
  points: AutoTaPoint[];
  neckline?: number;
  confidence: number;
  description: string;
}

export interface AutoTaResponse {
  contract_code: string;
  resolution: string;
  levels: AutoTaLevel[];
  trendlines: AutoTaTrendline[];
  patterns: AutoTaPattern[];
  safety: {
    confidence: string;
    caveats: string[];
    as_of: string;
    disclaimer: string;
  };
}

export async function getChartAutoTa(params: {
  contract_code: string;
  resolution: string;
  from: string;
  to: string;
}): Promise<AutoTaResponse> {
  const q = new URLSearchParams({
    contract_code: params.contract_code,
    resolution: params.resolution,
    from: params.from,
    to: params.to,
  });
  return apiFetch(`/v1/chart/auto-ta?${q.toString()}`);
}

// ── Seasonality (Phase 25) ───────────────────────────────────────────────────
export interface SeasonalityPoint {
  md: string; // "MM-DD"
  v: number;
}

export interface SeasonalityYear {
  year: number;
  points: SeasonalityPoint[];
}

export interface SeasonalityResponse {
  contract_code: string;
  years: SeasonalityYear[];
  average: SeasonalityPoint[];
}

export async function getChartSeasonality(params: {
  contract_code: string;
  years?: number;
}): Promise<SeasonalityResponse> {
  const q = new URLSearchParams({ contract_code: params.contract_code });
  if (params.years) q.set("years", String(params.years));
  return apiFetch(`/v1/chart/seasonality?${q.toString()}`);
}
