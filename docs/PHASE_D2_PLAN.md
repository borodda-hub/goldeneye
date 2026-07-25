# Phase D2 Plan — Carry / Term-Structure (curve archive + pre-registered probe)

**Objective (MASTER_PLAN §4 D2):** curve slope (backwardation/contango) is
the best-documented commodity return predictor (Gorton–Rouwenhorst; Koijen
et al. "Carry"). Two deliverables: (a) **D2a** — a daily futures-curve
vintage archive (the D5 pattern) so full-fidelity carry work is possible
forever after; (b) **D2b** — a pre-registered probe on the curve history we
can honestly reconstruct today.

**Status:** drafted + executed 2026-07-25 on `feat/phase-d2-carry`.

## Verified facts ([V], probed 2026-07-25)

- **Yahoo serves ACTIVE contract months with deep history** (NGU26.NYM:
  1,260 daily points ≈ 5y) but **expired months return Not Found**
  (NGZ23.NYM, CLZ20.NYM, GCZ24.CMX all dead) → the historical front-of-curve
  cannot be fully reconstructed from Yahoo.
- **Nasdaq Data Link CHRIS continuous (CME_NG1/NG2) is dead** (bot-walled
  HTML, no JSON) → no free historical continuous second-month either.
- **`price_bars` retains bars for since-expired contracts** (the DB is an
  archive by construction): the June/July backfills persisted 2026 front
  months that Yahoo has since dropped. Combined with 5y-deep listed months,
  a *partial* historical curve is reconstructible from our own DB.
- `contracts` carries `expiry_date`; the market adapter fetches by
  contract code; `backfill_instrument(lookback_days=...)` already supports
  arbitrary lookback (the CLI just didn't expose it).

## Design

**D2a — curve vintage archive** (rides the 31d refresh tick, D5 pattern):
- Migration `013_curve_vintages`: `futures_curve_vintages` — one row per
  (vintage_date, symbol), JSONB `curve` = the adapter's
  `get_curve_snapshot` list verbatim, `source` labeled. UNIQUE key;
  **insert-only repo (ON CONFLICT DO NOTHING)** — vintages are immutable
  history, same doctrine as D5.
- Prod archives daily automatically (`FEATURE_REFRESH_ENABLED` already on).

**D2b — probe** (`seeds/validate_d2_carry.py`, manual/network):
- **Data step first:** deep-backfill listed months for NG + CL with
  `--lookback-days 1825` (new optional CLI arg on `backfill_prices`,
  default unchanged) → per-contract real dailies in `price_bars`.
- **Signal:** at date t, take the two nearest-expiry contracts with bars at
  t; `slope[t] = (ln P_far − ln P_near) / Δyears` (annualized log slope).
  Sign view: backwardation (slope < 0) ⇒ bullish; contango ⇒ bearish (the
  classic carry direction). **Coverage caveat (recorded, not hidden):** for
  older dates the nearest *surviving* pair sits further out the curve —
  a deferred-slope proxy. This is a data-coverage limitation, NOT
  look-ahead: the contracts used were listed and priced at t.
- **Outcome:** forward 1w / 1m front-month (`NG=F`/`CL=F` continuous)
  returns; **1m is primary** (carry is slow). Weekly Friday decisions; all
  SEs overlap-scaled (1m: n_eff = n/4.3).

## Pre-registered gates (locked before the first run)

- **P0 — power rule:** if pooled (NG+CL) 1m decision count n_eff < 60, the
  verdict is **INSUFFICIENT-N — archive collecting** regardless of point
  estimates (a thin sample must not be crowned OR buried).
- **G1 (primary):** slope-sign direction beats drift-naive (walk-forward
  trailing base rate) on pooled OOS Brier @1m by ≥1 SE (paired, n_eff).
- **G2:** mean forward 1m return monotone across walk-forward expanding
  slope terciles, top−bottom ≥1 SE (n_eff), same sign on NG and CL.
- **VERDICT:** PASS = G1+G2 → scope carry-feature integration (separate
  phase, own gate). FAIL/PARTIAL/INSUFFICIENT → record; the D2a archive
  keeps collecting toward a full-fidelity re-run (re-entry trigger: ≥ ~2y
  of daily curve vintages, gate unchanged).

## Gates checklist (§7.4)

Health green · migration in the gated `tests/db` loop + vintage
immutability lock · S3 untouched (probe reads; the only writer is the
sanctioned backfill CLI) · S4 verdict recorded in `MODEL_DILIGENCE.md`
either way · S7 SCHEMA.md + this plan in-commit · S8 two-lane promotion.

## D2b verdict — ❌ **FAIL** (run 2026-07-25; adequately powered, recorded)

Coverage (after merging DB bars with direct 5y listed-month fetches — the
market adapter itself caps ~1y, a data-layer finding recorded here):
**1,257 curve days per symbol (2021-07 → 2026-07)**; 504 weekly decisions
@1w (non-overlapping), 498 @1m (n_eff ≈ 116 — **P0 power rule satisfied**).

- **G1 ✗:** carry-sign does NOT beat drift-naive — pooled ΔBrier
  **+0.0062 ± 0.0037 @1w** and **+0.0043 ± 0.0078 @1m** (worse, not
  better); carry hit 47–48% vs drift 46–49% vs base ~53%.
- **G2 ✗:** no monotone tercile pattern on either symbol; NG's contango
  tercile had the *highest* forward return in this sample (wrong sign).

**VERDICT = FAIL on this design.** Honest boundaries (recorded, not spin):
this is a **time-series** carry test on TWO commodities over FIVE years,
with the older half measured on **deferred-pair slope** (coverage
limitation). It does **not** refute the literature's strongest form —
**cross-sectional** carry across many commodities over decades — which is
untestable free today (no historical curves; that is exactly what the D2a
archive is accumulating). **Re-entry trigger:** ≥ ~2y of daily 6-symbol
curve vintages → re-run per-symbol front-slope AND add a cross-sectional
rank test, gates pre-registered then (this one unchanged for the re-run).

**D3 consequence:** the cross-sectional systematic desk depended on a
validated carry signal — with D2b FAIL and cross-sectional history
unavailable, **D3 is DEFERRED to the same trigger** (seeding a desk on a
just-refuted signal would be building on a refuted premise).
