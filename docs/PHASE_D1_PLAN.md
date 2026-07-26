# Phase D1 Plan — Implied-vs-Realized Vol (variance-risk-premium probe)

**Objective (MASTER_PLAN §4 D1):** the platform's one validated edge is
calibrated *realized*-vol forecasting. The classic way a vol forecast becomes
an *edge* is comparison against what the market is pricing: forecast RV vs
**implied** vol. This phase is **probe-first** (the Phase-30
vol-predictability-probe pattern): a manual real-data diagnostic with a
pre-registered gate. UI/endpoint work (a "market prices X% vol; our engine
says Y%" research surface) is **D1b, only if the gate passes**.

**Status:** drafted + executed 2026-07-25 on `feat/phase-d1-vol-premium`.
Base: `master == develop == 8b28ab5` (Phase 31 complete).

## Honest framing

The *variance risk premium* (IV persistently above subsequent RV) is a
well-documented market fact — replicating it is table stakes, not an edge.
The edge question is **G2**: does OUR forecast's spread to IV predict *how
large* the subsequent premium will be? Priors: HAR-family forecasts beating
raw IV as an RV predictor is standard literature (G1 likely); conditional
premium timing (G2) is harder. A FAIL on G2 is a publishable honest verdict;
PASS powers a rich/cheap-vol research view. Either way the verdict is
recorded (S4) and the probe stays re-runnable.

## Verified facts ([V], checked 2026-07-25)

- Yahoo serves **~12y of daily history (3,017 points)** for all four needed
  tickers via the production chart path: `^OVX` (CBOE Crude Oil ETF
  Volatility Index), `^GVZ` (CBOE Gold ETF Volatility Index), `USO`, `GLD`.
- OVX/GVZ are **30-day implied-vol indices on USO/GLD options** (annualized,
  in % — e.g. 35 = 35%/yr). Comparing them against USO/GLD realized vol (not
  futures RV) keeps the underlying identical on both sides.
- `services/models/vol_range._sigma_path(rets, h, estimator)` returns the
  full **walk-forward** daily-σ path for `ewma`/`har_log` — each σ[t] uses
  returns ≤ t only (30a/30b machinery, S3-safe by construction).
- Fetch helpers (`YAHOO_BASE_URL`, `_HEADERS`, `_parse_chart`) are
  importable from `adapters/market/yahoo_delayed` (the
  `validate_vol_real.py` pattern).

## Design

- **Pairs:** (USO, ^OVX) and (GLD, ^GVZ). Both sides of each comparison
  reference the same underlying ETF.
- **Forecast:** σ_f[t] = walk-forward daily σ from `_sigma_path`
  (**har_log** primary — the production default; **ewma** shown as
  robustness) annualized ×√252.
- **Implied:** IV[t] = index close / 100.
- **Realized outcome:** RV[t] = std of the NEXT 21 trading days' log
  returns, annualized ×√252 (matches the indices' 30-calendar-day tenor).
- **Decision points:** weekly (Fridays). 21-day outcomes from weekly points
  overlap ~4.2× → all SEs are scaled to **n_eff = n / 4.2** (the 30a
  overlap convention; never quote raw-n significance).
- **Walk-forward bucketing (G2):** the spread s[t] = σ_f[t] − IV[t] is
  bucketed into terciles of its own *expanding past* distribution
  ({s[·<t]}, ≥52-week warm-up) — no in-sample bucket boundaries.

## Pre-registered gates (locked before the first run)

- **G0 — sanity anchor (not a gate):** mean(IV − RV_next) > 0 on both
  assets (the premium exists on this sample). Literature replication,
  labeled as such.
- **G1 — input skill:** MAE(σ_f, RV_next) < MAE(IV, RV_next), paired
  difference ≥ 1 SE on n_eff, for har_log on **both** assets. Validates our
  input is competitive with the market's own forecast.
- **G2 — the edge claim:** mean subsequent premium (IV − RV_next) is
  **monotone decreasing** across the walk-forward spread terciles (low
  σ_f−IV ⇒ vol rich ⇒ larger premium), and (bottom-tercile − top-tercile
  premium) ≥ 1 SE on n_eff, with the **same sign on both assets**.
- **VERDICT:** PASS = G1 AND G2 on both assets → scope D1b (research
  surface). PARTIAL = G2 on exactly one asset → record, no build, revisit
  with more data. FAIL = otherwise → record and bench (the platform keeps
  its "we forecast RV honestly" claim and adds "and we checked whether that
  times the vol premium — it doesn't").

## Change set (probe only — no app code)

- `apps/api/seeds/validate_d1_vol_premium.py` — manual diagnostic (network;
  never CI), house conventions (walk-forward only, every metric beside its
  baseline, n_eff reported, explicit gate verdict printed).
- Docs in-commit: this plan, `MODEL_DILIGENCE.md` verdict row after the
  run, `MASTER_PLAN.md` D1 status, `HANDOFF.md`.

## Gates checklist (§7.4)

S1 WIP=1 (this is the primary thread) · S2 `pnpm health` (no app-code
change → trivially green, still run) · S3 untouched (no model/resolution
change; probe uses the walk-forward machinery read-only) · S4 provenance =
real-OOS probe, verdict recorded either way · S5 = re-runnable manual
diagnostic (network-dependent → not a hermetic CI lock, per the
`validate_*_real` precedent) · S6 no UI surface this phase · S7 docs
in-commit · S8 feat branch → develop → master sign-off.

## D1 verdict — ⚖️ **PARTIAL** (run 2026-07-25, `seeds/validate_d1_vol_premium.py`; record, no build, revisit)

Sample: 2015-08 → 2026-06, 549 weekly Friday decisions per pair, n_eff ≈ 131.

- **G0 ✅ (anchor):** the premium replicates — mean(IV − RV_next) = **+5.54
  vol-pts (USO/OVX)** and **+1.88 (GLD/GVZ)**, positive ~78% of weeks. As
  expected; table stakes, not an edge.
- **G1 ✗ (needed both):** GLD **passes** (MAE 3.58 vs 3.91, paired −0.32 ±
  0.27 — our har_log beats GVZ as an RV predictor >1 SE); USO better in
  point estimate (−0.51) but within noise (±0.71).
- **G2 ✗ (needed both):** **USO/OVX passes cleanly** — monotone terciles
  +7.61 → +5.55 → +2.03 vol-pts, low−high **+5.59 ± 3.77** (economically
  large: the premium nearly quadruples when our forecast sits far below
  OVX). **GLD fails** (non-monotone, +0.98 ± 1.06). EWMA robustness arm
  fails everywhere → the signal is specific to the har_log/crude cell.
- **VERDICT = PARTIAL per pre-registration:** one strong cell, no
  cross-asset replication, estimator-fragile — not crowned. **No D1b
  surface.** Revisit triggers: (a) more IV pairs to break the 1-of-2 tie
  (e.g. ^VIX/SPY via the identical harness — free), (b) ~2 more years of
  data on the same pre-registered gate, unchanged. The probe re-runs in
  one command; the gate must NOT be re-tuned to fit this sample.

## D1 revisit — trigger (a) exercised: add (SPY, ^VIX) — interpretation pre-registered BEFORE the run (2026-07-25)

The third pair runs through the **identical harness** (same PMAP, same
walk-forward terciles, same overlap-scaled SEs, har_log primary). The
original 2-pair verdict above stands untouched; this section only resolves
what the tie-breaker means — decided now, before the run:

- **G2 passes on (SPY,^VIX) → 2-of-3 with consistent direction:** upgrade
  PARTIAL → **PROMISING** — schedule a D1b *design review* (still NOT a
  validated edge: G1 remains unmet and the EWMA fragility stands; any
  product surface needs its own gate).
- **G2 fails on (SPY,^VIX) → 1-of-3:** downgrade the crude cell to
  **likely noise**; park D1 until trigger (b), full stop.
- No third outcome; no re-tuning; the equity pair gets no special
  treatment (the tercile machinery is scale-free by construction).

### Revisit result (filled after the run)
See below.
