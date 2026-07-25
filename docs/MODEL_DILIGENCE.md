# Model Diligence — what is validated, on what data

_Last updated 2026-07-24 (Phase 31a.0)._

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
| Vol **point forecast**: log-HAR beats EWMA (30b → **default in 30d**) | **real-OOS** ✅ | Beats incumbent EWMA ≈+0.05 R²: **5/6 @1w, 4/6 @1m** commodities (RB @1w, CL+RB @1m lose *marginally*, both still +R²). 30d made it the **default**; EWMA is the opt-out. 30d perf pass (refit every 5 steps, not per-step) is **skill-neutral** — a cadence sweep showed cadence-1 ≡ cadence-5 on the gate, so the cheaper version preserves the win | `seeds/validate_estimator_30b.py`, ~10y real, `estimator_skill` |
| Vol **point forecast**: raw-variance HAR (30b) | **real-OOS** ❌ benched | Does NOT beat EWMA; **blew up on real CL** (R² −1.06 @1m) — linear HAR on raw variance over-extrapolates in vol explosions. Code+tests retained, not wired | same harness; the failure log-HAR fixes |
| **Directional** edge (`moving_average_directional`, `holt_trend`) | **real-OOS** ✅ tested | **No edge.** Decisive accuracy ≈45–57%, *below* a drift-aware naive baseline in all 36 rows (edge −0.8 to −7.6pp); no confidence gradient | `seeds/validate_direction_real.py`, ~10y real, scored via `signal_scoring.score_forecast` |
| **Directional** edge (`logreg_directional`, `factor_composite`) | **unvalidated** ⚠️ | Cannot be tested — they consume synthetic COT/storage. Treat directional claims as unproven | blocked on real historical COT + EIA ingestion (deferred) |
| Ensemble **confidence gradient** (26c) | **real-OOS** ✅ tested | No reliable OOS gradient at any horizon; shipped reframed as down-weighting miscalibrated models | `tests/test_ensemble_calibration.py` |
| Per-model diagnostics (bias / Brier decomposition / drift) (26a) | **synthetic** | Methodology validated on seeded data; reproduces known truths | `services/model_diagnostics.py` |
| Desk **skill-vs-luck verdict** (B2) | **methodology** (not a predictive claim) | Wilson 95% CI on directional hit-rate vs the 0.50 chance baseline → `skill` only when the lower bound clears chance, else `luck`, else `insufficient` (`n < 10`). Pre-registered thresholds (`SKILL_BASELINE=0.50`, `WILSON_Z=1.96`). Consistent with the no-directional-edge finding, the blind `momentum`/`contrarian`/`random` desks are expected to read `luck` — the tool refuses to crown noise as skill | `services/desk_calibration.py::skill_verdict`; honesty-locked in `tests/db/test_desk_skill_verdict_e2e.py` (real coin-flip desk → `luck`) + `tests/test_desk_calibration.py` |
| **Backtest alt-data context integrity** (31a.0) | **methodology** (correctness fix, not a predictive claim) | Pre-31a.0, the backtest's context chokepoint was **symbol-blind**: `_cot_as_of` took the global two most recent COT rows across ALL markets (CFTC releases every market the same Friday → `mm_net_delta` mixed different commodities' nets every colliding week), and `_storage_as_of` fed **NG national storage to every symbol's backtest** as if it were its own fundamental. Fixed: COT is filtered by the instrument's CFTC market code (symbols without one — ES/ZN — get None, never another market's positioning); storage serves NG only. **Any persisted multi-symbol backtest/calibration row for `factor_composite` predating this fix contains contaminated context — re-run before citing.** | `services/backtest.py::_cot_as_of/_storage_as_of`; locked fail-without/pass-with in `tests/test_backtest_lookahead.py::test_cot_as_of_filters_by_market_code` + `tests/db/test_context_scoping.py` (real SQL, gated CI `db-tests`) |
| **Storage surprise = seasonal-norm proxy on real data** (31a.0) | **methodology** (labeled proxy) | Real EIA publishes **no analyst consensus** (`surprise_bcf` is NULL on every real row — the mock seed fabricates one), so the factor composite's "delta vs consensus" leg is impossible on real data (pre-31a.0 it crashed with `TypeError: float(None)`). Replaced with the **consensus-free seasonal surprise**: this week's net change vs the same-calendar-week 5-year average (min 3 prior years, else honest abstention). The UI/LLM note labels it "5-year seasonal norm (consensus-free proxy)" — never passed off as a survey. Surveyed consensus is still preferred when present | `services/storage_features.py::delta_vs_seasonal_norm`; `tests/test_storage_features.py` + `tests/test_factor_composite_alt_data.py` (TypeError regression + label locks) |
| **Cross-asset configs** for `index` (ES) + `rates` (ZN) (B5) | **unvalidated** ⚠️ (hand-set) | The per-asset-class vol-regime bands, voter thresholds, deadband, and band-widths for the two new classes are **hand-set plausible scales**, not calibrated or backtested. B5 is a **portability** phase: it proves the forecast→decision→resolution→calibration loop *runs* cross-asset with no commodity hardcode leaking (verified live on real ES/ZN bars — ZN reads treasury-scale: ~110 price, 0.32%/day vol, ±0.94% 1w band), **not** that it predicts equities or rates. The vol/range *band* self-calibrates per series (empirical walk-forward quantiles — ZN live cov80 ≈ 80%); the *directional* config values carry no edge claim. Validating them is future work | `services/asset_config.py` (`_INDEX`/`_RATES`); `tests/test_cross_asset_loop.py` (no-leak + runs); byte-identical commodity lock `tests/test_asset_config_golden.py` |

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
their directional output is unproven. Scoped as Stage C / Phase 31 in `MASTER_PLAN.md`
(detail: `PHASE_31_PLAN.md` v2). **31a.0 (2026-07-24) shipped the correctness
prerequisites** — symbol-scoped context + the consensus-free surprise proxy — without which
the eventual 31b verdict would have measured contamination and a dead storage leg instead of
the models.

**Paper-engine tick value — deliberate, labeled deferral (B5, issue #10).** The paper engine's
per-$1-move USD multiplier should be each instrument's real `contract_size` (NG 10000, CL 1000,
GC 100, SI 5000, ES 50, ZN 1000). B5 wired this for the **new** classes (`index`/`rates`) but
**deliberately pinned every pre-existing commodity/metal class to the legacy `10000`** so the
deployed demo's paper-trading equity curve does not move (the open-position MTM of a non-NG
trade would shift up to 10×). NG is correct either way (its `contract_size` *is* 10000); CL/GC/SI
keep a known-wrong multiplier **on purpose, as-shipped**, until the correction is reviewed
against the demo. The pin is documented in `services/paper_engine.py::_resolve_tick_value` and
tracked as **issue #10** — it is not a claim that 10000 is correct for those instruments.

## How to re-run

```
uv run --directory apps/api python -m seeds.validate_engine_oos      # WHOLE engine: direction (all 5 models + ensemble, vs baseline + Brier skill + deadband on/off) AND vol coverage, per-commodity + pooled
uv run --directory apps/api python -m seeds.validate_vol_real        # vol/range, real OOS
uv run --directory apps/api python -m seeds.validate_direction_real  # direction (price-only models), real OOS
```
All are manual diagnostics (live network → not hermetic CI). `validate_engine_oos` is the
one-table umbrella scorecard — each metric reported next to its baseline so the number can't
flatter itself (last run: **no directional edge over baseline on any model/horizon/commodity**;
vol bands calibrated ~80/95% across all 6). The *synthetic* locks live in
`tests/test_vol_range.py` / `tests/test_ensemble_calibration.py` and run in `pnpm health`.
