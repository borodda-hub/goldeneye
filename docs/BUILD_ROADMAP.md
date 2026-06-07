# Goldeneye — Build Roadmap (post-scenario-globe)

Status as of 2026-06-06. Organizing thesis: **decision intelligence, honest enough
to survive a capital firm's diligence.** Reviewed and prioritized with the owner.

## Decision (2026-06-06)
- **Open with Phase 26 — Model Intelligence v2.** Run the full phase (26a→26b→26c),
  promote, then reassess before picking the next phase.

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
- Backend: `services/models/vol_range.py` — a walk-forward vol forecaster emitting σ +
  interval bands (80% / 95%) per horizon; pure-numpy EWMA to start (it already passes
  80% coverage). Endpoint `GET /v1/forecast/range` (safety-wrapped per AI_BEHAVIOR).
- Frontend: expected-range band overlay on the chart + an "Expected Range" card with a
  **live walk-forward coverage readout** (the band's honesty, shown not asserted).
- **Gate:** walk-forward 80% coverage within [77, 83]%; 95% reported (tails fixed in
  30c); documented. (Already met for 80% on NG — lock it as a test.)

### 30b — Better estimator (flip point-forecast R² positive)
- EWMA → recalibrated-EWMA → **HAR-RV** (pure-numpy OLS on daily/weekly/monthly realized
  vol — no new deps; preferred) → optional GARCH-lite (flag `arch` as an optional dep,
  not required). Same walk-forward acceptance test.
- **Gate:** OOS R² > 0 vs the mean benchmark AND beats persistence; or keep the simplest
  estimator that is *calibrated* and say so (same honest-gate culture as 26b/26c).

### 30c — Fat tails + regime conditioning
- Student-t / empirical quantiles → 95% coverage near nominal (probe showed ~90% → fat
  tails). Regime-conditional vol (reuse the existing `volatility_regime` context).
- **Gate:** 95% coverage within [93, 97]% walk-forward.

### 30d — Mode selection / views (informed choice, not false equivalence)
The user picks the **view**, never a "which model is right" toggle — direction and range
answer different questions and must not be presented as co-equal (direction has no edge).
- **Range · Direction · Both** view selector (default Both, range primary; direction
  shown with its existing no-edge caveat).
- Estimator selector *within* vol mode (EWMA · HAR-RV · GARCH-lite).
- **Guardrail:** every mode/estimator carries its own live walk-forward calibration
  readout (coverage for range, the honest "no reliable gradient" label for direction).
  You can choose the view; you can't escape its track record. Prevents bias-confirming
  cherry-picking — the core "decision intelligence, honest enough for diligence" stance.

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

## Parallel quick-wins (fold in opportunistically)
- **Scenario fidelity:** make shocks move recent-return *momentum*, not just price
  level — fixes the lean-vs-ensemble divergence seen on the OPEC run.
- **Phase 19 cosmetic:** soften the "MOCK" label; lighter first-run walkthrough dim.
