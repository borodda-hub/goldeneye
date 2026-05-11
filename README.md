# NGTI — Natural Gas Trading Intelligence

A research, forecasting, and decision-support terminal for natural gas markets. Built as a credible end-to-end demo of the analytical workflow a desk would use — data ingestion, ensemble forecasting, scenario analysis, decision journaling, and paper trading — without ever touching a real broker or claiming to give financial advice.

> **NGTI is a research and decision-support prototype.** It does not provide personalized financial advice, does not execute trades against real brokers, and does not guarantee any forecast or scenario. Paper trading is simulated. For research, education, and decision-quality practice only.

## What's in the box

Seven screens, all driven by a FastAPI backend and a TimescaleDB/Redis substrate:

| Screen | What it does |
|---|---|
| **Dashboard** | Front-month price, volatility regime, directional bias, futures curve, recent events, live ticks via WebSocket. |
| **Chart** | OHLCV candles + SMA20/EMA50 overlays + event markers; Lightweight Charts under the hood. |
| **Signal Lab** | 4-model ensemble (moving average, prophet, volatility regime, gradient-boost placeholder) with agreement, input diversity, confidence rationale, per-model supporting/contradicting factors, LLM explanation, history table with server-side hit/miss scoring. |
| **Scenario Lab** | 6 preset templates (cold snap, LNG export disruption, freeze-off, hurricane, geopolitical, heat wave); strict-typed composable shocks; reruns the model registry against shocked context; LLM narrative with structurally-deterministic assumptions/counterarguments/data-needed-to-validate. |
| **Decision Journal** | Hypothesis + evidence + confidence + planned action + risk factors + invalidation criteria; LLM review writes assumption-finding feedback, not endorsement. |
| **Paper Trading** | Long/short with stop and take; live mark-to-market via WS price ticks; PnL math using NG tick value; equity curve with $100k starting equity; 10× leverage cap. |
| **Admin** | Adapter health (cadence-aware status), model health (sample counts), alerts with ack, environment presence flags. |

Every model output and every LLM string passes through a safety wrapper that scans for forbidden phrases and attaches a `{ confidence, caveats, as_of, disclaimer }` envelope.

## Architecture in one paragraph

A Next.js 14 (App Router) + TypeScript frontend talks to a Python FastAPI backend over REST and WebSocket. Postgres + TimescaleDB stores time-series and relational data. Redis caches recent reads and holds live state. Adapters for market, energy, weather, positioning, and news data are protocol-based — all start as mocks returning fixtures, with real-source adapters as drop-in replacements behind the same interface. A model registry exposes baseline forecasts. An LLM layer summarizes events, explains conditions, narrates scenarios, and reviews journal entries. Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```
apps/
  web/           Next.js 14, App Router, TypeScript, Tailwind, Recharts, Lightweight Charts
  api/           FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic
packages/
  contracts/     OpenAPI-generated TypeScript types
  fixtures/      JSON seed data
infra/
  docker-compose.yml
  migrations/    Alembic
docs/            Source-of-truth design docs
```

## Quickstart

Requirements: Docker, [pnpm](https://pnpm.io/), [uv](https://docs.astral.sh/uv/).

```bash
# Clone, then:
make demo
```

That single command spins up Postgres + Redis, runs migrations, seeds demo data, regenerates contracts, and starts the API + web dev servers. The UI lands on `http://localhost:3000`.

Manual flow if `make demo` doesn't fit your environment:

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m apps.api.seeds.demo --fresh
pnpm install
pnpm contracts:gen:local
pnpm dev   # spawns api + web concurrently
```

## Source-of-truth docs

| Topic | File |
|---|---|
| System architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Database schema | [`docs/SCHEMA.md`](docs/SCHEMA.md) |
| REST + WebSocket contracts | [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) |
| Mock fixtures and seed rules | [`docs/MOCK_DATA_SPEC.md`](docs/MOCK_DATA_SPEC.md) |
| LLM persona, forbidden phrases, safety contract | [`docs/AI_BEHAVIOR.md`](docs/AI_BEHAVIOR.md) |
| Frontend component tree and tokens | [`docs/FRONTEND_COMPONENTS.md`](docs/FRONTEND_COMPONENTS.md) |
| Real data source endpoints | [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) |
| Deployment paths | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| 5-minute demo walkthrough | [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) |
| Next-stage roadmap | [`docs/ROADMAP.md`](docs/ROADMAP.md) |

## What this is not

- Not a broker. Not a trading API. Not connected to any real exchange or counterparty.
- Not a financial advisor. The LLM is constrained by `docs/AI_BEHAVIOR.md` and the safety wrapper rejects any output that uses forbidden phrases (`guaranteed`, `will profit`, `go long`, etc.).
- Not a production ML stack. The four MVP models are intentional placeholders that demonstrate the shape of an ensemble — real training pipelines are in `docs/ROADMAP.md`.
- Not multi-tenant. Single local user; no auth scope; `user_id` stays NULL across all rows.

## Design language

Bloomberg / Palantir / TradingView aesthetic. Dark terminal palette. Hairline borders (no shadows). Color reserved for signal (up/down/flat, confidence bands). Numbers always font-mono tabular-nums with consistent precision per metric. Terse, institutional copy.

## Development

```bash
# Run all checks (lint + typecheck + tests, both stacks)
pnpm health

# Just one stack
pnpm --filter web run typecheck
pnpm --filter web run test
uv run --directory apps/api pytest

# Regenerate OpenAPI → TypeScript types after backend route changes
pnpm contracts:gen:local
```

The full health check is run by the `/health-check` slash command in Claude Code.

## License

MIT. See `LICENSE`.

## Credit

Built as a portfolio project. The phased build prompts are in `files/ngti-playbook/`.
