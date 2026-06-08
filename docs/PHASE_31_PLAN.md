# Phase 31 Plan — Real COT/EIA Feature-History Ingestion & Directional Validation

**Goal:** Close the **structural diligence gap**. Today `factor_composite` and
`logreg_directional` run on the *synthetic* seed, whose COT/storage are causally
independent of price — so Phase 26's "no out-of-sample directional edge" is
guaranteed *by construction*, and both multimodal models are `unvalidated` in
`docs/MODEL_DILIGENCE.md`. Phase 31 ingests **real historical COT (CFTC) + EIA
storage**, persists it, and re-runs the *locked* backtest on real point-in-time
features→price to produce a **true verdict**.

**Status:** Drafted 2026-06-08. Base: `fca8718` (post-Phase-30d + contracts resync,
`master == develop == origin`). **Estimated effort:** 31a+31b ≈ 1.5–2 days (the core
diligence answer); 31c conditional, +1–1.5 days.

## Honest framing — diligence-first, prediction-second

This is the one piece standing between *"we think these models work"* and *"we
checked."* The deliverable is an **honest answer**, not a guaranteed edge. Priors say
weekly COT + weekly storage have weak power over daily/weekly *direction*, so the most
likely outcome is **"still no reliable edge — now proven on real data,"** which is
itself a valuable diligence asset (it converts an *assumption* into a *tested claim*).
A genuine directional edge is the **upside**, not the premise. Either way the gap closes.

Gate culture is inherited from 26b/26c/30b: a **pre-registered** honest gate per
sub-phase; if the new thing doesn't beat the honest baseline out-of-sample, we **say so**
and keep the baseline (record the verdict in `MODEL_DILIGENCE.md`).

## What's already done (don't re-do) — the key insight

A code-grounded audit (2026-06-08) found the **look-ahead-safe point-in-time feature
reconstruction already exists** — so this phase is mostly *data*, not *machinery*:

- **Real adapters are built.** `adapters/positioning/cftc.py` → CFTC PRE Socrata
  (`kh3c-gbw2`, disaggregated futures-only, weekly, 6 symbols, **no API key** needed).
  `adapters/energy/eia.py` + `eia_petroleum.py` → EIA Open Data v2 (weekly NG storage +
  petroleum stocks, needs `EIA_API_KEY`). Both return dict shapes matching the mock
  generators (`seeds/cot_generator.py`, `seeds/storage_generator.py`).
- **Tables exist** (`cot_reports`, `eia_storage_reports`; migration `002`), with both
  `report_date` and `release_date` columns — enough for "as-known-then" queries. Head
  migration: `009_merge_heads`.
- **Point-in-time machinery exists & is look-ahead-safe.** `services/backtest.py::
  _context_as_of()` already feeds models `_storage_as_of()` (filters `report_date ≤
  as_of`) and `_cot_as_of()` (filters `release_date ≤ as_of`, computes `mm_net_delta`).
  **`factor_composite` already consumes these correctly** — it can be validated on real
  data the moment the DB is populated, with zero model changes.

## The gap (three things, in order)

| # | Gap | Where | Phase 31 action |
|---|---|---|---|
| 1 | **No real history in the DB** — adapters have no persistence; writes happen only in `seeds/demo.py` with mock data (repos `cot.py`/`eia.py` are read-only) | `repos/`, `seeds/` | 31a — upsert repos + backfill |
| 2 | **No multi-year backfill path** — adapters expose only `get_*_reports(limit=N)` (~latest 200 rows), no date-range/pagination | `adapters/positioning/cftc.py`, `adapters/energy/eia*.py` | 31a — `*_range(start, end)` methods |
| 3 | **`logreg_directional` ignores alt-data** — accepts `latest_storage`/`latest_cot` params but builds **price-only** features. (`factor_composite` does NOT have this gap.) | `services/models/logreg_directional.py` | 31c (conditional) |

---

## 31a — Ingest + persist real history *(the foundation, ~1 day)*

- **Adapter range-fetch:** add `get_cot_reports_range(start, end)` (Socrata `$where` on
  `report_date_as_yyyy_mm_dd`, paginated for ~10y) and `get_storage_reports_range(start,
  end)` (EIA `period` filter). Add the parallel range methods to the **mock** adapters too,
  for protocol parity. Leave the legacy `get_*_reports(limit=N)` intact for the live path.
- **Upsert repo methods:** `repos/cot.py::upsert_many()` + `repos/eia.py::upsert_many()`
  with `ON CONFLICT (report_date, contract_market_name) DO UPDATE` (COT) / `(report_date)
  DO UPDATE` (EIA). The existing UNIQUE constraint is the **idempotency key** — a feature,
  not a flaw: the backfill is safely re-runnable.
- **Backfill command:** `seeds/backfill_features.py`
  (`uv run --directory apps/api python -m seeds.backfill_features [--symbols ...] [--years 10]`)
  — fetch real history via the real adapters → upsert. Rate-limit aware (EIA ~10 req/min;
  CFTC Socrata generous). Manual/cron, **not CI** (needs network + `EIA_API_KEY`), same
  posture as the vol/direction validators.
- **Reuse the existing tables — no redesign.** Bitemporal/hypertable conversion is
  over-engineering for MVP: COT/EIA revisions are rare and immaterial for research, and the
  `release_date` gate already gives "as-known-then." Note hypertable conversion as a future
  refinement only (the tables stay small — ~6 symbols × ~10y × weekly ≈ a few thousand rows).
- **Gate:** backfill populates ≥ ~250 weekly COT rows/symbol + ≥ ~500 EIA rows; idempotent
  re-run produces no dupes; `pnpm health` green; new adapter/repo methods unit-tested.

## 31b — Validate `factor_composite` on real point-in-time features *(the diligence answer, ~1 day)*

- **No model change** — the backtest already feeds `factor_composite` real point-in-time
  storage/COT once the DB is populated.
- **New validator** `seeds/validate_factor_real.py` (mirrors `seeds/validate_direction_real.py`):
  run the **unchanged locked backtest** against the real DB history; report walk-forward
  hit-rate / Brier vs the **drift-naive baseline** and the **price-only models**
  (`moving_average_directional`, `holt_trend`), per commodity, at **1w** (the natural
  horizon — features update weekly; align decision points to post-release days). 1d is a
  stretch and should not be over-claimed (weekly features are stale 4 of 5 days).
- **Pre-registered honest gate:** does real-feature `factor_composite` beat **both**
  drift-naive **and** the price-only models OOS, with a confidence gradient?
  - **PASS** → a real directional edge exists. Write it up; consider a (separate) promotion.
  - **FAIL** → record the honest verdict in `MODEL_DILIGENCE.md` (`factor_composite` real-OOS
    ❌, no edge). **The diligence gap closes either way** — that is the phase's real value.

## 31c — `logreg` with alt-data features *(conditional, ~1–1.5 days — only if 31b is promising)*

- Extend `logreg_directional._features()` to add `storage_delta` + `cot_net_delta`; thread
  `_storage_as_of(date)` / `_cot_as_of(date)` per **training-window point** (currently called
  once per *decision* point — a small loop change in the backtest's training reconstruction).
  Retrain walk-forward (7–8 features), re-validate vs the price-only logreg baseline.
- **Pre-registered honest gate:** alt-data logreg beats price-only logreg OOS, or we say so
  and keep the simpler model benched (same posture as `factor_learned` in 26b).

---

## Key design decisions

- **Reuse schema, don't redesign.** `(report_date, contract_market_name)` UNIQUE is the
  right upsert key; `release_date` already enables look-ahead-safe as-of queries.
- **Weekly cadence → 1w/1m horizons.** Decision points aligned post-release. Daily direction
  with weekly features is structurally weak — don't over-claim it.
- **Universe = the 6 full-tier commodities** (NG, CL, HO, RB, GC, SI) the adapters + COT
  market codes cover.
- **`EIA_API_KEY` required** for the EIA leg (already in the Railway env; needed in
  `apps/api/.env` for a local backfill). CFTC needs no key.
- **Look-ahead safety is already enforced** at the `_context_as_of()` chokepoint — Phase 31
  inherits it; the validator runs the *locked* harness unchanged.

## Risks & caveats

- **Most likely outcome is "no edge, now proven"** — weak weekly features, daily/weekly
  noise. A *success* for diligence, a *miss* for prediction. Set expectations accordingly.
- **Backfill is network/rate-limited** — manual/cron, not CI.
- **COT release timing** (Fri 15:30 ET for Tue-dated data) must be honored in `release_date`
  or you leak ~3 days of look-ahead. The existing `_cot_as_of` gate handles this — verify on
  real data.
- **Production decoupling:** flipping `ADAPTER_POSITIONING=real` / `ADAPTER_ENERGY=real`
  *live* is a **separate** decision from backfilling history for backtests. Keep them apart.

## Sequencing

1. **31a** (ingest + persist) →
2. **31b** (validate `factor_composite`, get the honest verdict) →
3. decide on **31c** based on 31b's result.

31a+31b alone delivers the core diligence value (the tested verdict). 31c is conditional
upside only if 31b shows alt-data signal.

## Open questions to resolve before building

1. Confirm `EIA_API_KEY` is available locally (it's on Railway; needed in `apps/api/.env`).
2. Scope call: ship 31a+31b first (the honest verdict) and treat 31c as a follow-on, or
   commit to the full arc up front?
