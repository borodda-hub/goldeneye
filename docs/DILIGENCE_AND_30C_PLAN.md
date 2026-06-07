# Diligence Wrap-up + Phase 30c — Verified Plan

_Drafted 2026-06-07. Goal: close every ML-diligence gap that rests on synthetic-only
evidence, fix the one confirmed live defect (95% band), and plant a guardrail — so the
roadmap resumes with no claim resting on data we generated ourselves._

**Status: plan VERIFIED against code (not inferred).** Every interface below was read in
this session. The three refinements verification produced are marked **[V]**.

---

## Verified facts the plan depends on

| Assumption | Verified? | Evidence |
|---|---|---|
| `moving_average_directional.predict(closes, horizon)` is price-only, returns direction + confidence + expected_pct | ✅ | `inputs_used=["closes"]`; needs ≥55 closes; SMA-20/50 cross |
| `holt_trend.predict(closes, horizon)` is price-only, same `ForecastResult` shape | ✅ | pure-numpy Holt; needs ≥30 closes; SNR→confidence |
| `logreg_directional` / `factor_composite` need synthetic features (COT/storage) | ✅ | `backtest._predict` passes `latest_storage`/`latest_cot`; **not testable on real price alone** |
| Production "hit" definition is a reusable pure function | ✅ | `signal_scoring.score_forecast(direction, horizon, expected_pct, realized_pct, deadband=0.003)` → hit/miss/indeterminate/neutral/pending |
| Production horizon = calendar days 1/7/30 + forward-search to next trading bar | ✅ | `backtest._HORIZON_DAYS` + `_close_on_or_after` |
| `vol_range` band = `z[lv]·σ[t]·√h`; coverage test checks `|cum_h_return| ≤ z·band` | ✅ | `vol_range.walk_forward_coverage` lines 129–135 |

**[V1] Reuse `score_forecast` verbatim** in the direction harness — do NOT invent a hit
metric. This makes the real-data verdict directly comparable to the live Signal Lab table.

**[V2] Mirror production's calendar-day + forward-search horizon** (the Yahoo fetch already
returns `(date, close)` pairs, so this is exact, not approximated).

**[V3] Fat-tail fix must be estimated walk-forward** (expanding window, past standardized
residuals only) to stay look-ahead-safe — confirmed against the existing `_wf_sigma`
pattern. A naive full-sample quantile would leak.

---

## Step 1 — Direction on real data (finish the symmetry) · ~½ day

New manual diagnostic `apps/api/seeds/validate_direction_real.py` (sibling to
`validate_vol_real.py`; needs live network, not CI).

- Reuse the real-close fetch from `validate_vol_real.py` (continuous front-month, ~10y).
- For each symbol, walk forward: at index `t` (≥55 prior closes), feed `closes[:t+1]` to
  `ma_predict` and `holt_predict` at 1d/1w/1m. **[V2]** realized move = first close on/after
  `date[t] + {1,7,30}` calendar days, anchored on `closes[t]`.
- **[V1]** Score each via `score_forecast`; aggregate exactly like `backtest._summarize`
  (hit_rate over hits+misses+indeterminate; exclude neutral+pending).
- Report, per (symbol × model × horizon): overall hit-rate, **hit-rate by confidence bucket
  (low/med/high)** — the "does high actually hit more, on real data?" question — and the
  **base rate** (unconditional up-rate beyond the ±0.3% deadband) as the no-edge benchmark.
- Explicitly print `logreg_directional` / `factor_composite` as **NOT TESTABLE here**
  (need real COT/EIA history) — the documented wall that motivates the deferred phase.
- **Output:** an honest real-data verdict on price-only direction. Expected ≈ base rate
  (no edge), consistent with Phase 26 — but now a finding on real data, not a seed artifact.
  If a confidence gradient *does* appear on real data, that is itself a notable result.

## Step 2 — Phase 30c: fat-tailed band (the one confirmed live defect) · ~½–1 day

The real-data run proved the 95% band under-covers everywhere (92–94%). This is live and
wrong. Fix in `services/models/vol_range.py` (real model code → full health gate).

- **Approach (recommended): empirical quantile of standardized returns.** Standardize each
  realized h-day move by `σ[t]·√h`; the band multiplier for level `lv` becomes the empirical
  quantile of `|standardized|` at `lv` instead of the normal `z[lv]`. Fat tails ⇒ that
  quantile exceeds 1.96, widening the 95% band toward nominal coverage. Pure-numpy
  (`np.quantile`), no new deps. **Student-t(ν from kurtosis) is the fallback** if empirical
  misses the gate.
- **[V3]** Estimate the quantile **walk-forward** (expanding window of past standardized
  residuals only), with a warm-up floor (~40 samples) below which it falls back to normal
  `z` so early windows aren't estimated on noise. At serve time (`predict`) the full-history
  quantile is fine (no future data).
- Re-validate with BOTH the locked synthetic unit test AND the real-data harness.
- **Gate:** real-data **95% coverage in [93,97]%** across all 6 commodities, **80% stays in
  [77,83]%**. If empirical can't hold both, ship the calibrated-as-possible version and say
  so (honest-gate culture), documenting the residual miss.
- Update: the locked `test_vol_range.py` coverage assertions, `/v1/forecast/range` to expose
  the corrected band + method label, `API_CONTRACTS.md`.

## Step 3 — Provenance guardrail · ~1 hr

New `docs/MODEL_DILIGENCE.md` — the single source of truth for **what is validated, on what
data**: a table keyed by claim → {synthetic | real-OOS | real-in-sample} → evidence pointer.
Seed it with: vol/range 80% (real-OOS ✅), 95% (real-OOS after 30c), direction (Step 1
verdict), logreg/factor (unvalidated — real-feature wall). Add the one-line rule: no
predictive/calibration claim ships without stating its data provenance. This is the doc a
diligence reviewer reads first.

## Step 4 — Consolidate + explicitly defer the big rock · ~½ hr

`BUILD_ROADMAP.md`: record **real historical COT + EIA ingestion** as the remaining
structural gap (the only thing that can validate `factor`/`logreg`), scoped as a future
phase — deferred with rationale, not forgotten. Refresh `HANDOFF.md` + memory.

## Step 5 — Gate, commit, stop at develop

`pnpm health` green; commit per step (direction harness / 30c / docs); **leave on `develop`**
— no master promotion without owner sign-off (two-lane flow).

---

## Out of scope (consciously deferred so the roadmap can resume)
- Real feature-history ingestion (the Step-4 deferral) — multi-day build.
- Scheduling auto-resolution + live desk Brier (that's the Phase-28 product play).
- 30d Range·Direction·Both views — depends on Step 1's verdict; do after.

## Roadmap re-entry after this wraps
Either **30b (HAR-RV estimator)** — now that 30c calibrates the band, 30b sharpens the
point forecast — or the **Phase-28 product play** (schedule auto-resolution). Decide then.

## Effort: ~1.5–2 days total. No master promotion. No model code touched in Step 1; Step 2
is the only change to a live model and goes through the full gate + re-validation.
