# docs/ARCHITECTURE.md — NGTI System Architecture

## 1. System overview

NGTI is a four-tier system:

```
┌─────────────────────────────────────────────────────────────┐
│  apps/web  (Next.js 14, App Router, TypeScript, Tailwind)   │
│   ├── Dashboard, Chart, Signal Lab, Scenario Lab            │
│   ├── Decision Journal, Paper Trading, Admin                │
│   └── TanStack Query (REST) + WebSocket (live)              │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WS
┌──────────────────────────▼──────────────────────────────────┐
│  apps/api  (FastAPI, Pydantic v2, SQLAlchemy 2.x async)     │
│   ├── routers/   (HTTP + WS surface)                        │
│   ├── services/  (business logic, safety wrapper, model     │
│   │              registry, scenario engine, LLM explainer)  │
│   ├── adapters/  (market, energy, weather, positioning,     │
│   │              news — protocol-based, mock-first)         │
│   ├── repos/     (DB access, never imported by routers)     │
│   └── workers/   (Celery / RQ scheduled ingestion)          │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────────┐   ┌─────────────┐
│  Postgres   │   │      Redis      │   │  External   │
│  +          │   │  cache + WS     │   │  data       │
│  TimescaleDB│   │  pub/sub        │   │  sources    │
└─────────────┘   └─────────────────┘   └─────────────┘
```

## 2. Service boundaries

### apps/web (frontend)
- App Router, server components by default.
- Reads via TanStack Query against `/api/*` REST endpoints.
- Subscribes to live updates via a single multiplexed WebSocket on `/ws`.
- Renders charts with Recharts (analytics) and Lightweight Charts (candlesticks).
- All design tokens come from `docs/FRONTEND_COMPONENTS.md §tokens`. No ad-hoc colors or spacings.

### apps/api (backend)
- Routers expose REST + WebSocket endpoints. Thin: validate, call service, return.
- Services own business logic and orchestrate adapters, the model registry, the scenario engine, and the LLM explainer. Every output passes through `services/safety.py::wrap_with_uncertainty`.
- Repositories own DB access. SQLAlchemy 2.x async sessions. No raw SQL outside repositories.
- Adapters are protocol-based. Each domain (market, energy, weather, positioning, news) has a `Protocol` in `adapters/base.py` and at least one mock implementation. Real adapters are drop-in replacements selected at startup via env config.
- Workers handle scheduled ingestion: EIA storage report on Thursdays, COT reports on Fridays, NWS forecast pulls every 6 hours, daily price-bar refresh.
- In-process scheduler (`services/resolution_scheduler.py`, B1): an env-gated `asyncio` loop started from the FastAPI lifespan that periodically calls `services/auto_resolution.py::resolve_open_decisions` so the calibration ledger compounds without a manual mark. Off by default — runs only when `AUTO_RESOLVE_ENABLED=true`; cadence is `AUTO_RESOLVE_INTERVAL_HOURS` (default 24, floored to 60s). It is a co-located convenience tier, not the heavy ingestion worker above; resolution is idempotent (`resolved_direction IS NULL` only) and look-ahead-safe (real `price_bars` via the front-month path).

### Postgres + TimescaleDB
- Time-series data lives in hypertables: `price_bars`, `tick_data`, `weather_observations`, `weather_forecasts`. See `docs/SCHEMA.md §hypertables`.
- Relational data: `instruments`, `contracts`, `eia_storage_reports`, `cot_reports`, `news_events`, `model_forecasts`, `scenario_runs`, `user_decision_journals`, `paper_trades`, `alerts`.
- Migrations through Alembic only.

### Redis
- L1 read cache for hot endpoints (front-month price, latest signal, current scenario list).
- WebSocket pub/sub backbone — services publish on channels, the WS gateway fans out to subscribed clients.
- Job queue when worker stack uses RQ; if Celery, Redis is the broker and result backend.

## 3. Data flow — read path (Dashboard load)

1. Browser navigates to `/dashboard`.
2. Server component calls `apps/api` for `/v1/dashboard/summary`.
3. The `dashboard` service composes:
   - latest front-month price from `price_bars` (or Redis)
   - current volatility regime from `services/volatility.py`
   - latest forecast from `model_forecasts`
   - latest 5 events from `news_events`
   - LLM-generated market summary via `services/llm_explainer.py`, wrapped by safety
4. Response returns; React renders.
5. Client component opens WebSocket, subscribes to `price.NG.front`, `signal.NG`, `events.NG`. New ticks update the dashboard live.

## 4. Data flow — write path (scheduled ingestion)

1. Worker fires (cron). Example: Thursday 10:35 ET — EIA storage release.
2. Worker calls `adapters/energy/eia.py::fetch_storage_report()`.
3. Validated record inserted via `repos/eia.py`.
4. `services/storage_signals.py` recomputes the storage-vs-expectation delta.
5. New `model_forecast` row written.
6. Redis pub on `signal.NG`.
7. WebSocket gateway pushes to subscribed clients.

## 5. The safety wrapper

Every model output and every LLM output passes through `services/safety.py::wrap_with_uncertainty(payload)`. This:
- attaches a `confidence` band (low / medium / high)
- attaches a `caveats` array (string list of known limitations)
- attaches an `as_of` timestamp
- attaches the standard disclaimer string from `docs/AI_BEHAVIOR.md §disclaimer`
- runs the forbidden-phrase scan on any free text and rejects with a structured error if a phrase is present

Rejecting at this layer is correct; the alternative is leaking unsafe text into the UI.

## 6. The model registry

`services/model_registry.py` holds named forecast models behind a single interface:

```python
class ForecastModel(Protocol):
    name: str
    horizon: Literal["1d", "1w", "1m"]
    def predict(self, ctx: ForecastContext) -> ForecastResult: ...
```

Live voters (four directional models):
- `MovingAverageDirectional` (3 horizons)
- `HoltTrend` (pure-numpy Holt/AR trend; replaced the Prophet stub in Phase 26b)
- `FactorComposite` (transparent rules-based blend of storage surprise, COT positioning, and momentum — hand-set weights, not a trained model)
- `LogRegDirectional` (genuinely *trained* logistic regression on price features; fit walk-forward on each call from only past closes, so it's look-ahead-safe by construction — numpy, no heavy ML dep)

`VolatilityRegime` is **context, not a voter** (Phase 26b): a regime label stamped on every forecast row and the ensemble, not a directional vote. The volatility/range engine (`services/models/vol_range.py`) is a separate, real-OOS-validated subsystem (EWMA + log-HAR with empirical fat-tail bands). `ProphetTrend` and `factor_learned` are benched (code + tests retained, not wired).

Signals shown in the Signal Lab are an ensemble vote across the live voters with explicit "supporting" / "contradicting" attribution per model.

**Per-asset-class config (Phase B5).** The voter thresholds, vol-regime bands, ensemble band-widths, and the scoring deadband are no longer NG hardcodes — they live in `services/asset_config.py`, keyed by `Instrument.asset_class`. `ForecastContext(asset_class=…)` resolves an `AssetClassConfig` (`config_for`) that `run_all` threads into every voter + the regime classifier; the model *logic* is unchanged (only constants are parameterized), so the look-ahead invariant and the cheating-model proof are untouched. The `commodity` entry holds the exact pre-B5 values — a byte-identical golden lock (`tests/test_asset_config_golden.py`) proves every existing asset class (commodity/metal/energy/…) is unchanged; `metal`/unknown fall back to `commodity`. Two non-commodity classes are lit up: **`index`** (ES) and **`rates`** (ZN), with hand-set, **unvalidated** scales (see `MODEL_DILIGENCE.md`). The paper engine's per-contract multiplier comes from `Instrument.contract_size` for the new classes; **existing commodities are deliberately pinned to the legacy `10000`** for demo continuity (a labeled deferral — issue #10).

> **For the current model truth — what is live, benched, validated, or unvalidated, and on what data — `docs/MODEL_DILIGENCE.md` is the source of truth.** This section describes shape; the diligence ledger is authoritative for claims.

## 7. The scenario engine

`services/scenario_engine.py` runs counterfactual scenarios. Each scenario:
- accepts a list of `ScenarioShock` objects (e.g. `WeatherShock(region="midwest", delta_temp_f=-8, days=10)`)
- applies shocks to a baseline forecast context
- re-runs the model registry against the shocked context
- generates an LLM narrative via `services/llm_explainer.py`
- returns: directional pressure, confidence, affected timeframe, assumptions, counterarguments, validating data

Scenarios are persisted in `scenario_runs` for replay.

## 8. The LLM explainer

`services/llm_explainer.py` is the only place we call an LLM. It exposes:
- `summarize_market(ctx)` — the dashboard one-liner
- `explain_signal(signal, ctx)` — Signal Lab supporting/contradicting narrative
- `narrate_scenario(scenario, results, ctx)` — Scenario Lab narrative
- `review_journal_entry(entry)` — Decision Journal feedback (assumption-finding, not advice)
- `extract_event(article)` — News intake parsing

Every method composes a structured prompt that includes the persona from `docs/AI_BEHAVIOR.md §persona`, the relevant data context, and an explicit constraint block forbidding the phrases in `§forbidden_phrases`. Output passes through the safety wrapper before return.

## 9. Deployment topology

**Local dev / demo:** `infra/docker-compose.yml` brings up Postgres+Timescale, Redis, api, web, worker. `pnpm dev` and `uvicorn` run with hot reload.

**Demo cloud:** Single VM (Hetzner / Fly.io / Railway). Postgres managed (Neon, Supabase, or Railway). Redis managed (Upstash). Web on Vercel pointed at the api hostname. Worker as a separate process or Fly Machine.

**Production (out of MVP scope):** Kubernetes or ECS, RDS for Postgres, ElastiCache for Redis, separate worker autoscaling group. Documented in `next-stage roadmap` only.

## 10. Configuration

All runtime config via environment variables, loaded by Pydantic `BaseSettings`. The full list lives in `apps/api/config.py` and `apps/web/.env.example`. Nothing in the repo is environment-specific aside from these files.

## 11. Observability (minimal — Phase B4)

The smallest genuinely-useful layer now that the app is multi-tenant (deliberately **not** a full APM/OTel buildout):
- **Structured request logging + request-id.** One ASGI middleware (`services/observability.py`) assigns/propagates `X-Request-ID`, times each request, and emits one structured log line (`method, route, status, duration_ms, request_id`). `log_level` is a settings field; `logging.dictConfig` is installed at startup.
- **Metrics.** `prometheus-client` registry (`services/metrics.py`) exported at `GET /v1/metrics`: `http_requests_total`, `http_request_duration_seconds`, `safety_violations_total`, `auto_resolutions_total{outcome}`, `ledger_events_total{event_type}`.
- **Safety-violation alerting.** A blocked LLM output (after retry) writes an `Alert` (`kind="safety_violation"`, best-effort `user_id`) — activating the previously-dormant `Alert` table — and increments the counter; it surfaces in the admin alerts view.
- Adapter health surfaced through `/v1/admin/data-health` (last-success timestamps per adapter run).
- `sentry_dsn` is a settings field for completeness; `sentry_sdk` wiring + full OpenTelemetry tracing remain out of scope (tracked re-entry items).

## 11a. Decision/audit ledger (Phase B4)

An **append-only, tamper-evident** record (`decision_ledger_events`, see `SCHEMA.md`) shadowing the mutable `user_decision_journals` row — the *"at the moment of decision, here is exactly what you knew"* compliance view. Events (`created` / `resolved` / `amended`) are appended on the journal-create + resolution paths (the resolution append is a post-decision side-effect — it observes, never changes, what the engine resolved, so the S3 look-ahead invariant is untouched). **Immutability is DB-enforced** (a `BEFORE UPDATE OR DELETE` trigger), and a per-decision SHA-256 **hash chain** makes any out-of-band edit detectable (`chain_ok`). The `created` snapshot captures the user's inputs plus the system state at that instant (ensemble read, vol band/regime, model lineup) — or, when capture fails, an **explicit recorded absence** with a reason (never silently omitted). Read surface: `GET /v1/ledger`, `GET /v1/ledger/{decision_id}` (user-scoped, by-id 404); the web Decision Ledger view renders the per-decision timeline with an integrity badge.

## 12. What we deliberately don't do in MVP

- No real broker integration. Paper trading is a self-contained simulator.
- ~~No production auth.~~ **Updated (B3a/B3b):** optional Clerk bearer-token auth + per-user data scoping is wired — every personal-artifact query filters by `user_id`, by-id paths enforce ownership (404), admin/desk are auth-gated. The app still runs **fully open/anonymous when Clerk is unconfigured** (the demo on the shared `user_id IS NULL` pool), so single-tenant deployment is unchanged. Role-based access (beyond any-authenticated) and the leaderboard visibility model are still future work.
- No real-time tick feed. Bars are 1-minute or coarser, fed by the mock adapter; Databento integration is roadmap.
- No production-grade ML training pipeline. Most voters are price-only or hand-set, though `LogRegDirectional` is a genuinely *trained* (walk-forward) model and the vol/range engine is real-OOS-validated; a heavyweight training/serving pipeline is still roadmap.

*(Historical note: a look-ahead-safe backtest engine **does** exist since Phase 10 — `services/backtest.py`, with a cheating-model proof in `tests/test_backtest_lookahead.py`. The earlier "no backtest engine" caveat is obsolete.)*
