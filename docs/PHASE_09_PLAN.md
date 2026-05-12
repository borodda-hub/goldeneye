# Phase 09 Plan — Real Data Layer

**Goal:** Replace mock adapters with real (or delayed-real) data sources, and wire LLM calls through a per-method model-routing policy that minimizes token cost without sacrificing quality. No new screens, no schema changes.

The architecture was scoped for this exact swap — protocol-based adapters in `apps/api/adapters/base.py` are drop-in replaceable via env vars per `docs/ARCHITECTURE.md §2.2`.

**Estimated total:** ~7-10 working days. One commit per sub-step.

---

## Step 0 — Working-tree hygiene (~½ day)

| Sub-step | Action |
|---|---|
| **0a** | ORM `Enum → Text` swap committed — Alembic migration 001 is the source of truth for enum types. ORM no longer redundantly declares them. |
| **0b** | `apps/web/next-env.d.ts` added to `.gitignore`. |
| **0c** | Three dashboard display bugs: `impact_score` cast to float, `change_pct` multiplied by 100 in HeaderRow, `VolRegime` TS type aligned to backend `compressed\|normal\|elevated\|crisis`. |
| **0d** | This plan committed to docs. |

Bonus commit in the same window: CORS middleware added to FastAPI so the web dev server can reach the API.

---

## Step 1 — Real fundamental adapters (~4-5 days)

For each adapter:
1. New file in `apps/api/adapters/<domain>/<source>.py` implementing the existing Protocol in `apps/api/adapters/base.py`.
2. Wire into `apps/api/adapters/registry.py`, selectable via env var. Mock fallback when env var missing.
3. Scheduled task in `apps/api/workers/`.
4. Contract tests against the Protocol.
5. Update `docs/DATA_SOURCES.md` with endpoint + auth notes.

### 1a — EIA storage adapter (~1 day)

- File: `apps/api/adapters/energy/eia.py`
- Source: EIA Open Data API, series `NG.NW2_EPG0_SWO_R48_BCF.W`
- Auth: free key in `EIA_API_KEY` env var; mock fallback when missing
- Schedule: Thursday 10:35 ET
- Cache: Redis, full-week TTL
- Persists to: `eia_storage_reports`
- **Unlocks:** Signal Lab's `latest_storage` input is real; Scenario Lab storage shock validates against real reports.

### 1b — CFTC COT adapter (~1 day)

- File: `apps/api/adapters/positioning/cftc.py`
- Source: CFTC Disaggregated Commitments of Traders weekly CSV
- Filter: NG futures (CFTC code 023651)
- Extract: managed-money net + WoW delta
- Schedule: Friday 15:30 ET
- Persists to: `cot_reports`
- **Unlocks:** xgboost placeholder's `latest_cot` input is real; closes Phase 5's biggest credibility gap (`input_diversity: high` becomes honest).

### 1c — NWS weather adapter (~1-2 days)

- File: `apps/api/adapters/weather/nws.py`
- Source: NWS gridded forecast API (`api.weather.gov`)
- No auth required
- Pre-loaded region→grid mapping for major gas demand centers (Northeast, Midwest, Southeast, Texas, Mountain, Pacific)
- Schedule: every 6 hours
- Persists to: `weather_observations`, `weather_forecasts`
- **Unlocks:** Dashboard recent events, weather shocks, HDD anomaly features all real.

---

## Step 1.5 — LLM model routing + token efficiency (~1-2 days)

Touches: `apps/api/services/llm_client.py`, `apps/api/services/llm_explainer.py`, `apps/api/services/llm_prompts.py`, `apps/api/config.py`.

### 1.5a — Per-method routing matrix (locked rules)

| Method | Default Model | Why |
|---|---|---|
| `summarize_market` | **Haiku 4.5** | One-liner, called on every dashboard load. Formulaic prose, safety wrapper catches issues. Highest call frequency → biggest savings. |
| `extract_event` | **Haiku 4.5** | Structured extraction (category, sentiment, impact). JSON output, no creative reasoning. |
| `explain_signal` | **Sonnet 4.6** | Multi-input reasoning across 4 models + alt-data. Safety-critical institutional-tone prose. |
| `narrate_scenario` | **Sonnet 4.6** | 5 required sections, shock composition reasoning. |
| `review_journal_entry` | **Sonnet 4.6** | Assumption-finding with directional-language avoidance. |
| Escalation → **Opus 4.7** | `narrate_scenario` with ≥4 shocks **OR** `review_journal_entry` with `confidence_pct >= 80`. | Cases where wrong output has the most user impact. Rare. |

Implementation: `select_model(method, ctx) -> str` pure function in `llm_client.py`. Env overrides via `LLM_MODEL_<METHOD>` for testing.

### 1.5b — Prompt caching on every call

Persona + forbidden-phrases block in `llm_prompts.py` (~1.5k tokens) is identical across all 5 methods. Cache it via Anthropic's `cache_control: { type: "ephemeral" }` on the system message. ~90% input-token reduction on cache hits. 5-min TTL default; 1h for corpus tests.

### 1.5c — Context payload trimming

- `summarize_market`: pass only `direction`, `vol_regime`, `last_price`.
- `explain_signal`: keep full results but cap each model's `supporting`/`contradicting` to top-2 entries.
- `review_journal_entry`: cap evidence array to first 5 rows.

### 1.5d — Response cache for high-frequency calls

Redis cache on `summarize_market` results, 10-min TTL. Key: `llm:summary:{symbol}:{vol_regime}:{direction}:{round(last_price, 1)}`. Dashboard refreshes within window pay zero LLM cost.

### 1.5e — Telemetry + cost guardrails

- New `llm_calls` table: `(method, model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, latency_ms, ts)`.
- `LLM_DAILY_TOKEN_BUDGET` env var. On overrun, auto-downgrade all calls to Haiku 4.5 for the rest of the day. Surfaces in `/admin` as amber status.
- Admin screen tile: "LLM usage today" — input/output tokens, cost estimate, cache hit ratio.

### 1.5f — Test corpus via Batch API

`tests/llm/test_explain_signal_corpus.py` and `tests/llm/test_narrate_scenario.py` 50-response live runs (gated by `pytest -m llm_live`) switch to Anthropic Batch API → 50% off, async. Mock-mode tests unchanged.

**Expected impact:** ~75-80% LLM token-cost reduction at moderate use (1 dashboard load every 5 min, 2 signal explanations, 1 scenario, 1 journal review per day). Quality unchanged.

---

## Step 2 — Delayed market data adapter (~2 days)

### 2a — `yfinance` delayed adapter (~1 day)

- File: `apps/api/adapters/market/yfinance_delayed.py`
- Implements `MarketDataAdapter` protocol
- Source: Yahoo Finance via `yfinance` library (15-min delayed for NG futures)
- Symbol mapping: `NG=F` (front-month) + contract-specific (`NGM26.NYM`-style) → our `contract_code` scheme
- Persists 1m bars to `price_bars` table

### 2b — Replace `tick_simulator.py` (~½ day)

- File: `apps/api/workers/tick_simulator.py` → rename to `delayed_quote_poller.py`
- Poll every 15 min, emit latest quote to WS channel `price.NG.front`
- Same WS payload shape — frontend unchanged

### 2c — UX honesty fixes (~½ day)

- `apps/web/components/LiveDot.tsx`: accept `mode: "live" | "delayed"` prop; render "DELAYED 15m" amber badge when delayed
- `apps/web/components/dashboard/DashboardLiveBar.tsx`: surface the delayed status
- `apps/api/services/data_health.py`: adapter status reflects delayed cadence
- `docs/AI_BEHAVIOR.md`: explicit clarification that "delayed" labeling is required when feed isn't real-time

---

## Step 3 — Seed example user content (~½ day)

- File: extend existing seed script (or add `infra/seed/example_journal_and_trades.py`)
- 2-3 `user_decision_journals` rows with realistic hypotheses, evidence, confidence, and pre-generated `llm_review` text (via mock LLM, deterministic)
- 2-3 closed `paper_trades` linked to journal entries, with computed PnL
- Wired into `make demo` so first-load demo experience has content on every screen

---

## Step 4 — Stop and decide

No code. Re-evaluate next direction:
- TradingView widget swap (~3-5 days, optional)
- Backtest engine (~2 weeks)
- Multi-instrument (WTI crude) (~few days)
- Deploy to managed VM/Vercel (~1 day)

---

## Out of scope (deliberately deferred)

- TradingView widget — defer to Step 4 decision
- Backtest engine, real ML pipeline
- Multi-tenant auth, OpenTelemetry, mobile responsive
- Multi-instrument
- Tick-level / DOM data (paid Databento path — ~$182/mo)

---

## Acceptance criteria for Phase 09

- All four data adapters work in real mode when env vars set, fall back to mock when missing.
- LLM routing matrix enforced; prompt caching live; daily-budget guardrail wired.
- `pytest` and `pnpm health` green.
- Dashboard shows delayed (not synthetic) prices, with honest "DELAYED 15m" label.
- Signal Lab's `confidence_rationale` references real storage and COT data.
- Demo on first load: example journal entries visible, example closed trades visible.
- No new screens, no schema migrations, no LLM contract changes.
