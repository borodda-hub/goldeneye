# docs/HANDOFF.md — Session handoff & next-steps plan

_Last updated: 2026-06-07. Read this first to pick up where we left off._

## TL;DR

Two strategic arcs landed since the charting overhaul: **Phase 26 — Model
Intelligence v2** (complete, promoted) and **Phase 30 — Volatility & Range
Engine** (30a complete + hardened, promoted). The honest finding from 26 —
**no reliable out-of-sample _directional_ edge at 1d/1w/1m** — reframed the
product, and 30 found the platform's first genuine, calibrated edge in the
opposite place: **volatility/range** (80% interval coverage holds across 6
commodities with zero tuning, now locked as regression tests). A WS4 pass
synced the stale source-of-truth docs to code reality. On 2026-06-07 that
vol/range edge was **validated out-of-sample on ~10y of REAL data across all
six commodities** (6/6 pass the 80% gate; forward-vol correlation 0.44–0.59,
*stronger* than synthetic) — it survived an adversarial test built to break it,
so it is a real edge, not a seed artifact. Caveats that stand: the *directional*
"no edge" finding is still synthetic-only; the 95% band is confirmed
miscalibrated on real data too (fat tails → 30c); and it's a table-stakes vol
fact, so the moat is honest calibration, not a proprietary signal.

Everything is in sync: `master == develop == origin/master == origin/develop
== 3d63888`, clean working tree. **895 backend tests** passing; web tests
green. `pnpm health` green end-to-end.

The single-sentence product story has correctly pivoted from "we predict
price" to **"we calibrate uncertainty honestly."**

The current roadmap source of truth is **`docs/BUILD_ROADMAP.md`** (this file
defers to it for phase detail).

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

- **Sync:** `master == develop == origin/* == 3d63888`. Nothing un-promoted.
  Clean working tree.
- **Tests:** backend **895** passing; web green; `pnpm health` GREEN end-to-end
  (ruff → mypy → pytest → web lint → typecheck → test).
- **Models:** 4 voters (MA · holt_trend · factor_composite · logreg) +
  `volatility_regime` as context. Calibration-weighted ensemble. `factor_learned`
  benched.
- **Forecast surfaces:** `GET /v1/forecast/range` (calibrated vol band, live);
  Signal Lab shows the honest Agreement framing + Expected Range strip.
- **Honest posture, codified:** the directional "no OOS edge" and the vol/range
  "real calibrated edge" are both *tested claims*, not narrative.

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

The owner-requested **full project audit + plan reassessment** (agenda in
`docs/BUILD_ROADMAP.md`) is the formal next decision point. The recommended
build, if proceeding, continues Phase 30 — the one place with a real edge.

### Recommended first move: Phase 30b — Better estimator
Flip the out-of-sample point-forecast R² positive while keeping the calibrated
band.
- EWMA → recalibrated-EWMA → **HAR-RV** (pure-numpy OLS on daily/weekly/monthly
  realized vol — no new deps, preferred) → optional GARCH-lite (flag `arch` as
  an *optional* dep, not required).
- Same walk-forward acceptance test as 30a.
- **Gate:** OOS R² > 0 vs the mean benchmark AND beats persistence; or keep the
  simplest *calibrated* estimator and say so (same honest-gate culture as
  26b/26c). Clean, self-contained, no-new-deps increment.

### Then, in Phase 30 order
- **30c — Fat tails + regime.** Student-t / empirical quantiles to pull 95%
  coverage from ~90% to nominal; regime-conditional vol reusing the
  `volatility_regime` context. Gate: 95% coverage within [93, 97]%
  walk-forward.
- **30d — Mode / views.** Range · Direction · Both selector; estimator selector
  within vol mode (EWMA · HAR-RV · GARCH-lite). **Guardrail:** every mode carries
  its own live walk-forward calibration readout so users can't cherry-pick around
  a bad track record. This is the UX payoff of the honesty stance.

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
