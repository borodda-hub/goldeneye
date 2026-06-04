# docs/DATA_SOURCES.md — Real Data Source Reference

This file exists so Claude Code does not have to re-research these every time we add a real adapter. All adapters in MVP ship with a mock implementation; this is the cheat-sheet for the eventual real swap.

> **Adapter pattern.** Every adapter implements a `Protocol` from `apps/api/adapters/base.py`. Mock and real implementations are siblings — `MockEIAAdapter` and `EIAAdapter` both implement `EnergyDataAdapter`. Selection at startup via env var `ADAPTER_<NAME>=mock|real`. When the real adapter's API key is missing, it logs a warning and falls back to mock.

## §eia — U.S. Energy Information Administration

- **API:** EIA APIv2, base `https://api.eia.gov/v2/`
- **Auth:** free API key, query string param `api_key=...` or header. Register at https://www.eia.gov/opendata/.
- **Pattern:** RESTful with hierarchical routes. `GET /v2/<route>/<sub-route>/data/?api_key=...&frequency=...&data[0]=value&facets[seriesId][]=...`
- **Documentation:** https://www.eia.gov/opendata/documentation/APIv2.0.1.pdf (and the live query browser at the same site).
- **Natural gas routes (the ones we care about):**
  - `natural-gas/stor/wkly/data/` — weekly working gas in storage (the EIA storage report we ingest weekly)
  - `natural-gas/pri/fut/data/` — natural gas futures prices (e.g., series `RNGC1` is front-month daily)
  - `natural-gas/prod/sum/data/` — production summary
  - `natural-gas/cons/sum/data/` — consumption summary
  - `natural-gas/move/expc/data/` — exports
  - `natural-gas/move/impc/data/` — imports
- **Petroleum product weekly stocks (Phase 17 — HO/RB/CL alt-data):** all ride the
  `petroleum/stoc/wstk/data/` route via `adapters/energy/eia_petroleum.py`'s
  per-symbol `PETROLEUM_SERIES` table. Series IDs (verify live; EIA occasionally
  reissues):
  - CL → `WCESTP31` (Cushing OK ending stocks) + `WCESTUS1` (total Lower-48 ex-SPR, context)
  - HO → `WDISTUS1` (total distillate stocks)
  - RB → `WGTSTUS1` (total motor gasoline stocks)
  Metals (GC/SI) have no EIA inventory report — `registry.get_energy()` routes them
  to `NullEnergyAdapter` (empty), never to NG storage.
- **Frequency:** weekly (`weekly`), monthly (`monthly`), daily (`daily`) where applicable.
- **Notes:**
  - APIv1 is deprecated. Use v2 only.
  - Series IDs from v1 (e.g., `NG.RNGC1.D`) can be translated to v2 using the EIA series-ID translator in the API browser.
  - The weekly storage release happens Thursdays at 10:30 ET. Schedule the worker for 10:35 ET on Thursdays with a small jitter and a retry envelope.

## §cftc — Commitment of Traders

- **API:** CFTC Public Reporting Environment (PRE), built on Socrata. Base `https://publicreporting.cftc.gov/resource/`.
- **Auth:** none required for read; an app token is recommended for higher rate limits (free, register on the PRE site).
- **Datasets we use:**
  - **Disaggregated Futures-Only** — Socrata resource code (check current code in PRE; previously `kh3c-gbw2`). The disaggregated report is the right one for natural gas because it splits speculators (managed money) from commercials.
  - **Legacy Futures-Only** — fallback if disaggregated isn't returning a particular field.
  - **Traders in Financial Futures (TFF)** — financial contracts only; we don't use it for NG but the schema lives here for future symbols.
- **Query example (disaggregated, NG, last 2y):**
  ```
  GET https://publicreporting.cftc.gov/resource/<code>.json
    ?$where=contract_market_name like 'NATURAL GAS%' and report_date_as_yyyy_mm_dd > '2024-05-01'
    &$order=report_date_as_yyyy_mm_dd DESC
  ```
- **Release cadence:** weekly Friday 15:30 ET; data dated as-of the previous Tuesday.
- **Notes:**
  - Late-2025: CFTC paused publication during a federal funding lapse, then resumed in chronological order. Adapter must tolerate gaps and out-of-order publication; never assume "the most recent report is for last Tuesday."
  - There is no primary key; sort by `report_date_as_yyyy_mm_dd` and `contract_market_name`.
  - The natural-gas contract market name we want includes `NATURAL GAS - NEW YORK MERCANTILE EXCHANGE`. There are several other NG-adjacent markets (Henry Hub Last Day, etc.) — match deliberately.
  - **Market codes (Phase 17)** in `adapters/positioning/cftc.py::MARKETS` and
    `instruments.json` metadata `cftc_market_code` (verify live — Socrata reissues):
    NG `023651`, CL `067651`, HO `022651` (NY Harbor ULSD), RB `111659` (Gasoline
    RBOB), GC `088691` (Gold, COMEX), SI `084691` (Silver, COMEX).

## §nws — National Weather Service

- **API:** `https://api.weather.gov/`
- **Auth:** none. Identify with a `User-Agent` header containing contact info — the NWS asks for this.
- **Format:** GeoJSON-LD; alerts use CAP v1.2.
- **Endpoints we use:**
  - `GET /points/{lat},{lon}` — returns the gridpoint URLs for a location. Always go through this first; do not hard-code grid coordinates.
  - `GET /gridpoints/{office}/{x},{y}/forecast` — 7-day forecast for a grid cell.
  - `GET /gridpoints/{office}/{x},{y}/forecast/hourly` — hourly forecast.
  - `GET /alerts/active?area={state}` — active alerts for a state (used for storm shock detection).
- **HDD/CDD:** the NWS does not return HDD/CDD directly. We compute them from the hourly/daily temperatures.
- **Region aggregation:** for the 6 NGTI regions (`northeast`, `midwest`, `mountain`, `pacific`, `south_central`, `southeast`), we maintain a list of representative population-weighted points per region in `apps/api/adapters/weather/regions.py`. The adapter pulls each point's forecast and aggregates with the configured weights.
- **Rate-limit posture:** generous but unspecified. Cache aggressively. Default in MVP: refresh every 6 hours per region.

## §market_data — front-month futures

The MVP uses a mock OHLCV generator (see `docs/MOCK_DATA_SPEC.md §price_bars`). For the eventual real data swap:

- **Nasdaq Data Link (formerly Quandl)** for end-of-day historical futures prices. CME-derived continuous contract series `CHRIS/CME_NG1` for front-month, `CHRIS/CME_NG2` for second-month, etc. Premium tiers exist for tick data.
- **Databento** for tick / order-book data. CME licensing applies. Documented as a future option only — not MVP.
- **TradingView UDF / Datafeed** — TradingView's Universal Data Feed adapter spec. We expose our own `/v1/tv-udf/*` endpoints (separate from the main API) so the embedded TradingView widget can pull our seeded bars directly. This is a polish-phase item, not Phase 02.

## §news — event intelligence

MVP uses curated fixtures (`packages/fixtures/news_events.json`) plus a placeholder adapter that accepts user-pasted articles via `POST /v1/news/ingest`. Future real adapters:
- **NewsAPI.org / GDELT** for headline streams. Both have free tiers. Keyword filter on a curated NG-relevant term list.
- **EIA "Today in Energy"** RSS as a curated upstream.
- **CME exchange bulletins** scraped or RSS-fetched for contract-specific notices.

For each ingested article, the news adapter calls `services.llm_explainer.extract_event` to produce the structured `category / sentiment / impact_score / affected_regions / entities` fields documented in `docs/SCHEMA.md`.

## §rate_limits_and_backoff

All adapters use a shared `apps/api/adapters/_http.py` HTTP client wrapping `httpx.AsyncClient` with:
- per-host concurrency limits
- exponential backoff with full jitter (max 5 retries)
- structured error logging that writes a row to `adapter_runs` on each call
- a "freshness" annotation so the data-health endpoint can surface stale-data warnings

## §do_not_do

- Do not log or persist API keys, even in error messages.
- Do not retry on 4xx other than 429.
- Do not crash a request path because an adapter is degraded; degrade gracefully, mark the data as stale, and let the dashboard show a "data degraded" badge.
- Do not let an adapter's mock and real outputs diverge in shape. The contract test in `tests/adapters/` enforces parity.
