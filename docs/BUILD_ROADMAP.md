# Goldeneye — Build Roadmap (post-scenario-globe)

Status as of 2026-06-06. Organizing thesis: **decision intelligence, honest enough
to survive a capital firm's diligence.** Reviewed and prioritized with the owner.

## Decision (2026-06-06)
- **Open with Phase 26 — Model Intelligence v2.** Run the full phase (26a→26b→26c),
  promote, then reassess before picking the next phase. ✅ Done + promoted to live.
- **NEXT SESSION = full project audit + plan reassessment** (owner-requested
  2026-06-06). Before more building: audit real-vs-placeholder across the stack, review
  the Phase 26 honest findings (no OOS directional edge) + the vol/range edge, and
  re-prioritise the whole roadmap. Treat phases below 30 as provisional pending that
  reassessment.

### Audit agenda — to be discussed next session (note, 2026-06-06)
A structured pass (Claude can drive it on request):
1. **Real-vs-placeholder inventory across the stack** — what is genuinely built and
   working vs. mock/stub/hand-set, end to end (adapters, models, ensemble, LLM, UI).
2. **What the honest findings mean for the product's core claim** — reconcile the
   "decision intelligence" pitch with: no out-of-sample *directional* edge at any
   horizon (Phase 26), but a real, calibrated, multi-commodity *vol/range* edge.
3. **Re-rank everything against that** — 30b (HAR-RV), 30c (fat tails + regime), Brent
   parity, the deferred Expected Range card, and the queued Phase 27 (concierge) /
   28 (accounts + decision ledger) / 29 (charting differentiators).

## Why this first — current-state honest assessment
A code-grounded map of the forecasting layer found:
- **Only 1 of 5 models is genuinely trained** (`logreg_directional`, walk-forward
  safe). The other four are heuristics or hand-set rules:
  - `moving_average_directional` — SMA-20/50 cross (standard technical baseline).
  - `volatility_regime` — regime classifier; weak direction signal (only fires in
    elevated/crisis), always low confidence. Mostly used for its `vol_regime` output.
  - `prophet_trend` — real IF Prophet installed, **stub otherwise** (prod risk).
  - `factor_composite` — hand-set weights over storage+COT+momentum; its own code
    says "Not a trained model … every weight is hand-set, not learned."
- **Ensemble is an agreement-vote**, not a learned blend — confidence measures model
  *agreement*, not out-of-sample accuracy.
- **Calibration is surface-level**: Brier + hit-rate by confidence bucket + optional
  by-regime split. **No bias detection, no drift monitoring, no sharpness/calibration
  decomposition** — the system measures *whether* models work today, not *why* they
  might fail tomorrow.

This gap is exactly what diligence probes, so we close it first.

## Cross-cutting gates (every phase)
- `pnpm health` green (ruff → mypy → pytest → web lint → typecheck → test).
- Honest framing per `docs/AI_BEHAVIOR.md` — safety envelope on every model/LLM
  output; no certainty/advice language; in-sample vs out-of-sample always labeled.
- Any new/changed model is **look-ahead-safe by construction** and passes the
  existing cheating-model backtest proof.
- Docs updated in the same commit; two-lane flow (`feat/*` → `develop` → deliberate
  `master` promotion with the push guard + explicit owner sign-off).

---

## Phase 26 — Model Intelligence v2 (ACTIVE)
Turn "5 models, 1 real" into "4 genuinely distinct models, each with a clear driver,
plus the machinery to see when they're wrong."

### 26a — Model diagnostics & error/bias detection ✅ SHIPPED (`847bcf2`)
Build the X-ray before adding models.
- `services/model_diagnostics.py` + `GET /v1/backtest/diagnostics`:
  - per-model **directional bias** (chronically too bullish/bearish),
  - **regime-conditional accuracy** (e.g. logreg in crisis vol),
  - **Brier decomposition** (calibration vs sharpness, not just the scalar),
  - **feature-importance drift** for logreg over time.
- **Model Health** card on `/calibration`.
- **Gate:** diagnostics reproduce known truths on seeded data (e.g. vol_regime's
  weak direction signal shows as low sharpness); tests; honest in-sample labels.

### 26b — Four distinct, honest models ✅ SHIPPED (2026-06-06)
**Final shipped lineup:** ① `moving_average_directional` · ② `holt_trend` (NEW) ·
③ `factor_composite` (hand-set baseline **retained** — see gate outcome) ·
④ `logreg_directional`. `volatility_regime` demoted to shared context.

**26b gate outcome (the honest "say so"):** the NEW pure-numpy `factor_learned`
(walk-forward logistic + theory-signed alt-data tilt) was built and fully tested,
but on the re-seeded NG backtest it did **not** beat `factor_composite` on
out-of-sample Brier (0.278 vs 0.259 over n≈190–250 — a ~1 SE difference, i.e. a
statistical tie, with `factor_learned` mildly overconfident). Per the pre-registered
gate, we **kept the honest baseline**: `factor_composite` stays in the prod voter
slot; `factor_learned` is benched (code + tests retained) for 26c to revisit once the
ensemble is calibration-weighted (which would naturally down-weight an overconfident
voter). `holt_trend` ships as the always-on statistical slot (no baseline competitor;
it replaces the Prophet-stub prod slot). `pnpm health` backend green; re-seed verified.

Original lineup plan, grounded in 26a's diagnostics:
- ① **MA crossover** (`moving_average_directional`) — technical/momentum. 26a showed
  calib err 0.102 (overconfident) → recalibrate its confidence→prob mapping.
- ② **Statistical time-series** — NEW pure-numpy **Holt/AR linear-trend** model
  (`holt_trend`), always-on (Prophet stays an optional upgrade, not the prod slot).
- ③ **Learned multimodal factor** — NEW `factor_learned`: **pure-numpy** walk-forward
  logistic over [storage Δ, COT Δ, momentum], replacing `factor_composite`'s hand-set
  weights (no new deps; same approach as `logreg_directional`).
- ④ **Logistic (ML)** (`logreg_directional`) — real; 26a showed ~zero sharpness +
  momentum-importance drift → add the regime feature, address sharpness.
- **`volatility_regime` demoted to a CONTEXT input** — keeps its regime
  classification (feeds the other models + ensemble + diagnostics) but stops casting
  a directional vote. Lineup becomes 4 voters.

Build sequence: (1) `holt_trend` model + tests; (2) `factor_learned` model + tests
(walk-forward safe, alt-data-optional fallback); (3) refactor `model_registry.run_all`
to the 4 voters + vol_regime-as-context; (4) update `ensemble.compute_ensemble` to take
regime as explicit context (not a voter); (5) backtest `_predict`/`SUPPORTED_MODELS` +
`refresh_backtests` seed for the new model names; (6) re-seed backtests locally so
diagnostics/calibration show the new lineup; (7) update registry/ensemble tests.

- **Gate:** every model passes the look-ahead-safe backtest (cheating-model proof);
  `factor_learned` beats `factor_composite` on out-of-sample Brier, or we keep the
  honest baseline and say so; `pnpm health` green; re-seed verified.

### 26c — Ensemble v2 (calibration-weighted) ✅ SHIPPED (2026-06-06)
- **Shipped:** `compute_ensemble(..., model_weights=...)` — each model's vote is now
  scaled by `model_weights_from_brier` (inverse-Brier, normalised to mean 1.0, clamped
  [0.4, 2.0]). `model_weights_for(session, instrument_id, horizon)` derives the weights
  from the persisted-backtest calibration; wired into all live ensemble call sites
  (signals / dashboard / explain / signal_quality / scenarios). Live weights are
  full-history (no look-ahead at serve time).
- **Gate OUTCOME (the honest "say so"):** the literal gate — *high-confidence ensemble
  calls demonstrably hit more* — was **NOT met out-of-sample at any horizon.** A
  walk-forward harness (`services/ensemble_calibration.py`, weights from resolved
  priors only) found: **1d** flat (high 0.48 ≈ med 0.50, near-random); **1w** the clean
  in-sample gradient (0.58 > 0.52) *inverts* walk-forward (high 0.53 < med 0.69);
  **1m** in-sample 0.52 > 0.33 collapses to walk-forward 0.48 < 0.50 (high still below
  coin-flip). The in-sample gradients were **overfitting** — which is exactly what the
  harness exists to catch.
- **Decision (owner-approved):** ship the mechanism anyway, **reframed**: it is
  justified as *down-weighting demonstrably-miscalibrated models* (the MA model fires
  246 "high" calls at 42.7%), **not** as achieving a calibrated confidence gradient.
  The docstrings + the ensemble rationale string say so; ensemble confidence is
  relative, not a realized-hit-rate promise. The walk-forward harness is **locked as a
  permanent test** (`tests/test_ensemble_calibration.py`) so no future change can
  re-introduce an in-sample illusion unchallenged. `pnpm health` backend green.
- **Phase 26 honest headline:** across 1d/1w/1m the models have **no reliable
  out-of-sample directional confidence gradient**; the system correctly declines to
  manufacture one. The durable assets of Phase 26 are the *diagnostics* (26a) and this
  *walk-forward honesty harness*, not a predictive edge.

---

## Phase 30 — Volatility & Range Engine (RECOMMENDED NEXT — the edge has an address)

**Why this, why now.** Phase 26 proved daily *direction* is near-random (no OOS
gradient at 1d/1w/1m). A walk-forward vol-predictability probe (2026-06-06) found the
opposite for *volatility*: on NG front-month, EWMA-vol forecasts show **+0.246
correlation** with realized forward 5-day vol (~3.7 SE, real signal — mild
overlapping-window caveat) and **80% interval coverage of 79.6% / 80.1%** at 5d/10d
walk-forward, essentially perfect with zero tuning. Point-forecast OOS R² is negative
(crude EWMA *level* is over-reactive/mis-scaled) — but corr>0 means the information is
present and the level is *calibratable*, unlike direction where the signal was absent.
This is the platform's first genuine, calibrated edge. **Recommend sequencing this
before Phases 27–29.**

The honesty harness transfers directly: **interval coverage IS the calibration gate**
(reuse the `ensemble_calibration` walk-forward pattern), and the Brier/decomposition
culture maps onto proper scoring rules for vol.

### 30a — Range/interval forecast (ship the calibrated 80% band first)
- Backend: ✅ SHIPPED (`53266b7`, develop). `services/models/vol_range.py` — walk-forward
  EWMA vol forecaster emitting σ + 80%/95% bands per horizon; `GET /v1/forecast/range`
  (safety-wrapped); `walk_forward_coverage` locked as a calibration test.
- **✅ VALIDATED OUT-OF-SAMPLE ON REAL DATA (2026-06-07).** Every prior 30a number was
  measured on the *synthetic* regime-switching seed — which has vol clustering injected by
  construction, so an EWMA "finding" it was partly circular. An adversarial real-data
  harness (`seeds/validate_vol_real.py`, manual diagnostic — not CI, needs live network)
  fetched ~10y real daily history for all six commodities through the production Yahoo path
  and ran the **unchanged locked functions** on real returns:
  - **80% coverage holds on real data: 6/6 commodities pass [77,83]% at 1w** (NG 81.2 · CL
    81.2 · HO 79.0 · RB 81.3 · GC 79.5 · SI 79.3), n_eff ≈ 497 independent windows.
  - **Forward-vol correlation is *stronger* on real data than synthetic** (1w: 0.44–0.59;
    NG 0.444, CL 0.572, HO 0.589) — with large n_eff the significance is genuine. This,
    not the coverage level, is the real evidence of skill (the 80% level is somewhat
    forgiving; correlation cannot be).
  - The edge survived an adversarial test built to break it → it is a **real, validated
    out-of-sample, cross-commodity** calibration of the range band, not a seed artifact.
  - **Honest scope of the claim:** (1) it validates the *range/vol* edge only — the
    "no directional edge" finding is still synthetic-only and remains artifact-suspect
    until tested on real features→price; (2) it's a **table-stakes** edge (vol
    autocorrelation, the GARCH/HAR fact every vol desk has) — the moat is honest
    calibration + presentation, not a proprietary signal; (3) the **95% band is confirmed
    miscalibrated on real data too** (92–94%, fat tails) → 30c is necessary, not optional.
- Frontend: **✅ SHIPPED** (`e6d946c`, Signal Lab honesty fix). The Expected Range strip
  (`components/signals/ExpectedRange.tsx`) is live in `SignalsShell` (Row 1b), below the
  directional hero: 80% $-band + daily vol + live walk-forward coverage/correlation, "range
  only — no directional claim", instrument-following, auto-height (the earlier `8dd15b6`
  `h-full` bug is fixed). **Lesson banked: run the app and look before placing any UI.** The
  Phase-30d view/estimator selectors (below) build on this card.
- **Gate:** walk-forward 80% coverage within [77, 83]%; 95% reported (tails fixed in
  30c); documented. **Met on REAL out-of-sample data, 6/6 commodities** (synthetic locked
  as a regression test; real-data check re-runnable via `seeds/validate_vol_real.py`).

### 30b — Better estimator (flip point-forecast R² positive) ✅ SHIPPED + PROMOTED (`6f71827`, live 2026-06-08)
**Outcome: log-HAR beats the EWMA incumbent OOS on real data → shipped opt-in.** Default
stays EWMA (cheap single pass; the validated-calibrated 30a band). `estimator=har_log` is the
new opt-in path on `predict()` + `GET /v1/forecast/range`.

- **Built** (`services/models/vol_range.py`): pure-numpy walk-forward HAR-RV (Corsi 2009) — OLS
  of realized forward-h-day variance on [daily, weekly, monthly] RV components, refit each step
  on only target windows closed *before* the decision point (look-ahead-safe; prefix-invariance
  locked as a test). Two forms: raw-variance (`_har_rv_sigma`) and **log-HAR** (`log=True`, the
  shipped one) with a causal Jensen back-transform. No new deps.
- **`estimator_skill()`** is the acceptance harness: walk-forward OOS R² (vs the mean benchmark)
  + RMSE for persistence / EWMA / raw-HAR / log-HAR on the same target & sample.
- **Gate MET on real data** (`seeds/validate_estimator_30b.py`, ~10y, 6 commodities):
  - **log-HAR > EWMA**: mean OOS R² **+0.25 vs +0.20 @1w**, **+0.21 vs +0.16 @1m**; wins NG
    decisively (+0.22 vs +0.06 @1w; +0.14 vs −0.03 @1m); the few "losses" are marginal ties.
  - **raw-variance HAR FAILED** and is **benched** (code+tests retained): it did not beat EWMA
    and **blew up on real CL (R² −1.06 @1m)** — linear HAR over-extrapolates in vol explosions.
    log-HAR is bounded-multiplicative and fixes exactly this (the "say so" honest-gate moment).
  - **Coverage preserved** under log-HAR (bands recompute against its σ): cov80 ≈0.78–0.81,
    cov95 ≈0.93–0.95 — locked in `tests/test_vol_range.py`.
- **Provenance** (`docs/MODEL_DILIGENCE.md`): log-HAR point forecast = **real-OOS ✅**; raw-HAR
  = **real-OOS ❌ benched**.
- **Deferred to 30d:** make log-HAR the *default* (needs a perf pass — periodic refit, not daily
  O(n) OLS — + re-validation) and surface the estimator selector in the UI with its live
  calibration readout. The frontend contract regen also rides along with 30d (additive optional
  query param; web untouched this session).

### 30c — Fat tails + regime conditioning
- **✅ SHIPPED + real-OOS validated (2026-06-07).** Replaced the fixed normal-z band
  multipliers with **empirical quantiles of past realized standardized moves** (walk-forward,
  look-ahead-safe, normal-z fallback while thin) in `vol_range.py`. Real returns are
  fat-tailed → the 95% multiplier runs above 1.96 and the band reaches nominal.
- **Gate MET on real data:** 95% coverage now **93–95%** across NG/CL/HO/RB/GC/SI (was 92–94%
  under normal-z); 80% stays 78–81%. Locked in `tests/test_vol_range.py`; re-checked via
  `seeds/validate_vol_real.py`. Endpoint + `API_CONTRACTS.md` updated.
- **Remaining (optional):** regime-conditional vol (reuse `volatility_regime` context) — the
  empirical-quantile fix already meets the coverage gate, so this is a refinement, not a
  blocker.

### 30d — Mode selection / views (informed choice, not false equivalence)
**Frontend views ✅ SHIPPED (session 2026-06-07, branch `feat/phase-30d-views`).** The first
*visible* payoff of the vol/range arc. Owner-decided split: **frontend views first**, the
log-HAR **default-swap deferred to a focused backend follow-up** (see "Remaining" below).

The user picks the **view**, never a "which model is right" toggle — direction and range
answer different questions and must not be presented as co-equal (direction has no edge —
**confirmed real-OOS 2026-06-07**: price-only models score ≈45–57% decisive, below a
drift-aware naive baseline in all 36 commodity×model×horizon cells; see `MODEL_DILIGENCE.md`).
- ✅ **Range · Direction · Both** view selector in Signal Lab (`SignalViewControls.tsx` +
  reusable `Segmented.tsx`); default Both, range primary; Range hides the directional hero,
  Direction hides the range + the estimator selector (never co-equal).
- ✅ **Estimator selector (EWMA · log-HAR)** *within* vol views — wired through
  `useRangeForecast(symbol, horizon, estimator)` → `?estimator=`; ExpectedRange badges the
  active estimator and its band/coverage recompute live (verified: EWMA ±6.6% → log-HAR
  ±12.4% on NG 1w). HAR-RV/GARCH-lite naming collapsed to the two shipped estimators.
- ✅ **Guardrail intact:** ExpectedRange carries its live walk-forward coverage/corr; the
  EnsembleHeader keeps its "no proven directional edge" caveat. You can choose the view; you
  can't escape its track record. Visual-verified (Playwright, all four states); `pnpm health`
  web lane green (typecheck + biome + 402 vitest, +4 new).
- **Remaining (backend follow-up, deferred by owner this session):** make log-HAR the
  **default** after a **perf pass** (periodic refit, not per-step O(n) OLS) + re-validation on
  `seeds/validate_estimator_30b.py`; then frontend contract regen (the `estimator` param is
  additive/optional, so nothing is broken meanwhile). Frontend + this backend swap promote to
  live together.

- **Cross-cutting gate (all of 30):** walk-forward coverage/skill is the acceptance test
  (extend the `ensemble_calibration` harness to vol); honest framing per AI_BEHAVIOR;
  `pnpm health` green; the 80%-coverage result locked as a regression test.

### Also still on the table (post-26 strategic)
**Selective abstention** — emit a directional call only when a configuration has
*historically* paid (extreme regime + strong agreement + catalyst), abstaining
otherwise. Harvests residual directional edge honestly; complements Phase 30. Lower
priority than the vol engine but a natural follow-on.

---

## Later phases (sequence TBD — Phase 30 recommended ahead of these)

### Phase 27 — Concierge copilot (wow + utility)
Floating agentic assistant: navigates screens, explains any feature/number, greets
signed-in users by name (Clerk). Reuses the LLM layer + `services/safety.py`.
Open question to resolve first: admin-only vs agentic-for-all.

### Phase 28 — Accounts GA + Decision Ledger (retention / X-factor)
Finish Clerk (PR #7) → per-user saved work, then a decision ledger: every thesis
captured with conviction → auto-resolution → personal calibration (track record over
time). Ties into existing `desk_calibration` + `auto_resolution`.

### Phase 29 — Charting differentiators (Phase 25 leftovers that differentiate)
Spread/ratio charts (crack spread, gold/silver, CL/NG), multi-symbol compare, manual
drawing tools (LWC v5 primitives), pattern-credibility backtest (reuse Phase-10
engine to show which patterns actually paid).

### Phase 31 (DEFERRED) — Real feature-history ingestion (the structural diligence gap)
The remaining substrate gap surfaced by the 2026-06-07 diligence pass. Backtests +
calibration currently run on the synthetic seed, whose COT/storage/weather are causally
independent of the price path — so `logreg_directional` and `factor_composite` **cannot be
validated** and their directional output is `unvalidated` in `MODEL_DILIGENCE.md`. Closing it:
ingest **real historical COT (CFTC, free) + EIA storage history**, persist them, and re-run
the backtests on real features→price. Only then can the multimodal models earn a real-OOS
verdict. Multi-day effort; deferred consciously so the roadmap can proceed — but it is the
one thing standing between "we think these models work" and "we checked." Not forgotten.

## Parallel quick-wins (fold in opportunistically)
- **Scenario fidelity:** make shocks move recent-return *momentum*, not just price
  level — fixes the lean-vs-ensemble divergence seen on the OPEC run.
- **Phase 19 cosmetic:** soften the "MOCK" label; lighter first-run walkthrough dim.
