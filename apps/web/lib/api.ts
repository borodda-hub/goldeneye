const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
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

// ── Signals ────────────────────────────────────────────────────────────────
export async function getCurrentSignal(symbol = "NG"): Promise<unknown> {
  return apiFetch(`/v1/signals/current?symbol=${encodeURIComponent(symbol)}`);
}

export async function getSignalHistory(params: {
  symbol?: string;
  limit?: number;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params.symbol) q.set("symbol", params.symbol);
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  return apiFetch(`/v1/signals/history?${q.toString()}`);
}

// ── Scenarios ──────────────────────────────────────────────────────────────
export async function runScenario(body: {
  template_id?: string;
  symbol?: string;
  parameters?: Record<string, unknown>;
}): Promise<unknown> {
  return apiFetch("/v1/scenarios/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getScenarioTemplates(): Promise<unknown> {
  return apiFetch("/v1/scenarios/templates");
}

export async function getScenarioRuns(limit?: number): Promise<unknown> {
  const q = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch(`/v1/scenarios/runs${q}`);
}

// ── Journal ────────────────────────────────────────────────────────────────
export async function createJournalEntry(body: {
  title: string;
  content: string;
  tags?: string[];
  symbol?: string;
}): Promise<unknown> {
  return apiFetch("/v1/journal", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listJournalEntries(limit?: number): Promise<unknown> {
  const q = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch(`/v1/journal${q}`);
}

export async function getJournalEntry(id: string): Promise<unknown> {
  return apiFetch(`/v1/journal/${encodeURIComponent(id)}`);
}

export async function patchJournalEntry(
  id: string,
  body: Partial<{ title: string; content: string; tags: string[] }>,
): Promise<unknown> {
  return apiFetch(`/v1/journal/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Paper Trading ──────────────────────────────────────────────────────────
export async function openPaperTrade(body: {
  symbol: string;
  direction: "long" | "short";
  quantity: number;
  entry_price: number;
  notes?: string;
}): Promise<unknown> {
  return apiFetch("/v1/paper/trades", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function closePaperTrade(
  id: string,
  body: { exit_price: number; notes?: string },
): Promise<unknown> {
  return apiFetch(`/v1/paper/trades/${encodeURIComponent(id)}/close`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listPaperTrades(params?: {
  status?: string;
  limit?: number;
}): Promise<unknown> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch(`/v1/paper/trades${qs ? `?${qs}` : ""}`);
}

export async function getPaperTrade(id: string): Promise<unknown> {
  return apiFetch(`/v1/paper/trades/${encodeURIComponent(id)}`);
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
