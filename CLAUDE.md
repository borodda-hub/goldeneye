# CLAUDE.md — NGTI Project Conventions

You are working on **NGTI (Natural Gas Trading Intelligence)** — a research, forecasting, and decision-support terminal. Read this file fully on every new session.

## Product framing — non-negotiable

- NGTI is a **research and paper-trading terminal**. It is not a broker, not a financial advisor, not an automated trading system.
- Never produce output that promises returns, claims certainty, or gives personalized financial advice. The full AI behavior contract is in `docs/AI_BEHAVIOR.md` and is mandatory for every LLM-facing endpoint and UI string.
- Every screen that displays forecasts, scenarios, or signals must include the disclaimer string defined in `docs/AI_BEHAVIOR.md §disclaimer`.

## Architecture in one paragraph

A Next.js 14 (App Router) + TypeScript frontend talks to a Python FastAPI backend over REST and WebSocket. Postgres with the TimescaleDB extension stores time-series and relational data. Redis caches recent reads and holds live state for WebSocket fan-out. Modular adapter classes ingest market, energy, weather, positioning, and news data — all start as mock adapters returning fixtures, with real-source adapters as drop-in replacements behind the same interface. A model registry exposes baseline forecasts (moving average, ARIMA/Prophet, volatility regime, gradient-boosted placeholder). An LLM layer summarizes events, explains conditions, narrates scenarios, and reviews journal entries. Full detail in `docs/ARCHITECTURE.md`.

## Source-of-truth files (do not duplicate their content)

| Topic | File |
|---|---|
| System architecture | `docs/ARCHITECTURE.md` |
| Database schema | `docs/SCHEMA.md` |
| REST + WebSocket contracts | `docs/API_CONTRACTS.md` |
| Mock fixtures and seed rules | `docs/MOCK_DATA_SPEC.md` |
| LLM persona and forbidden phrases | `docs/AI_BEHAVIOR.md` |
| Frontend component tree and tokens | `docs/FRONTEND_COMPONENTS.md` |
| Real data source endpoints | `docs/DATA_SOURCES.md` |

When you need information from any of these, **read the file, do not infer**. When you change any of these, update the file in the same commit.

## Folder layout

```
apps/
  web/                  Next.js 14 App Router, TypeScript, Tailwind, Recharts
  api/                  FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic
packages/
  contracts/            shared OpenAPI-derived TypeScript types
  fixtures/             JSON fixture files referenced by docs/MOCK_DATA_SPEC.md
infra/
  docker-compose.yml    Postgres+Timescale, Redis, api, web, worker
  migrations/           Alembic migrations (one source of truth, generated)
docs/                   the source-of-truth files above
prompts/                phased build prompts
.claude/                Claude Code skills, agents, slash commands
```

## Coding conventions

**Python (backend)**
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic, `pytest`, `ruff`, `mypy --strict` on the `api` package.
- All adapters implement the `MarketDataAdapter` / `EnergyDataAdapter` / `WeatherDataAdapter` / `PositioningDataAdapter` / `NewsDataAdapter` protocols in `apps/api/adapters/base.py`.
- Endpoints live under `apps/api/routers/<domain>.py`. Business logic lives in `apps/api/services/`. Repositories live in `apps/api/repos/`. No business logic in routers.
- Every model output and every LLM output goes through `apps/api/services/safety.py::wrap_with_uncertainty()` before serialization.

**TypeScript (frontend)**
- Next.js 14 App Router, React Server Components by default, client components only when needed.
- Tailwind with the design tokens in `docs/FRONTEND_COMPONENTS.md §tokens`. No ad-hoc colors.
- Charts use Recharts for standard charts; Lightweight Charts (`lightweight-charts`) for the Chart View candlesticks.
- Shared types live in `packages/contracts/` and are generated from the FastAPI OpenAPI schema via `pnpm contracts:gen`. Never hand-write a type that exists in the OpenAPI doc.
- Data fetching uses TanStack Query. WebSocket subscriptions go through `apps/web/lib/realtime.ts`.

**Database**
- All time-series tables are TimescaleDB hypertables. Partitioning rules in `docs/SCHEMA.md §hypertables`.
- All migrations through Alembic. Never edit the database directly. Never write raw DDL outside a migration.

**Testing**
- Backend: `pytest` with `httpx.AsyncClient` for route tests and a TimescaleDB test container for integration tests. Aim for adapter contract tests on every adapter.
- Frontend: Vitest + Testing Library for components, Playwright for the dashboard happy path only (MVP).
- Contract tests in `tests/contracts/` verify the OpenAPI schema matches `packages/contracts/`.

## Token-budget rules

These exist because they cost nothing to follow and save thousands of tokens per session.

1. **Reference, don't restate.** Cite `docs/X.md §section` instead of pasting content.
2. **One concern per session.** Backend session does not touch `apps/web/`. Frontend session does not touch `apps/api/`. Schema session touches only `infra/migrations/` and `docs/SCHEMA.md`.
3. **Diff-mode after Phase 04.** Prefer extending existing modules. Avoid creating new top-level packages unless the prompt explicitly authorizes it.
4. **Delegate read-heavy work to sub-agents** — `backend-builder`, `frontend-builder`, `schema-keeper`. They run in their own context and return summaries.
5. **Use the skills.** When you see a pattern you've used before, check `.claude/skills/` first. Do not re-derive boilerplate.
6. **No speculative scope.** MVP target is a credible demo. "Production-ready", "enterprise-grade", "fully scalable" are all out of scope unless explicitly requested.

## Workflow expectations

- **Plan before code** for anything architectural. Use plan mode (`/plan`) and commit the plan into `docs/` before implementing.
- **Run `/health-check` before declaring a phase done.** This runs lint, typecheck, and tests across both stacks.
- **Run `/contract-check` whenever you change the FastAPI schema.** It regenerates frontend types and fails if anything diverged.
- **Update `docs/` in the same commit as the code change.** A schema change without a `docs/SCHEMA.md` update is an incomplete commit.

## Things you must never do

- Never call out to a real broker, real trading API, or real money venue from anywhere in the code.
- Never store API keys for paid data sources in the repo. All real-source adapters read from environment variables and have a mock fallback when the env var is missing.
- Never let an LLM endpoint return text without the safety wrapper from `services/safety.py`.
- Never write a UI string that says "guaranteed", "will profit", "buy this", "sell this", or any phrase from `docs/AI_BEHAVIOR.md §forbidden_phrases`.
- Never skip the disclaimer on a screen that displays forecasts, signals, or scenarios.

## Compaction guidance

When compacting this conversation, always preserve:
- the active phase number and its acceptance criteria
- any uncommitted file paths
- any deviations from the conventions above (with rationale)
- the disclaimer rule and the forbidden-phrase rule
