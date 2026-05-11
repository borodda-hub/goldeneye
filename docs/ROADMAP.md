# docs/ROADMAP.md — Next-Stage Roadmap

What the MVP deliberately doesn't do, and the path to take each piece from prototype to production. Nothing on this list is in scope for the demo build; if it were, it would be in `docs/PHASE_*.md` instead.

## 1. Real CFTC, EIA, and NWS adapters

Today's adapters in `apps/api/adapters/{energy,positioning,weather}/` return fixtures from `packages/fixtures/`. The adapter Protocols in `apps/api/adapters/base.py` already define the contract — real adapters are drop-in replacements selected at startup via `ADAPTER_*` env vars.

- **EIA (Weekly Natural Gas Storage):** swap `EnergyMockAdapter` for `EiaApiAdapter`. The EIA Open Data API returns the weekly storage report under series ID `NG.NW2_EPG0_SWO_R48_BCF.W`. Auth is a free API key passed as a query param. Cache responses for the full week.
- **CFTC (COT report):** swap `PositioningMockAdapter` for `CftcCsvAdapter`. CFTC publishes Disaggregated COT as a CSV; pull the latest week, filter to NG futures, extract managed-money net.
- **NWS:** swap `WeatherMockAdapter` for `NwsApiAdapter`. The NWS gridded forecast API is free, no key, returns by lat/lon — pre-load region-to-grid mappings for major gas demand centers (Northeast, Midwest, Southeast, etc.).

**Why it matters:** Every Phase-05 ensemble that says "input_diversity: high" is actually claiming alt-data influence; right now that influence is synthetic. Real adapters make the ensemble's confidence rationale honest.

## 2. TradingView UDF datafeed for chart embedding

Replace the Lightweight Charts implementation in `apps/web/components/chart/PriceChart.tsx` with the full TradingView Advanced Chart widget pointed at a custom UDF datafeed. The UDF endpoints (`/symbols`, `/resolve_symbol`, `/history`, `/symbol_info`, `/marks`) are documented in TradingView's "Connecting Your Data" guide and slot in as new FastAPI routes that wrap our existing `chart/bars` endpoint.

**Why it matters:** Lightweight Charts is fine for the demo but TradingView's widget gives drawing tools, indicators, multi-timeframe analysis, and a UI that users already know. It's the single highest-leverage UX improvement for analysts.

## 3. Databento or CME-licensed tick feed

Replace the synthetic WebSocket tick generator in `apps/api/workers/tick_simulator.py` with a real exchange tick subscription. Databento offers historical and real-time CME data including NG futures with reasonable per-symbol pricing; alternatively, direct CME GovBox / CME Connect feeds for licensed users.

**Why it matters:** Mark-to-market on Paper Trading currently runs against synthetic ticks. A real feed makes paper trading a usable practice tool and unlocks intraday model evaluation. Also opens the door to bar resolutions finer than 1m.

## 4. Backtest engine

A new `apps/api/services/backtest.py` that replays a model registry against historical bars. Input: model name + symbol + date range + retrain cadence. Output: per-forecast `realized_pct`, hit rate by horizon, distribution of `delta_from_expected_pct`, Sharpe-equivalent.

**Why it matters:** The Signal Lab's history table shows realized outcomes prospectively. A backtest gives you the same scoring retroactively, so you can compare model variants without waiting weeks. Currently the only way to assess model quality is sit and watch.

## 5. Real ML training pipeline

Replace `xgboost_placeholder.py` with a trained model. Stack: feature store on top of TimescaleDB (continuous aggregates for rolling features), training jobs in `apps/api/training/` triggered weekly by a worker, models versioned in MLflow or a simple disk-backed registry, the registry-loaded model used in `model_registry.py` instead of the placeholder.

Features to start: rolling vol, storage-vs-consensus delta, COT managed-money net WoW change, weather HDD-weighted anomaly, calendar features (DOW, month, days-to-expiry).

**Why it matters:** The current placeholder is honest about being a placeholder. A real model — even a modest one — turns the ensemble from a demo into something where the input diversity claim has teeth.

## 6. Multi-tenant auth and orgs

Add a user system. Stack: Clerk or Auth.js for the frontend, propagate JWTs to FastAPI, partition data by `user_id` (already in the schema, currently always NULL). Add an org concept layered on top so multiple users can share a paper-trading book. Build a simple admin role for the data-health screen.

**Why it matters:** The demo is single-user. Any real deployment hosting more than the builder needs proper isolation. The schema is ready; the wiring is not.

## 7. Production observability (OpenTelemetry, metrics, alerting)

OTel instrumentation in the FastAPI app and the worker, exported to a managed collector (Honeycomb, Grafana Cloud, or Datadog). Key spans: per-route latency, LLM call duration and cache hit rate, adapter run duration. Metrics for safety-violation count (should be zero), forbidden-phrase scan rate, model agreement distribution. Alert rules on adapter `down` status persisting >2 cadences, on safety-violation count > 0.

**Why it matters:** The Admin screen surfaces data health to a human looking at the UI. OTel surfaces it to a pager. Both are needed; right now we only have the first.

## 8. Mobile responsive pass

The current layout assumes 1280×800 (Bloomberg/Palantir terminal mindset). Mobile is hostile to all of it — multi-column grids, tabular numbers, fixed sidebar. A mobile pass would single-column the dashboard, hide the side nav behind a drawer, switch chart libraries to one that handles touch (Recharts handles mobile reasonably; Lightweight Charts has touch support but the chart-view layout doesn't).

**Why it matters:** Analysts use phones for monitoring even if they don't use them for analysis. A simple monitoring-only mobile view (price, vol regime, latest signal, latest journal entry) covers 80% of the away-from-desk use case.

## 9. Hardening for non-NG instruments

The whole stack is parameterized by symbol but only `NG` is seeded. Adding WTI crude, electricity (PJM West Hub day-ahead), or currency futures (DX) means:
- New instruments + contract rows in `instruments.json`
- New fixtures (or real adapters) for each domain
- Instrument-specific tick values in `paper_engine.py` (currently hardcoded $10,000/contract for NG)
- Re-tune the vol regime thresholds per instrument
- Re-train (or re-stub) the xgboost model per instrument

**Why it matters:** The product framing is "commodities desk" not "natural gas desk." Single-instrument is the right MVP scope, but the moment a real user lands they ask "where's oil?"
