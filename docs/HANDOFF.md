# docs/HANDOFF.md — Session handoff & next-steps plan

_Last updated: 2026-06-08. Read this first to pick up where we left off._

## TL;DR

Two strategic arcs landed since the charting overhaul: **Phase 26 — Model
Intelligence v2** (complete, promoted) and **Phase 30 — Volatility & Range
Engine** (30a + 30b + 30c complete, **promoted to live**). The honest finding from 26 —
**no reliable out-of-sample _directional_ edge at 1d/1w/1m** — reframed the
product, and 30 found the platform's first genuine, calibrated edge in the
opposite place: **volatility/range** (80% interval coverage holds across 6
commodities with zero tuning, now locked as regression tests). A WS4 pass
synced the stale source-of-truth docs to code reality.

**2026-06-07 diligence wrap-up (complete).** A code-grounded audit found that every
predictive claim rested on the synthetic seed. We closed it:
- **Vol/range edge — validated out-of-sample on ~10y REAL data, 6/6 commodities**
  (80% coverage 78–81%; forward-vol corr 0.44–0.59, *stronger* than synthetic). It
  survived an adversarial test built to break it → real edge, not a seed artifact.
- **Phase 30c shipped** — empirical fat-tail band quantiles replaced normal-z; **95%
  coverage now reaches nominal on real data (93–95%)**, locked in tests.
- **Direction tested on real data — no edge, confirmed.** Price-only models
  (`moving_average_directional`, `holt_trend`) score ≈45–57% decisive across 6
  commodities, below a drift-aware naive baseline in all 36 cells; no confidence
  gradient. Phase 26's finding holds on real data, not just synthetic.
- **`logreg`/`factor` stay unvalidated** (need real COT/EIA → deferred Phase 31).
- Provenance now governed by `docs/MODEL_DILIGENCE.md`. The one real edge is
  vol/range; it's table-stakes, so the moat is honest calibration, not alpha.

**2026-06-08 — Phase 30d shipped + promoted; Phase 31 planned.** Phase 30d (the
visible payoff of the vol/range arc) is now **live on master**: Range·Direction·Both
view selector + EWMA·log-HAR estimator selector in Signal Lab, and **log-HAR is now
the default** estimator (perf pass + skill-neutral real-OOS re-validation). The
`packages/contracts` drift was resynced to the live OpenAPI schema in a dedicated
chore commit. A detailed **Phase 31 plan** (real COT/EIA feature-history ingestion →
validate `factor_composite`/`logreg` on real features) is drafted in
`docs/PHASE_31_PLAN.md`; **`EIA_API_KEY` is resolved** (set in `apps/api/.env`,
validated live against EIA v2). Owner is mulling the 31 scope call (31a+31b first, or
the full arc).

Everything is in sync: `master == develop == origin/master == origin/develop
== 2c5daad`, clean working tree, **nothing un-promoted, nothing unpushed** (verified
2026-06-08). **906 backend + 402 web tests** passing; `pnpm health` green end-to-end.

The single-sentence product story has correctly pivoted from "we predict
price" to **"we calibrate uncertainty honestly."**

The current roadmap source of truth is **`docs/BUILD_ROADMAP.md`** (this file
defers to it for phase detail); the next-build detail is **`docs/PHASE_31_PLAN.md`**.

---

## What shipped since the last handoff (Phases 26 → 30a)

### Phase 26 — Model Intelligence v2 ✅ COMPLETE + promoted to live
Turned "5 models, 1 genuinely trained" into "4 distinct honest models + the
machinery to see when they're wrong." Full detail in `docs/BUILD_ROADMAP.md`.
- **26a (`847bcf2`)** — model diagnostics: per-model directional bias,
  regime-conditional accuracy, Brier decomposition (calibration vs sharpness),
  logreg feature-importance drift. `GET /v1/backtest/diagnostics` + **Model
  Health** card on `/calibration`.
- **26b (`c251a49`)** — 4-voter lineup: added `holt_trend` (pure-numpy
  Holt/AR, replaces the Prophet-stub slot); demoted `volatility_regime` to
  shared **context** (stamped on every row, not a directional voter). Lineup =
  MA + holt_trend + factor_composite + logreg. **Honest gate outcome:** the
  new `factor_learned` did NOT beat hand-set `factor_composite` on OOS Brier
  (0.278 vs 0.259, ~1 SE tie, mildly overconfident) → kept the honest baseline;
  `factor_learned` is **benched** (code + tests retained).
- **26c (`35db519`)** — calibration-weighted ensemble: each vote scaled by
  inverse-Brier (`model_weights_from_brier`, clamped [0.4, 2.0]), wired into all
  5 live call sites. **Gate NOT met OOS at any horizon** — the walk-forward
  harness caught the in-sample 1w/1m gradients as overfitting. **Shipped
  reframed** as down-weighting demonstrably-miscalibrated models (not a
  calibrated confidence claim). The walk-forward harness is **locked as a
  permanent test** (`tests/test_ensemble_calibration.py`).
- **Phase 26 honest headline:** no reliable OOS directional confidence gradient
  at 1d/1w/1m; the system correctly declines to manufacture one. The durable
  assets are the *diagnostics* + the *walk-forward honesty harness*, not a
  directional edge.

### Phase 30 — Volatility & Range Engine ✅ 30a shipped + hardened, promoted
The edge has an address. A walk-forward probe found EWMA-vol forecasts correlate
**+0.246** with realized forward 5d vol (~3.7 SE) and deliver **80% interval
coverage of ~79.6/80.1%** at 5d/10d with zero tuning — the platform's first
genuine, calibrated edge.
- **30a backend (`53266b7`)** — `services/models/vol_range.py`: walk-forward
  EWMA vol forecaster emitting σ + 80%/95% bands per horizon; `GET
  /v1/forecast/range` (safety-wrapped); `walk_forward_coverage` locked as a
  calibration test. Multi-commodity confirmed (80%/1W coverage 76–84% across
  NG/CL/HO/RB/GC/SI).
- **30a hardening (`b487f44`)** — moved the claims out of roadmap narrative and
  into **code as locked regressions**: `forecast_vol_correlation()` (walk-forward
  corr of forecast σ vs realized fwd vol), `walk_forward_coverage()` now reports
  `n_eff` (non-overlapping window count) so the overlap estimate isn't over-read.
  `/v1/forecast/range` surfaces `forward_vol_corr` + `n_eff` + the honest
  "point-forecast vol level is not reliable OOS — use the band" caveat. Measured
  on seeded NG: cov80 ~0.80, fwd-vol corr 0.30–0.42 (the probe's 0.246 was
  conservative).
- **30a real-data validation (2026-06-07, `seeds/validate_vol_real.py`)** — the
  diligence step that was missing: the seed result was partly circular (vol
  clustering is injected by construction; EWMA detects it). The harness fetches
  ~10y real daily history for all six commodities through the production Yahoo
  path and runs the **unchanged locked functions** on real returns. Result:
  **6/6 pass the [77,83]% 80% gate at 1w** (NG 81.2 · CL 81.2 · HO 79.0 · RB 81.3
  · GC 79.5 · SI 79.3, n_eff ≈ 497), and **forward-vol corr is stronger on real
  data** (0.44–0.59). The vol/range edge is real and validated OOS. Manual
  diagnostic only (needs live network → can't be a hermetic CI test); re-run with
  `uv run --directory apps/api python -m seeds.validate_vol_real`.
- **30a frontend (`e6d946c`, Signal Lab honesty fix)** — kept the engaging
  directional hero + LLM narration but fixed the one false truth-claim:
  "Confidence: HIGH/MED/LOW" → **"Agreement: N of M"** (it is a vote-agreement
  measure, not a realized hit-rate); un-buried the always-visible "No proven
  directional edge at this 1-day horizon (walk-forward) — read as a view, not a
  probability" note. New **ExpectedRange** strip below the hero: the calibrated
  80% $-band + daily vol + live walk-forward coverage/correlation readout, "range
  only — no directional claim." Auto-height (never `h-full` — the prior attempt's
  bug). Renders nothing until the endpoint answers, so a not-yet-deployed backend
  can't break the page.

### Phase 30c — Fat tails ✅ + Phase 30b — log-HAR estimator ✅ (promoted `6f71827`)
- **30c (`5b0726d`)** — band multipliers became **empirical quantiles of past realized
  standardized moves** (walk-forward, look-ahead-safe; normal-z fallback while thin), so the
  95% band reaches nominal on real fat tails. Real-OOS 95% coverage 93–95% (was 92–94%); 80%
  holds 78–81%. Locked in `tests/test_vol_range.py`.
- **30b (`6f71827`)** — opt-in **log-HAR** vol estimator (`estimator=har_log` on `predict()` +
  `GET /v1/forecast/range`). Walk-forward HAR-RV (Corsi 2009) on **log** realized variance with
  a causal Jensen back-transform. It **beat the EWMA incumbent on real OOS point-forecast R²**
  (mean +0.25 vs +0.20 @1w, +0.21 vs +0.16 @1m across 6 commodities; wins NG decisively) and
  fixed the raw-variance HAR's vol-explosion blow-up (real CL R² −1.06 → +0.14). **Default stays
  EWMA** — opt-in only, so promotion was behavior-preserving. Raw-variance HAR **benched** (code
  + tests retained) per the honest-gate culture. `estimator_skill()` is the acceptance harness;
  the real-OOS verdict is re-runnable via `seeds/validate_estimator_30b.py`. Bands/coverage
  recompute against the chosen estimator → calibration preserved (verified live: cov80 ~0.81 for
  both; `?estimator=har_log` returns the wider log-HAR band). Provenance in `MODEL_DILIGENCE.md`.

### WS4 — trust hygiene ✅ (`3d63888`)
Synced stale source-of-truth docs to code:
- **SCHEMA.md** — added 3 tables missing since Phase 12/14 (theses, users,
  user_settings) + the 8 `user_decision_journals` calibration columns + a
  current-head (009) note.
- **AI_BEHAVIOR.md** — fixed the §disclaimer string to match
  `services/safety.py` ("NGTI … prototype" → "Goldeneye … terminal"); it's a
  contractual UI string.
- **INNOVATION_BRIEF.md** — corrected the moat: auto-resolution is **BUILT**
  (`auto_resolution.py` + `POST /v1/journal/auto-resolve`), not manual; the real
  gap is it's **unscheduled**.

---

## Current state

- **Sync:** `master == develop == origin/* == 2c5daad`. Nothing un-promoted,
  nothing unpushed. Clean working tree, no stashes.
- **Tests:** backend **906** passing; web **402** green; `pnpm health` GREEN
  end-to-end (ruff → mypy → pytest → web lint → typecheck → test).
- **Models:** 4 voters (MA · holt_trend · factor_composite · logreg) +
  `volatility_regime` as context. Calibration-weighted ensemble. `factor_learned`
  + raw-variance HAR benched.
- **Forecast surfaces:** `GET /v1/forecast/range` (calibrated vol band, live;
  **`estimator=har_log` is now the default** | `ewma` one-click opt-out — 30d);
  Signal Lab has the **Range·Direction·Both** view selector + the EWMA·log-HAR
  estimator selector, the honest Agreement framing, and the Expected Range strip.
- **Vol estimators:** log-HAR (**default** — better real-OOS point forecast) +
  EWMA (opt-out). 30d perf pass: HAR serve cost 21.4ms → 14.9ms; re-validation
  confirmed the periodic-refit perf pass is skill-neutral.
- **Honest posture, codified:** the directional "no OOS edge" and the vol/range
  "real calibrated edge" are both *tested claims*, not narrative; provenance per
  `docs/MODEL_DILIGENCE.md`.

### Key architecture notes (vol/range engine)
- **`services/models/vol_range.py`** — pure-numpy walk-forward EWMA vol
  forecaster. `_wf_sigma()` helper; `walk_forward_coverage()` (reports `n_eff`);
  `forecast_vol_correlation()`. No new deps. The acceptance test is
  walk-forward *coverage* (interval calibration), mirroring the
  `ensemble_calibration` honesty harness from 26c.
- **Honesty harness pattern** (`services/ensemble_calibration.py` +
  `tests/test_ensemble_calibration.py`) is the template for every predictive
  claim: weights/forecasts from resolved priors only, no look-ahead at serve
  time, in-sample vs out-of-sample always separated. Reuse it for 30b/30c.
- **Model registry / ensemble**: `volatility_regime` is context, not a voter;
  `compute_ensemble(..., model_weights=...)` takes per-model inverse-Brier
  weights; `model_weights_for(session, instrument_id, horizon)` derives them from
  persisted-backtest calibration (full-history at serve time, no look-ahead).

### Operational gotchas (Windows dev) — still current
- **uvicorn `--reload` (WatchFiles) intermittently stops detecting changes.**
  After adding new backend files the running server often won't pick them up —
  restart the stack.
- **`TaskStop` on `pnpm dev` orphans the uvicorn worker children** (they hold
  port 8000 via an inherited socket). Clean restart: `taskkill /F` the
  multiprocessing-spawn `python.exe` workers + any listeners on 8000/3000/3001,
  confirm ports free, then `pnpm dev`.
- **Re-seed** after a schema/seed change:
  `uv run --directory apps/api python -m seeds.demo --fresh`
  (use `-m seeds.demo`, NOT `-m apps.api.seeds.demo`).
- **Contract regen** (after a response-model change): with the dev server up,
  `curl -s http://localhost:8000/openapi.json -o packages/contracts/openapi.json
  && pnpm contracts:gen:local`.
- **Playwright** chromium is installed. Set `localStorage
  goldeneye:walkthrough-completed = "1"` in `addInitScript` to suppress the
  first-run tour overlay.
- **Lesson banked (30a frontend):** *run the app and look before placing any
  UI.* The Expected Range card shipped 3× with an `h-full` bug before visual
  verification caught it. Frontend + backend that depend on each other promote to
  live together.

---

## Next-steps plan (start-fresh-ready)

**All of Phase 30 (30a–30d) is shipped and promoted to live.** The recommended
next build is **Phase 31 — real COT/EIA feature-history ingestion** (detailed plan
in `docs/PHASE_31_PLAN.md`): the one structural diligence gap left. It validates
`factor_composite`/`logreg` on real point-in-time features→price — closing the
"we think these models work" vs "we checked" gap. Most-likely honest outcome is
"still no directional edge, now proven on real data," which is itself a diligence
asset; a genuine edge is the upside. **`EIA_API_KEY` is resolved**; the
look-ahead-safe point-in-time machinery already exists, so 31a+31b ≈ 1.5–2 days.
**Open decision before building:** ship 31a+31b first, or commit to the full
31a→31c arc up front (owner mulling).

### Phase 30d — Mode / views + log-HAR default ✅ COMPLETE + PROMOTED TO LIVE (`2c5daad`)
The visible payoff of the vol/range arc **plus** the log-HAR default-swap. Both halves shipped
(owner split the work frontend-first within one session).
- ✅ **Range · Direction · Both** view selector in Signal Lab (`SignalViewControls.tsx` +
  reusable `Segmented.tsx`, house segmented-control idiom). Default Both (range primary);
  Range hides the directional hero; Direction hides the range *and* the estimator selector —
  never co-equal.
- ✅ **Estimator selector (EWMA · log-HAR)** within vol views; `useRangeForecast` now takes an
  `estimator` arg → `?estimator=`. `ExpectedRange` badges the active estimator; band + coverage
  recompute live (verified EWMA ±6.6% → log-HAR ±12.4% on NG 1w).
- ✅ Guardrail intact: range carries its live coverage/corr readout; direction keeps its "no
  proven edge" caveat. **Visual-verified** (Playwright, all four states — ran the app and
  looked, per the banked `h-full` lesson). Web lane green: typecheck + biome + **402 vitest**
  (+4 new); no backend change this session (endpoint already supported `estimator`).
- ✅ **log-HAR is now the DEFAULT** — endpoint `Query(default="har_log")` + the frontend
  defaults (`useRangeForecast`/`ExpectedRange`/`SignalsShell`). EWMA is a one-click opt-out.
  Pure-function `estimator=` defaults stay `"ewma"` so the EWMA calibration locks stay honest;
  the user-facing default lives at the endpoint + UI.
- ✅ **Perf pass:** `_har_rv_sigma` now refits the OLS every `_HAR_REFIT=5` steps (absolute-index
  schedule → prefix-invariant, look-ahead-safe). Serve cost predict+cov+corr **21.4ms → 14.9ms**.
- ✅ **Re-validated real-OOS — skill-NEUTRAL.** A cadence sweep on ~10y real data proved
  cadence-1 (per-step) ≈ cadence-5: log-HAR beats EWMA **5/6 @1w, 4/6 @1m**, mean +0.05 R²
  (matches the 30b headline). RB @1w / CL+RB @1m lose marginally — the *same* losses that exist
  per-step, not a cadence artifact; both estimators stay positive-R² there. Honest: log-HAR is
  the better default *on the majority*; the band is coverage-validated under either estimator.
- ✅ Gate: full `pnpm health` green — backend **906** (+2 new endpoint tests: default-is-har_log
  + ewma-opt-out), web 402, ruff/mypy clean.
- ✅ **Contract regen done as a separate `chore/contracts-resync` commit** (kept out of the 30d
  logic commits on purpose). `packages/contracts` had drifted across multiple phases (its
  `openapi.json` predated the 30a/30b forecast endpoints) — regenerated from the live schema
  (+581 lines of genuinely-missing endpoint types, incl. `forecast/range` + the `estimator`
  param with `default:"har_log"`); the regenerated `src/index.ts` compiles clean (tsc strict).
  Note: the package is **not imported by app code** (web uses hand-written `lib/api.ts`), and its
  `typecheck` script has no local `tsc` — the pre-existing reason drift was never CI-enforced
  (a hermetic OpenAPI-dump-and-diff CI step would be the durable fix; deferred).
- **Promotion:** ✅ **promoted to live 2026-06-08.** Frontend + backend shipped together and
  fast-forwarded into `master` (`32e85bf` backend + `48b37ff` frontend); the contracts resync
  landed as a follow-on chore (`fca8718`). `master == develop == origin == 2c5daad`.

### Optional 30 refinement (not a blocker)
- **30c regime-conditional vol** — condition the band on the `volatility_regime` context. The
  empirical-quantile fix already meets the coverage gate, so this is polish, not required.

### Phase 31 — Real COT/EIA feature-history ingestion 📋 RECOMMENDED NEXT (plan: `docs/PHASE_31_PLAN.md`)
The one structural diligence gap. Backtests/calibration currently run on the synthetic
seed, whose COT/storage are causally independent of price — so `factor_composite` and
`logreg_directional` are `unvalidated` in `MODEL_DILIGENCE.md`. **31a** ingests + persists
real historical COT (CFTC Socrata, no key) + EIA storage (`EIA_API_KEY` ✅ resolved) via the
already-built real adapters + new `*_range()` fetch + upsert repos + `seeds/backfill_features.py`.
**31b** runs the *unchanged locked backtest* on real point-in-time features (the
look-ahead-safe `_context_as_of()` machinery already exists) → an honest real-OOS verdict for
`factor_composite`. **31c** (conditional) adds alt-data features to `logreg`. Honest scope:
most-likely outcome is "no edge, now proven" — a diligence win either way. **Owner decision
pending:** 31a+31b first, or the full arc.

### Queued strategic phases (sequence TBD, all below 30)
- **Phase 27 — Concierge copilot.** Floating agentic assistant (navigates
  screens, explains any number, greets signed-in users by name). Reuses the LLM
  layer + `services/safety.py`. Resolve first: admin-only vs agentic-for-all.
- **Phase 28 — Accounts GA + Decision Ledger.** Finish Clerk (PR #7) → per-user
  saved theses → personal calibration track record. The auto-resolution
  machinery is already built (`auto_resolution.py` + `POST
  /v1/journal/auto-resolve`) — the gap is it's **unscheduled** + needs the ledger
  UI.
- **Phase 29 — Charting differentiators.** Spread/ratio charts (crack spread,
  gold/silver, CL/NG), multi-symbol compare, manual drawing tools (LWC v5
  primitives), pattern-credibility backtest (reuse the Phase-10 engine).

### Parallel quick-wins (fold in opportunistically)
- **Selective abstention** — emit a directional call only when a configuration
  has *historically* paid (extreme regime + strong agreement + catalyst),
  abstaining otherwise. Harvests residual directional edge honestly; natural
  follow-on to Phase 30.
- **Scenario fidelity** — make shocks move recent-return *momentum*, not just
  price level (fixes the lean-vs-ensemble divergence on the OPEC run).
- **Phase 19 cosmetic** — soften the "MOCK" label; lighter first-run walkthrough
  dim.

---

## Pointers
- `docs/BUILD_ROADMAP.md` — **current roadmap source of truth** (Phase 26 + 30
  detail, the audit agenda, gates).
- `docs/PHASE_31_PLAN.md` — **detailed next-build plan** (real COT/EIA ingestion →
  directional validation; 31a/31b/31c breakdown, gates, open scope question).
- `docs/CHARTING_ROADMAP.md` — the 6-phase charting plan + per-phase closeouts
  (Phases 20–25, now Phase 29 territory).
- `docs/INNOVATION_BRIEF.md` — code-grounded audit + "decision intelligence"
  repositioning (corrected in WS4).
- `~/.claude/.../memory/project_phase_state.md` — running phase state
  (auto-loaded each session).
- Source-of-truth docs synced in WS4: `SCHEMA.md`, `AI_BEHAVIOR.md`,
  `API_CONTRACTS.md` (documents `/v1/forecast/range`). Unchanged:
  `ARCHITECTURE.md`, `MOCK_DATA_SPEC.md`, `FRONTEND_COMPONENTS.md`,
  `DATA_SOURCES.md`.
