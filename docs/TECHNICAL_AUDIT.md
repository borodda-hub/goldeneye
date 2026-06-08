# Goldeneye / NGTI — Technical Due-Diligence Report

**Subject:** `github.com/borodda-hub/goldeneye` (internal codename **NGTI — Natural Gas Trading Intelligence**)
**Public face:** goldeneyeterminal.com
**Audited commit:** `2c5daad` — *"docs(phase31): mark EIA_API_KEY resolved — set in .env + validated live"* (2026-06-07)
**Report date:** 2026-06-08
**Method:** Full repository clone, static read of source, tests, migrations, config, and docs. The live website was reviewed separately. Test files were inventoried and read but the suite was **not executed** (it requires Docker/Timescale/Redis containers not available in the audit sandbox); reported pass counts are the project's own documented figures and are flagged as such.

---

## 0. Methodology, scope, and how to read this report

This audit cross-checks every load-bearing claim — from the public site, the pitch brief, and the repo's own docs — against the actual source at commit `2c5daad`. Each subsystem is graded:

- **REAL** — implemented, tested, and does what it claims.
- **PARTIAL** — implemented but with a material limitation, a stale claim, or a gap that diligence will find.
- **PLACEHOLDER / NOT WIRED** — exists in shape only, or is disabled/unscheduled by default.

A recurring theme is **documentation drift**: the codebase has moved through ~31 build phases over four weeks, and several "source-of-truth" docs (notably `ARCHITECTURE.md` and the public website) describe earlier states. Where a doc and the code disagree, **the code is treated as ground truth** and the drift is called out, because that is exactly what a sharp reviewer will catch.

The single most important finding up front: **the product is more honest, and in some respects more built-out, than the brief I was given suggests — but its public-facing language (website + pitch) still carries several claims the current code has either outgrown or quietly walked back.** The risk in diligence is not that the engineering is thin; it is that the *marketing* is ahead of and occasionally behind the code in ways a quant reviewer will probe.

---

## 1. Executive summary

Goldeneye is a research and decision-support terminal for commodity markets (natural gas first, six commodities wired: NG/CL/HO/RB/GC/SI), built as a Next.js 14 + FastAPI monorepo over Postgres/TimescaleDB and Redis. It is explicitly **not** a broker, not an advisor, and not an automated trader — and that constraint is enforced in code, not just in copy.

What the audit found, in one paragraph: the **scaffolding is genuinely rigorous** — a look-ahead-safe backtest with a working cheating-model proof, a real walk-forward volatility/range engine validated out-of-sample on ~10 years of real data, a real conviction-at-decision calibration engine with sample-size guardrails and built auto-resolution, a structurally-enforced safety layer, disciplined per-task LLM routing, and ~900 backend / ~400 web tests under CI with `mypy --strict`. The **predictive alpha is, by the team's own honest admission, not there** for price *direction* — and the code correctly declines to manufacture it. The one validated edge is volatility/range calibration, which the team itself describes as table-stakes. The defensible asset is therefore **the honesty architecture plus the compounding calibration ledger**, not a proprietary signal.

The headline strategic tension for diligence:

> The website still advertises **"Four models … Prophet … Factor Composite,"** an **"explainable forecast"** directional story, and **"live"** data. The code has replaced Prophet with a numpy Holt model, relabels the hand-set composite honestly, has *demoted the directional confidence claim* to "Agreement: N of M" because it found no real directional edge, ships **mock adapters by default**, and runs the LLM in **fake mode by default**. None of this is dishonest in the repo — the repo is scrupulous about it — but the public surface has not fully caught up. A reviewer who reads the code after the website will notice the gap.

### Verdict by subsystem

| Subsystem | Grade | One-line |
|---|---|---|
| Backtest engine (look-ahead safety) | **REAL** | Three-layer defense + working cheating-model proof; single-front-month limitation. |
| Volatility/range engine | **REAL** | Walk-forward EWMA + log-HAR, empirical fat-tail bands, validated OOS on ~10y real data. |
| Directional forecasting | **PARTIAL (honest)** | No real OOS edge; product correctly declines. logreg/factor unvalidated on real features. |
| Decision-quality / calibration | **REAL** | Conviction snapshot + reliability diagram + n≥3 guardrail; auto-resolution built but unscheduled. |
| Safety / epistemic-honesty layer | **REAL** | Forbidden-phrase scan + retry-then-block, disclaimer envelope, certainty regex. |
| LLM layer | **REAL, single-shot** | 9 tasks, 3-tier routing, prompt caching, graceful degradation; no tool use / agentic loop; fake by default. |
| Data adapters (5 domains) | **PARTIAL** | Real adapters exist for all five; **mock by default**; only EIA confirmed wired live in prod env. |
| Price history persistence | **PARTIAL (improved)** | Real Yahoo backfill **persists to the Timescale hypertable** — corrects the "seeded/unfed" claim; coverage per-contract uncertain. |
| Frontend | **REAL** | 8 screens, 103 components, deep chart stack, 74 web test files. |
| Auth / multi-tenancy | **PLACEHOLDER** | Clerk built but optional; anonymous single-user, `user_id` NULL by default. |
| Testing / CI | **REAL** | 75 backend + 74 web test files; CI runs ruff, mypy --strict, pytest, biome, typecheck, vitest. |

---

## 2. Claims-vs-code reconciliation (the diligence-survival table)

This is the section a skeptical partner should read first. Each row is a claim from the website, the pitch brief, or repo docs, with the code verdict and evidence.

| # | Claim (source) | Verdict | Evidence in code |
|---|---|---|---|
| 1 | "Look-ahead-safe replay with cheating-model property tests" (website) | **TRUE** | `services/backtest.py` strict `ts < as_of` + runtime assertions; `tests/test_backtest_lookahead.py` asserts a future-leaking model stays `hit_rate ≤ 0.65`. |
| 2 | "Four models: Moving Average · Volatility Regime · Prophet · Factor Composite" (website) | **STALE** | Live voters are MA + **holt_trend** + factor_composite + **logreg_directional**; `volatility_regime` is **context, not a voter**; `prophet_trend.py` is unused (prophet is an *optional, uninstalled* dep). |
| 3 | "Explainable Forecasts … honest hit-rate," directional hero (website) | **PARTIAL** | Real per-model attribution exists, but the team found **no OOS directional edge** (`MODEL_DILIGENCE.md`) and changed the UI to "Agreement: N of M," not a hit-rate probability. Website still leads with direction. |
| 4 | "The 4th model (XGBoost) is a hardcoded heuristic" (pitch brief) | **INACCURATE** | There is **no XGBoost** (it's an optional, uninstalled extra). The hand-set model is `factor_composite`, which *self-labels* "Not a trained model." A genuinely **trained** model (`logreg_directional`) also exists. |
| 5 | "LLM confidence bands are hardcoded 'medium'" (pitch brief) | **TRUE (narrow)** | `llm_explainer.py` passes literal `confidence="medium"`/`"low"` at 7 call sites. But vol/range bands are empirically calibrated and directional confidence comes from the model — so the gap is the *LLM narrative envelope* only. |
| 6 | "Calibration resolution is manual" (pitch brief) | **OUTDATED** | `services/auto_resolution.py` + `POST /v1/journal/auto-resolve` auto-resolve against real prices using the backtest's scoring. The real gap is it is **unscheduled** (no cron). |
| 7 | "Production price history is seeded GBM; hypertables exist but unfed" (pitch brief) | **OUTDATED** | `services/price_backfill.py` fetches real Yahoo OHLC and **upserts into `price_bars`** (`source="yahoo_delayed"`), with `replace_mock` to retire the GBM showcase. Per-contract real coverage in the deployed DB is unconfirmed from code alone. |
| 8 | "LLM is single-shot — no tool use, no RAG, no agentic loop" (pitch brief) | **TRUE** | `llm_client.call_llm` is one `messages.create` with no `tools=`. Concierge/agentic copilot is queued (Phase 27), not built. |
| 9 | "7 wired Claude features" (pitch brief) | **UNDERCOUNT** | Nine task types: summarize_market, explain_signal, narrate_scenario, review_journal_entry, extract_event, extract_prediction, **critique_thesis**, **devils_advocate**, **coach_dq**. |
| 10 | "Real per-task model routing (Haiku→Sonnet→Opus), ~90% token savings via persona caching, graceful degradation" | **TRUE** | `services/llm_routing.py` matrix + escalation; `llm_client._call_real` uses cached `system_blocks`; falls back to canned on any error. |
| 11 | "Safety layer structurally forbids advice/guarantee language" | **TRUE** | `services/safety.py` word-bounded forbidden-phrase regex + certainty regex; `llm_explainer._call_with_safety_check` scans, retries once stricter, then raises `SafetyViolation`. |
| 12 | "Live official-source data across 5 domains" (website/brief) | **PARTIAL** | Real adapters exist for EIA, CFTC, NWS, Yahoo, RSS/NewsAPI — but **all five default to `mock`** (`settings.adapter_*`). Only `eia_api_key` is noted as set+validated live in the deployed `.env`. |
| 13 | "Decision-quality engine: conviction snapshot → reliability diagram with sample-size guardrails + per-bucket LLM coaching" | **TRUE** | `services/calibration.py` (n≥3 guardrail, `thesis_conviction_at_write` snapshot, the exact "Your X% theses resolved at Y%" line) + `services/dq_coach.py`. |
| 14 | "~149 components, 8 screens, 9 themes" (website/brief) | **MOSTLY TRUE** | 8 app screens confirmed; **103 non-test components** (149 likely counts tests/stories). Themes not separately re-counted. |
| 15 | "Default `LLM_MODE=fake`" (brief) | **TRUE** | `settings.llm_mode: Literal["fake","real"] = "fake"`. |
| 16 | "No multi-tenant; user_id stays NULL" (README) | **TRUE** | Clerk is optional (`clerk_publishable_key` default `""` → anonymous); auth is built but not enforced. |

**Net for diligence:** the dangerous rows are **#2, #3, #12** — public-facing claims (Prophet, the directional forecast hero, "live" data) that a reviewer can falsify by reading the code or hitting the demo with default config. The fix is cheap (update the website and demo env), and the underlying engineering is sound. Rows #4, #6, #7 are cases where the **pitch brief understates the code** — those are easy wins to correct in your favor.

---

## 3. System architecture

### 3.1 Topology

A four-tier system, accurately described by `docs/ARCHITECTURE.md` at the structural level (the doc's *model* and *backtest* sections are stale; the topology is not):

```
apps/web  (Next.js 14 App Router, RSC, TypeScript, Tailwind)
   │  REST (TanStack Query) + a single multiplexed WebSocket (/ws)
apps/api  (FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic)
   ├── routers/    57 endpoints across 23 routers (thin: validate → service → return)
   ├── services/   business logic, safety wrapper, model registry, scenario + backtest + calibration engines, LLM
   ├── adapters/   market / energy / weather / positioning / news — Protocol-based, mock + real siblings
   └── repos/      DB access (never imported by routers)
        │
   Postgres + TimescaleDB   Redis (cache + WS pub/sub)   External sources (EIA/CFTC/NWS/Yahoo/RSS)
```

Layering discipline is real and enforced by convention (`CLAUDE.md`): routers stay thin, business logic lives in services, DB access is isolated in repos, and every model/LLM output is meant to pass through `services/safety.py`. Spot-checks confirm the pattern holds.

### 3.2 Monorepo layout

- `apps/web` — frontend (App Router route group `(app)` holds the 8 screens).
- `apps/api` — backend (`adapters`, `services`, `services/models`, `services/indicators`, `services/patterns`, `repos`, `routers`, `models/orm`, `realtime`, `seeds`, `auth`).
- `packages/contracts` — OpenAPI-derived TS types (**note:** not imported by app code; web uses a hand-written `lib/api.ts`, and the contracts package drifted across phases — a known, documented weakness).
- `packages/fixtures` — JSON seed data.
- `infra` — `docker-compose.yml` + Alembic migrations.
- `docs` — 30+ source-of-truth and phase-plan docs, including the candid `MODEL_DILIGENCE.md`, `HANDOFF.md`, and `DILIGENCE_AND_30C_PLAN.md`.
- `tests/` (repo root) — adapter, contract, db, llm, realtime integration tests, separate from `apps/api/tests`.

### 3.3 Engineering hygiene signals

- **239 commits** over ~4 weeks (2026-05-10 → 06-07), conventional-commit style (123 `feat`, 38 `fix`, 20 `docs`). Steady, disciplined cadence.
- Stack pins are current and sane: FastAPI ≥0.111, Pydantic ≥2.7, SQLAlchemy 2.x async, numpy/pandas, `anthropic` SDK, `reportlab` (PDF export), `pyjwt`+`cryptography` (Clerk JWT verification). **Prophet and XGBoost are *optional* extras and are not installed** — core forecasting is numpy-only by deliberate design.
- A two-lane git flow (`develop` → `master`) with owner sign-off before promotion is documented and visible in `HANDOFF.md`.

---

## 4. The backtest engine — `services/backtest.py` · **REAL**

This is the credibility-load-bearing component and it holds up.

**What it does.** Replays a model day-by-day over a date range. For each calendar date `d` it (1) builds a `ForecastContext` strictly from data known at `d`, (2) runs the model, (3) looks up the realized move at `d + horizon`, and (4) scores it via the same `signal_scoring.score_forecast` the live Signal Lab uses (±0.3% deadband, hit/miss/indeterminate/neutral/pending).

**Look-ahead defense — three layers, all present:**

1. **Single chokepoint.** `_context_as_of()` is the only place a context is constructed; every leg (`_closes_as_of`, `_storage_as_of`, `_cot_as_of`) flows through it.
2. **Strict SQL bound.** Price closes use `PriceBar.ts < as_of` (strict, not `<=`); EIA uses `report_date <= as_of.date()` (correct — Thursday 10:30 ET release is public by EOD); COT uses `release_date <= as_of.date()` (Friday release). A unit test inspects the *compiled SQL* to assert `<` and the absence of `<=`.
3. **Runtime assertions.** After each query a Python-side loop re-checks every returned row and raises `RuntimeError("backtest look-ahead detected: …")` if anything with `ts >= as_of` slipped through — defense against a future regression relaxing the WHERE clause. A test (`test_closes_as_of_runtime_assertion_catches_leak`) forces a leak and asserts the raise.

**The cheating-model proof** (`test_cheating_model_does_not_score_100_percent`). A synthetic `predict_fn` is injected that would score ~100% *if* the future leaked into `ctx.closes`. Run over a deterministic random walk, the test asserts `hit_rate ≤ 0.65` (well below the ~1.0 a real leak would produce, with headroom for chance on a ~60-row sample). This is a genuine, well-reasoned proof — not a token test.

**Limitations (acknowledged in code):**
- **Single front-month contract, no rollover** (`_resolve_contract_id` picks today's front month for the whole window; pre-listing dates produce `pending`). This is the biggest methodological caveat for any long-horizon backtest claim.
- `retrain_cadence_days` is a placeholder (not honored).
- Backtest rows persist to `model_forecasts` with `inputs_hash="backtest:v1"` via delete-then-insert (no unique index) — idempotent but not concurrency-safe.

---

## 5. Forecasting models — `services/models/` · **PARTIAL (honest)**

**Live ensemble: four voters + one context signal.**

| Model | File | Nature | Status |
|---|---|---|---|
| Moving-average directional | `moving_average_directional.py` | SMA-20/50 cross, price-only (≥55 closes) | live voter |
| Holt trend | `holt_trend.py` | pure-numpy Holt/AR, price-only (≥30 closes) | live voter (replaced Prophet) |
| Factor composite | `factor_composite.py` | **hand-set** weighted blend (storage surprise + COT delta + momentum); self-labels "Not a trained model" | live voter |
| Logistic regression | `logreg_directional.py` | **genuinely trained** (gradient descent, walk-forward, numpy-only); look-ahead-safe by construction; passes the cheating-model proof | live voter |
| Volatility regime | `volatility_regime.py` | regime label | **context** stamped on every row, not a directional vote (Phase 26b) |

**Benched (code + tests retained, not wired):** `prophet_trend.py` (Prophet stub), `factor_learned.py` (lost its honest gate vs the hand-set composite on OOS Brier), and the raw-variance HAR estimator (blew up on real CL).

**The ensemble** (`services/ensemble.py`) is **calibration-weighted**: each vote is scaled by an inverse-Brier weight clamped to `[0.4, 2.0]`, so a well-calibrated model counts more and a chronically-overconfident one (e.g. the MA model's "high" calls) counts less. Crucially, the docstring states the honest scope itself: this is **down-weighting demonstrably-miscalibrated models, not a claim of a calibrated confidence gradient** — the walk-forward harness (`ensemble_calibration.py`) found no reliable OOS gradient at any horizon.

**The honest directional finding** (`MODEL_DILIGENCE.md`, validated on ~10y real OOS data via `seeds/validate_direction_real.py`): price-only directional models score ≈45–57% decisive accuracy, **below a drift-aware naive baseline in all 36 (symbol×horizon) cells**, with no confidence gradient. `logreg`/`factor` cannot be validated on real data yet because they consume synthetic COT/storage features — they are explicitly marked **unvalidated**, blocked on real historical COT+EIA ingestion (deferred). This is the single biggest *predictive* gap, and the product's correct response is to not sell direction.

---

## 6. The volatility / range engine — `services/models/vol_range.py` · **REAL**

The one genuinely validated edge, and the best code in the repo.

- **Mechanism:** RiskMetrics EWMA (λ=0.94) of daily log-return vol, scaled by √h, turned into ±multiplier·σ·√h bands. **Opt-in/now-default log-HAR** (Corsi 2009 HAR-RV on *log* realized variance with a causal Jensen back-transform) sharpens the point forecast and fixes the raw-variance HAR's vol-explosion blow-up.
- **Calibration:** band multipliers are **empirical walk-forward quantiles of past standardized moves** (Phase 30c), not fixed normal-z — so the 95% band reflects real fat tails. Normal-z fallback until ~40 residuals exist.
- **Honesty baked into the code:** `walk_forward_coverage()` *measures* how often the band actually contained the move (the locked calibration test), and `forecast_vol_correlation()` reports `n_eff` (non-overlapping window count) so overlapping-window significance isn't over-read. The docstring explicitly warns that the **point-forecast vol level is not reliable OOS — use the band width**.
- **Validation (per `MODEL_DILIGENCE.md`, real-OOS, ~10y, 6/6 commodities):** 80% band coverage 78–81%; 95% coverage 93–95% after 30c; forward-vol correlation 0.44–0.59 on real data (stronger than synthetic). It survived an adversarial test built to break it.
- **Team's own framing (adopt this verbatim):** the edge is real but **table-stakes** (the GARCH/HAR vol-autocorrelation fact every desk knows). The moat is honest calibration + presentation, not a proprietary signal. Saying this proactively is more credible than implying directional alpha.

---

## 7. Decision-quality / calibration engine · **REAL (the crown jewel)**

This is the asset the strategy should be built around, and it is genuinely built.

- **Conviction snapshot.** `calibration.py::_conviction_for` prefers `thesis_conviction_at_write` (the value captured *at decision time*, migration `006_journal_calibration`) and falls back to `confidence_pct` for legacy rows. This ex-ante capture is the mechanism the whole pitch rests on, and it exists.
- **Reliability diagram.** `compute_calibration` buckets entries (default 5: 0-20…80-100), computes per-bucket hit rate over `hit`/`miss` only (neutral/unresolved excluded), and enforces a **sample-size guardrail: `hit_rate=None` when resolved_count < 3** (UI must render "n=N (need 3+)"). The auto-summary picks the largest claimed-vs-actual gap ≥5pp and emits exactly the website's line: *"Your {claimed}% theses resolved at {actual}% (n={N})."*
- **Auto-resolution (corrects the brief).** `auto_resolution.py::resolve_open_decisions` resolves open structured decisions against real prices using the *same* `score_forecast` as the backtest, with the analyst's own `threshold_pct` as the deadband, touching only `resolved_direction IS NULL` rows (never overwrites a manual mark). Exposed at `POST /v1/journal/auto-resolve`. **It is asset-class-agnostic.** The genuine gap is that it is **unscheduled** — nothing triggers it on a cron, so in practice resolution still waits on a manual endpoint call.
- **Coaching & desk view.** `dq_coach.py` produces per-bucket pattern coaching (LLM, confidence derived from resolved-count threshold); `desk_calibration.py` + `model_diagnostics.py` extend toward desk-level Brier and per-model bias/drift. `devils_advocate` / `critique_thesis` adversarial features are wired (tests + a `DevilsAdvocateDrawer` component exist).

**Gaps:** cold-start (weeks before a bucket fills); auto-resolution unscheduled; evidence-weight captured but not yet analyzed; single-user (no per-analyst desk ledger until Clerk lands).

---

## 8. The LLM layer · **REAL, single-shot**

- **Nine tasks**, routed per-task (`llm_routing.py`): fast tasks (summarize_market, extract_event, extract_prediction) → **Haiku 4.5**; reasoning tasks → **Sonnet 4.6**; escalate to **Opus 4.7** when `narrate_scenario` shocks ≥4, or `review_journal_entry` confidence ≥80, or `critique_thesis`/`devils_advocate` conviction ≥80. Per-task env overrides supported.
- **Execution** (`llm_client.py`): `llm_mode` defaults to **`fake`** (deterministic canned responses, all of which pass the forbidden-phrase scan); `real` mode calls the Anthropic SDK with **prompt caching on the persona `system_blocks`** and **falls back to canned on any exception** (graceful degradation). An in-memory response cache keyed by prompt hash also short-circuits repeats.
- **Safety enforcement** (`llm_explainer._call_with_safety_check`): scan output → if clean, return; if not, **retry once with a stricter appended instruction**; if still failing, **raise `SafetyViolation` and block**. This is the structural "can't lie about advice/certainty" property.
- **Limitations:** strictly **single-shot** — `call_llm` issues one `messages.create` with no `tools=`, no RAG, no agentic loop. The LLM cannot query the backtest/calibration substrate itself. The narrative **confidence envelope is hardcoded** `"medium"`/`"low"` (the one real residue of the brief's "hardcoded confidence" concern).

---

## 9. Data layer & ingestion · **PARTIAL**

- **Real adapters exist for all five domains:** `energy/eia.py` + `eia_petroleum.py`, `market/yahoo_delayed.py` + `nasdaq.py`, `weather/nws.py` (+ population-weighted regions), `positioning/cftc.py`, `news/rss.py` + `newsapi.py` — each with a `mock_*` sibling and a `null_energy` for metals. A shared `_http.py` wraps `httpx` with backoff + jitter, and a protocol-parity contract test (`tests/adapters/test_protocol_parity.py`) keeps mock/real output shapes identical. Real-adapter tests (`test_eia_real.py`, `test_cftc_real.py`, `test_nws_real.py`, `test_yahoo_delayed.py`) exist.
- **But the default is mock.** `settings.adapter_market/energy/weather/positioning/news` all default to `"mock"`; real adapters are env-opt-in and fall back to mock when their key is missing. Only `eia_api_key` is documented as set + validated live in the deployed `.env` (the latest commit). **So "live data across 5 domains" is a deployment-configuration claim, not a repo default** — and only one domain (EIA) is confirmed live from the evidence available.
- **Persistence (corrects the brief).** `price_backfill.py` fetches real Yahoo daily OHLC and **upserts into the `price_bars` Timescale hypertable** (PK `(ts, contract_id, resolution)`, `source="yahoo_delayed"`), with `replace_mock=True` retiring NG's seeded GBM only after a successful real fetch. So the hypertables are **not** unfed-by-design; real bars land in them. What can't be confirmed from source alone is *how much* real history each contract carries in the deployed DB. Fundamentals/COT/weather adapters appear to be read-through (not yet persisted to their hypertables), consistent with the brief.
- **"Real-time" caveat stands:** Yahoo is 15-min delayed; fundamentals are weekly; no tick/order-book feed.

---

## 10. Frontend · **REAL**

- **8 screens** (`app/(app)/`): dashboard, chart, signals, scenarios, journal, calibration, paper, admin (+ a marketing landing `page.tsx`).
- **103 non-test components** (the "~149" figure includes the 74 web test files and Storybook stories). Tailwind with enforced design tokens; Recharts for analytics, Lightweight Charts for candlesticks; deep chart stack (indicators, S/R, candlestick + chart patterns, seasonality, drawing tools). TanStack Query for REST, a single multiplexed WebSocket via `lib/realtime.ts`.
- **Honesty fixes are in the UI:** Signal Lab now shows "Agreement: N of M" (not a hit-rate), an always-visible "no proven directional edge at this horizon" note, and an Expected Range strip with live coverage/correlation readout. The `Range · Direction · Both` view selector + EWMA/log-HAR estimator selector shipped (Phase 30d, on a not-yet-promoted branch per `HANDOFF.md`).
- **Known polish gaps (from docs):** scenario/paper forms are plain inputs; admin is largely static tables; the `packages/contracts` types aren't actually imported by the app (hand-written `lib/api.ts` instead), and that package's types had drifted — a real-but-low-severity divergence.

---

## 11. Security, safety & compliance posture · **PARTIAL**

- **Strengths:** the safety/forbidden-phrase architecture (§8) is a genuine compliance-adjacent control; secrets are env-only with mock fallback and a "never log API keys" rule; CORS is configurable; DB TLS is supported (`database_ssl` / `sslmode=require`); Clerk JWTs would be verified via public JWKS (no secret key stored).
- **Gaps for an institutional buyer:** **no enforced auth by default** (anonymous, `user_id` NULL) → **no multi-tenancy, no per-user data isolation, no access control, no audit log of who-saw-what**. For a fund-facing "decision ledger / compliance" story (an explicit roadmap pillar), this is the critical missing layer. Sentry is a disabled stub; no OpenTelemetry/metrics. These are correctly scoped as out-of-MVP, but they are the gating work for any enterprise/regulatory pitch.

---

## 12. Testing, CI & quality · **REAL**

- **Coverage:** 75 backend test files + 74 web test files. Project docs report ~906 backend / ~402 web *cases* passing at the current phase; I verified the files and their content (not executed here). The high-value tests are present and substantive: the look-ahead/cheating-model proof, the walk-forward calibration harnesses (`test_vol_range.py`, `test_ensemble_calibration.py`), the forbidden-phrase eval and routing/caching tests, adapter protocol-parity, OpenAPI round-trip, migrations-run, and Playwright e2e happy paths.
- **CI** (`.github/workflows/ci.yml`, on push/PR to main/master): Python **ruff** + **mypy --strict** + **pytest**, web **biome** + typecheck + vitest. `mypy --strict` on the whole `src` package is a strong signal for a four-week-old codebase.
- **Caveat:** the real-data validation harnesses (`validate_vol_real.py`, `validate_direction_real.py`) are **manual** (live network → not hermetic), so the headline real-OOS numbers are reproducible-on-demand but **not enforced in CI**. The synthetic locks that *are* in CI guard the methodology, not the real-data result.


---

## 13. Production readiness & scalability · **PARTIAL (demo-grade)**

- **Today:** designed for a single VM / managed-Postgres / managed-Redis demo deployment (`railway.json` present; Vercel + managed PG/Redis described). Single-user, mock-default, fake-LLM-default — i.e. it runs and demos with zero external keys, which is excellent for a pitch and honest for a prototype.
- **What breaks at scale:**
  - **No tenancy/auth** → cannot onboard a second user safely without finishing Clerk (PR #7) and adding row-level scoping (every table carries `user_id`, currently NULL).
  - **Auto-resolution unscheduled** → the calibration loop doesn't advance without a manual trigger; needs a worker/cron (the worker tier is described in `ARCHITECTURE.md` but the scheduled jobs aren't wired).
  - **In-memory LLM/response caches** are per-process → won't share across replicas; Redis is the intended backbone but the LLM cache is local.
  - **Backtest is O(days) sequential** with per-day queries → fine for demo windows, not for large-scale or many-symbol sweeps; single-front-month means no true multi-year continuous backtest yet.
  - **`packages/contracts` drift is not CI-enforced** → frontend/backend type divergence can ship silently (mitigated only because the app hand-writes its client).

---

## 14. Technical risk register & remediation roadmap

Ordered by diligence severity (likelihood a sharp reviewer finds it × damage if unaddressed).

| Risk | Severity | Effort | Remediation |
|---|---|---|---|
| **R1 — Website/demo claims outrun code** (Prophet listed; directional "explainable forecast" hero; "live" data with mock defaults) | **High** | **S** | Update the website model list (drop Prophet, name Holt + the honest composite + logreg); lead the forecast story with the *range* edge, not direction; either flip the demo env to real adapters or relabel as "delayed/seeded showcase." Pure copy + config. |
| **R2 — logreg/factor directional output is unvalidated on real features** | **High** | **L** | The documented "big rock": ingest real historical COT (CFTC, free) + EIA storage, persist to their hypertables, and re-run the existing harnesses on real features→price. Until then, keep directional output explicitly unproven. |
| **R3 — No auth/tenancy/audit** (blocks any enterprise/compliance pitch) | **High** | **M** | Finish Clerk (PR #7); scope every query by `user_id`; add an immutable decision-audit view. This is the gate for the "decision ledger" pillar. |
| **R4 — LLM narrative confidence hardcoded "medium"** | **Med** | **S** | Derive the envelope confidence from ensemble agreement + vol-band width (the inputs already exist) so the one remaining "hardcoded confidence" criticism dies. |
| **R5 — Auto-resolution unscheduled** | **Med** | **S** | Wire a daily worker to call `resolve_open_decisions` (machinery already built); this is what makes the calibration ledger *compound* without manual intervention. |
| **R6 — Single front-month backtest (no rollover)** | **Med** | **M** | Multi-contract continuous-series stitching so long-horizon backtests are methodologically defensible. |
| **R7 — Real-data validation not in CI** | **Low-Med** | **M** | Add a scheduled (non-PR-blocking) CI job that runs the real-OOS harnesses and posts the coverage/correlation numbers, so the headline edge is continuously re-verified, not a point-in-time claim. |
| **R8 — Contracts type drift not enforced** | **Low** | **S** | Add a hermetic OpenAPI-dump-and-diff CI step (already identified in `HANDOFF.md`). |

**Pre-diligence priority (do these three first):** R1 (cheap, removes the most obvious "gotcha"), R4 (kills the last hardcoded-confidence criticism), and R5 (makes the moat visibly compound). R2 and R3 are the larger bets that convert "honest prototype" into "defensible product."

---

## 15. Appendices

**A. Inventory (audited commit `2c5daad`)**
- Languages: 255 `.py`, 186 `.tsx`, 53 `.ts`, 36 `.md`. 239 commits (2026-05-10 → 06-07).
- API: 57 endpoints / 23 routers. Web: 8 screens / 103 components. Tests: 75 backend + 74 web files.
- Migrations (9): `001` extensions/enums, `002` relational, `003` Timescale hypertables, `004` retention/compression, `005` theses, `006` journal calibration columns, `007` decision capture + `007` users, `008` auto-resolution, `009` merge heads.

**B. Backend dependencies (core):** fastapi, uvicorn, pydantic(+settings), sqlalchemy[asyncio], asyncpg, alembic, redis, httpx, tenacity, orjson, **numpy, pandas**, anthropic, reportlab, pyjwt, cryptography. *Optional/uninstalled:* prophet, xgboost. *Dev:* pytest(+asyncio), ruff, mypy, testcontainers[postgres].

**C. Config flags that decide behavior** (`apps/api/src/settings.py`): `llm_mode` (default `fake`), `llm_model_fast/smart/premium` (Haiku 4.5 / Sonnet 4.6 / Opus 4.7), `adapter_market/energy/weather/positioning/news` (default `mock`), `anthropic_api_key`, `eia_api_key`, `clerk_publishable_key` (empty → anonymous), `database_ssl`, Redis TTLs.

**D. Authoritative docs to read in order:** `MODEL_DILIGENCE.md` (provenance ledger — read first), `HANDOFF.md` (current state), `DILIGENCE_AND_30C_PLAN.md`, `SCHEMA.md`, `API_CONTRACTS.md`, `AI_BEHAVIOR.md`. Treat `ARCHITECTURE.md` model/backtest sections and the public website as **stale**.

**E. What I could not verify from source alone:** actual deployed adapter config (which domains run real vs mock in prod); real-history depth per contract in the deployed `price_bars`; live test-suite execution and exact pass counts (reported from docs); the live demo's runtime behavior.

---

## 16. Summary for the engineering copilot

Paste-ready starting context for planning:

> **Goldeneye/NGTI audit, commit `2c5daad`.** The engineering is real and unusually honest. Verified REAL: look-ahead-safe backtest with a working cheating-model proof (`backtest.py` + `test_backtest_lookahead.py`); walk-forward vol/range engine (EWMA + log-HAR, empirical fat-tail bands) validated OOS on ~10y real data (`vol_range.py`); conviction-snapshot calibration engine with n≥3 guardrail and the live "Your X% theses resolved at Y%" line (`calibration.py`); auto-resolution against real prices (`auto_resolution.py`, but **unscheduled**); structurally-enforced safety layer with retry-then-block (`safety.py` + `llm_explainer.py`); 3-tier LLM routing + persona caching + graceful degradation (single-shot, `fake` by default); real adapters for all 5 domains (mock by default); real Yahoo price backfill that **persists to the Timescale hypertable** (`price_backfill.py`). Honest predictive reality: **no real OOS directional edge** (confirmed on real data); the one validated edge is vol/range, which is table-stakes — so the moat is honest calibration + the compounding ledger, not alpha. logreg/factor remain **unvalidated** on real features.
>
> **Do, in order:** (1) **R1 copy/config** — fix the website (drop Prophet, lead with range not direction, relabel data) and decide the demo's real-vs-mock posture; (2) **R4** — derive LLM-envelope confidence from ensemble agreement + band width to retire the last "hardcoded confidence" criticism; (3) **R5** — schedule a daily worker calling `resolve_open_decisions` so calibration compounds automatically; (4) **R3** — finish Clerk (PR #7) + per-`user_id` scoping + an immutable decision-audit view to unlock the enterprise/compliance ledger; (5) **R2** (the big rock) — ingest real historical COT + EIA, persist to hypertables, re-run the existing harnesses on real features→price to move logreg/factor out of "unvalidated"; (6) R6 multi-contract backtest, R7 real-OOS validation as a scheduled CI job, R8 OpenAPI dump-and-diff CI. Keep the honest-gate culture: no predictive/calibration claim ships without provenance per `MODEL_DILIGENCE.md`.

*End of report.*
