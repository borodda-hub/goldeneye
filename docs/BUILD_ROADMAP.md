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

### Post-26 strategic note (not yet scheduled)
Since the lineup shows no OOS directional edge at any horizon, future real value is
likelier in: (a) **volatility / range forecasting** (vol clusters → genuinely
predictable), or (b) **selective abstention** (emit a directional call only when a
configuration has *historically* paid), than in more directional-ensemble work.

---

## Later phases (sequence TBD after Phase 26 reassessment)

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
