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

MVP models:
- `MovingAverageDirectional` (3 horizons)
- `ProphetTrend` (1w, 1m)
- `VolatilityRegime` (regime label + transition probability)
- `FactorComposite` (transparent rules-based blend of storage surprise, COT positioning, and momentum — hand-set weights, not a trained model)
- `LogRegDirectional` (genuinely *trained* logistic regression on price features; fit walk-forward on each call from only past closes, so it's look-ahead-safe by construction — numpy, no heavy ML dep)

Signals shown in the Signal Lab are an ensemble vote across these models with explicit "supporting" / "contradicting" attribution per model.

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

## 11. Observability (MVP)

- Structured JSON logs from FastAPI (uvicorn access + app logger).
- Adapter health surfaced through `/v1/admin/data-health`, which reads last-success timestamps stored by each adapter run.
- A simple Sentry stub wired but disabled by default.
- Production observability (OpenTelemetry, metrics) is out of MVP scope.

## 12. What we deliberately don't do in MVP

- No real broker integration. Paper trading is a self-contained simulator.
- No production auth. A simple session cookie or bearer token over a single local user is acceptable for the demo. Multi-tenant comes later.
- No backtest engine. Forecasts are run forward only; backtesting is in the next-stage roadmap.
- No real-time tick feed. Bars are 1-minute or coarser, fed by the mock adapter; Databento integration is roadmap.
- No production-grade ML training pipeline. Models are placeholders that demonstrate shape; real training pipelines are roadmap.
