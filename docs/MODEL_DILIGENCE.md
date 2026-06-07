# Model Diligence — what is validated, on what data

_Last updated 2026-06-07._

This is the single source of truth for **which model claims are real and on what evidence.**
It exists because the failure mode that nearly bit this project was framing quietly
escalating *synthetic-data properties* into *product claims*. Every backtest and calibration
number in this repo is computed on the **synthetic seed** (`seeds/price_generator.py`, a
regime-switching GBM) unless a row below says otherwise.

## The rule (non-negotiable)

> **No predictive or calibration claim ships — in code, docs, UI, or a pitch — without
> stating its data provenance: `synthetic`, `real-OOS`, or `real-in-sample`.**

`synthetic` = measured on seeded data. `real-OOS` = walk-forward on real market data the
model never fit. `real-in-sample` = real data but fit/tuned on the same sample (weak).

## Why synthetic-only is disqualifying as *evidence*

The seed is fine for demos and UI. It cannot be evidence of an edge because:
- It **injects** volatility clustering by construction (a Markov chain over 4 vol regimes),
  so any vol detector "finds" an edge tautologically.
- Its feature generators (COT, storage, weather) are **causally independent of the price
  path** — they never read a close. So price is unpredictable from features *by
  construction*, which guarantees "no directional edge" before any model runs.

Both of those are guaranteed results, not discoveries. Only real-data validation tells you
whether a claim survives outside the generator.

## Validation ledger

| Claim | Provenance | Verdict | Evidence |
|---|---|---|---|
| Vol/range **80% band** is calibrated | **real-OOS** ✅ | Holds: 78–81% coverage, 6/6 commodities @1w | `seeds/validate_vol_real.py`, ~10y real daily NG/CL/HO/RB/GC/SI |
| Vol/range **95% band** is calibrated | **real-OOS** ✅ (after Phase 30c) | Holds: 93–95% coverage (was 92–94% under normal-z) | same harness, post-30c empirical fat-tail quantiles |
| Vol forecast carries **forward-vol info** | **real-OOS** ✅ | corr 0.44–0.59 @1w, stronger than synthetic, n_eff≈497 | `forecast_vol_correlation` on real data |
| **Directional** edge (`moving_average_directional`, `holt_trend`) | **real-OOS** ✅ tested | **No edge.** Decisive accuracy ≈45–57%, *below* a drift-aware naive baseline in all 36 rows (edge −0.8 to −7.6pp); no confidence gradient | `seeds/validate_direction_real.py`, ~10y real, scored via `signal_scoring.score_forecast` |
| **Directional** edge (`logreg_directional`, `factor_composite`) | **unvalidated** ⚠️ | Cannot be tested — they consume synthetic COT/storage. Treat directional claims as unproven | blocked on real historical COT + EIA ingestion (deferred) |
| Ensemble **confidence gradient** (26c) | **real-OOS** ✅ tested | No reliable OOS gradient at any horizon; shipped reframed as down-weighting miscalibrated models | `tests/test_ensemble_calibration.py` |
| Per-model diagnostics (bias / Brier decomposition / drift) (26a) | **synthetic** | Methodology validated on seeded data; reproduces known truths | `services/model_diagnostics.py` |

## What this means for the product story

- The platform's **one genuine, real-data-validated predictive edge is volatility/range**,
  not price direction. Say exactly that.
- It is a **table-stakes** edge (vol autocorrelation — the GARCH/HAR fact every desk has).
  The moat is honest calibration + presentation, not a proprietary signal.
- **Direction has no real edge** and the product correctly declines to manufacture one.
  This is now backed by real-data evidence, not just the synthetic seed.

## The remaining structural gap (deferred, tracked)

The only way to move `logreg`/`factor` out of `unvalidated` is to **ingest real historical
COT (CFTC, free) + EIA storage** and re-run the backtests on real features→price. Until then,
their directional output is unproven. Scoped as a future phase in `BUILD_ROADMAP.md`.

## How to re-run

```
uv run --directory apps/api python -m seeds.validate_vol_real        # vol/range, real OOS
uv run --directory apps/api python -m seeds.validate_direction_real  # direction, real OOS
```
Both are manual diagnostics (live network → not hermetic CI). The *synthetic* locks live in
`tests/test_vol_range.py` / `tests/test_ensemble_calibration.py` and run in `pnpm health`.
