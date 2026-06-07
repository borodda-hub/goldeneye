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

### 26a — Model diagnostics & error/bias detection (start here)
Build the X-ray before adding models.
- `services/model_diagnostics.py` + `GET /v1/models/diagnostics`:
  - per-model **directional bias** (chronically too bullish/bearish),
  - **regime-conditional accuracy** (e.g. logreg in crisis vol),
  - **Brier decomposition** (calibration vs sharpness, not just the scalar),
  - **feature-importance drift** for logreg over time.
- **Model Health** card on `/calibration`.
- **Gate:** diagnostics reproduce known truths on seeded data (e.g. vol_regime's
  weak direction signal shows as low sharpness); tests; honest in-sample labels.

### 26b — Four distinct, honest models
- Settle the 4-model lineup with non-overlapping theses: ① technical/momentum,
  ② statistical time-series (make Prophet/ARIMA non-optional so it isn't a prod
  stub), ③ **learned multimodal factor** (replace `factor_composite` hand-set
  weights with a trained model over storage+COT+momentum), ④ ML directional
  (`logreg`, possibly upgraded). Fold `volatility_regime` into a regime *context*
  input rather than a directional voter.
- **Gate:** each model passes the look-ahead-safe backtest; the learned factor
  model beats its hand-set predecessor on out-of-sample Brier, or we keep the
  honest baseline and say so explicitly.

### 26c — Ensemble v2 (calibration-weighted)
- Weight models by measured historical accuracy (Brier), not just agreement;
  ensemble confidence should track realized hit-rate.
- **Gate:** ensemble confidence buckets are demonstrably calibrated on the backtest
  (high-confidence calls actually hit more).

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
