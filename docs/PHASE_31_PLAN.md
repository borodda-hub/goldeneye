# Phase 31 Plan (v2) — Real COT/EIA Feature-History Ingestion & Directional Validation

**Goal:** Close the **structural diligence gap**. Today `factor_composite` and
`logreg_directional` run on the *synthetic* seed, whose COT/storage are causally
independent of price — so Phase 26's "no out-of-sample directional edge" is
guaranteed *by construction*, and both multimodal models are `unvalidated` in
`docs/MODEL_DILIGENCE.md`. Phase 31 ingests **real historical COT (CFTC) + EIA
storage**, persists it, and re-runs the *locked* harness on real point-in-time
features→price to produce a **true verdict**. It also resolves **issue #13**
(prod EIA configured-real but serving stale mock) as a decoupled final step.

**Status:** v2, revised 2026-07-24 after a full code audit of the 2026-06-08 draft.
Base: `b2d60f0` (`master == develop == origin`, post-B5/theme/responsive arc; head
migration **`011_decision_ledger`**). **Scope decision (owner-agreed): ship
31a.0 → 31a → 31b; 31c strictly conditional on 31b; 31d (prod flow, #13) is a
separate promotion.** Estimated effort: 31a.0+31a+31b ≈ **2.5–3 days**
(revised up from 1.5–2 — the audit found correctness pre-fixes and adapter
pagination work the v1 plan assumed away); 31d ≈ 0.5 day; 31c +1–1.5 days if it fires.

## v2 changelog (what the audit corrected — read before building)

The v1 draft's "already done, don't re-do" section was verified against current
code. Four claims failed or drifted; they reshape the change set:

1. **"`factor_composite` validates with zero model changes" — FALSE.**
   `services/models/factor_composite.py:43-44` does
   `float(latest_storage["delta_vs_consensus"])`; `_storage_as_of()` always returns
   the key, as **`None`** on real data, because the real EIA adapter never populates
   `surprise_bcf` (`adapters/energy/eia.py:147-148` — EIA publishes no analyst
   consensus; the mock generator fabricates one). Real backfill → `TypeError`.
   → fixed in **31a.0** with a consensus-free surprise proxy, not a bare guard
   (a guard alone silently kills the storage leg of the very model under test).
2. **The as-of context queries are symbol-blind — undocumented blocker.**
   Neither `_cot_as_of()` (`services/backtest.py:270-274`) nor `_storage_as_of()`
   filters by market/series; `mm_net_delta` is computed from the global two most
   recent rows across *all* commodities. Already subtly wrong on the 6-symbol seed;
   catastrophically wrong on a 6-symbol real backfill (COT release dates collide).
   `repos/cot.py:11` already has the market filter param — the backtest doesn't use
   it. Any 31b verdict produced before this fix measures a bug. → **31a.0**.
3. **`eia_storage_reports` has NO `release_date` column** (v1 claimed both tables
   had one; only `cot_reports` does — `002_relational.py:52-53` vs `:73-74`). NG
   storage is look-ahead-safe *by naming accident*: the NG adapter sets
   `report_date` to the publication Thursday (`eia.py:139-140`). But
   **`eia_petroleum.py:177` sets `report_date = week_ending`** — loading petroleum
   stocks into this table leaks ~5 days through the `report_date <= as_of` gate.
   → petroleum is **excluded from 31a scope** (see design decisions).
4. **Adapter ceilings are harder than v1 implied.** CFTC `_fetch_all()` is
   hard-pinned to `$limit=200` (~3.8y ceiling, no `$offset`, `limit=N` applied
   client-side); EIA NG capped at `length=1100` ≈ 2.3y. The `*_range()` methods are
   required, with real pagination. Also: `eia.py:156` leaves `net_change_bcf=None`
   on the oldest fetched row → violates the table's NOT NULL (`002_relational.py:60`).

Plus two assets v1 didn't know about:
- **`seeds/validate_engine_oos.py`** (2026-06-28) already scores all five voters +
  ensemble on ~10y real Yahoo closes, every metric beside its baseline, and runs
  `factor_composite`/`logreg` **price-only** as the flagged-unvalidated control arm
  (`:26-29`, `:102-103`). **31b extends this file** rather than writing a new
  `validate_factor_real.py` mirror — the price-only control comparison comes free.
- **`services/price_backfill.py`** is a complete idempotent backfill template
  (adapter → `on_conflict_do_nothing`, `BackfillResult` accounting, guarded
  `replace_mock`); `seeds/backfill_prices.py` is the CLI pattern;
  `repos/users.py:15-50` is the repo `on_conflict_do_update` idiom. 31a copies
  these, it does not invent.

## Honest framing — diligence-first, prediction-second (unchanged from v1)

The deliverable is an **honest answer**, not a guaranteed edge. Priors say weekly
COT + weekly storage have weak power over daily/weekly *direction*; the price-only
control arm is already proven no-edge real-OOS (36/36 cells, `MODEL_DILIGENCE.md`).
Most likely outcome: **"still no reliable edge — now proven on real data"** — a
diligence asset either way. A genuine edge is the upside, not the premise. Gate
culture inherited from 26b/26c/30b: pre-registered gates; if the model fails, we
say so, bench it, and record the verdict in `MODEL_DILIGENCE.md` (S4).

## What's verified-still-true (the machinery we inherit)

- `adapters/positioning/cftc.py` — Socrata `kh3c-gbw2`, no key, 6 markets
  (NG/CL/HO/RB/GC/SI), emits `report_date` + `release_date = report_date + 3d`
  (Tue→Fri, correct lag), keys match `seeds/cot_generator.py`.
- `cot_reports` UNIQUE `(report_date, contract_market_name)` — the right upsert /
  idempotency key. `eia_storage_reports` UNIQUE `(report_date)`.
- `_cot_as_of()` gates on **`release_date <= as_of`** with a hard `RuntimeError`
  look-ahead assert (`backtest.py:272-280`) — the Friday-release lag is honored.
- `repos/cot.py` / `repos/eia.py` are read-only; writes happen only in
  `seeds/demo.py` (mock). Nothing of 31a pre-exists — gaps confirmed.
- `logreg_directional` accepts `latest_storage`/`latest_cot` and ignores both
  (price-only 5-feature `_features()`, `inputs_used=["closes"]`) — the 31c gap.
- `_context_as_of()` (`backtest.py:291-303`) is the single point-in-time chokepoint;
  the S3 cheating-model proof covers it.

---

## 31a.0 — Correctness pre-fixes *(new; prerequisite for a meaningful verdict, ~0.5 day)*

Small, but each is load-bearing. All three get regression locks (S5).

1. **Symbol-scope the as-of context.** `_cot_as_of(session, as_of, market)` filters
   by the instrument's COT market name (the `repos/cot.py` filter param exists);
   `mm_net_delta` becomes a same-market delta. For storage: **[V]erify first**
   whether `eia_storage_reports` rows are distinguishable per commodity/series
   (column audit) — if the table is NG-national-storage-only today, scoping is a
   no-op to codify + assert; if mixed series are possible, add the discriminator
   before backfilling. **Lock:** a testcontainer test seeding two markets with
   colliding release dates and asserting the delta never crosses markets
   (fail-without/pass-with, the B3a landmine pattern).
2. **`factor_composite` consensus-free surprise proxy.** Replace the
   `delta_vs_consensus` dependency with **`delta_vs_5yr_seasonal_norm`** (actual
   weekly change vs the 5-year average change for that calendar week — the standard
   consensus-free surprise definition, computable point-in-time from the table
   itself). Keep the consensus path when the field is present (mock/backward
   compat); guard `None` so absence degrades to neutral, never `TypeError`.
   Label the proxy swap in `MODEL_DILIGENCE.md` (S7). **Lock:** unit test —
   real-shaped row (`surprise_bcf=None`) produces a finite score; proxy math
   verified on a known fixture.
3. **Petroleum `report_date` trap.** 31a scope **excludes** `eia_petroleum.py`
   backfill (see design decisions). Land a guard now anyway: fix
   `eia_petroleum.py:177` to map `report_date` to the *release* date (Wed for the
   Weekly Petroleum Status Report) so the trap can't bite a future phase, and drop
   the extra non-table keys at the adapter boundary. **Lock:** adapter unit test on
   the date mapping.
4. **`net_change_bcf` NOT NULL fix.** Compute the oldest row's change from the
   fetch overlap or drop the boundary row at the adapter — never insert NULL.

**Gate:** `pnpm health` green; S3 proof unchanged-and-green (the chokepoint
signature changes, the invariant must not); new locks red→green demonstrated.

## 31a — Ingest + persist real history *(~1 day)*

- **Adapter range-fetch with real pagination:**
  `get_cot_reports_range(start, end)` — Socrata `$where` on
  `report_date_as_yyyy_mm_dd` + `$offset` paging (the current hard `$limit=200`
  ceiling goes away for the range path; the legacy latest-N path stays intact).
  `get_storage_reports_range(start, end)` — EIA `period` start/end + offset paging
  past the `length` cap. Mirror both on the **mock** adapters for protocol parity.
- **Upsert repos:** `repos/cot.py::upsert_many()` (`ON CONFLICT (report_date,
  contract_market_name) DO UPDATE`) and `repos/eia.py::upsert_many()`
  (`ON CONFLICT (report_date) DO UPDATE`) — copy the `repos/users.py` idiom.
- **Backfill command:** `seeds/backfill_features.py`
  (`uv run --directory apps/api python -m seeds.backfill_features [--symbols ...] [--years 10]`)
  — modeled on `services/price_backfill.py` + `seeds/backfill_prices.py`
  (BackfillResult accounting, idempotent, rate-limit aware: EIA ~10 req/min,
  Socrata generous). Manual/cron, **not CI** (network + `EIA_API_KEY`), same
  posture as the `validate_*_real` diagnostics.
- **Scope: COT for all 6 commodities + EIA weekly NG storage.** No petroleum
  backfill this phase (31a.0 §3). No schema redesign — the existing tables +
  UNIQUE keys are the idempotency mechanism (v1's judgment holds).
- **Gate (pre-registered):** ≥ ~450 weekly COT rows/symbol (~10y; the old 200-row
  ceiling demonstrably broken) + ≥ ~500 weekly NG storage rows; re-run inserts 0
  new rows (idempotency proven); adapter/repo methods unit-tested with mocked
  HTTP; `pnpm health` green.

## 31b — The verdict: `factor_composite` on real point-in-time features *(~1 day)*

- **Harness = extend `seeds/validate_engine_oos.py`**, not a new file: add an
  **alt-data-fed arm** — `factor_composite` receiving real `_storage_as_of()` /
  `_cot_as_of()` context (post-31a.0, symbol-scoped) — printed in the same
  one-table scorecard beside its price-only control arm and every baseline.
- **Price source:** ~10y direct Yahoo fetch (the established validator
  convention), joined to DB features via the as-of gates. The DB's `price_bars`
  real depth is only ~730 days (`DEFAULT_LOOKBACK_DAYS`) — too thin for the
  verdict; do **not** silently run on it.
- **Decision points:** aligned post-release (COT: Fridays after 15:30 ET;
  storage: Thursdays), horizons **1w and 1m**. 1d is explicitly out of scope
  (weekly features are stale 4 of 5 days — don't over-claim).
- **Pre-registered honest gate (locked before the first run):** real-feature
  `factor_composite` must beat **both** the drift-naive baseline **and** the best
  price-only model on **OOS Brier at 1w**, with the difference exceeding ~1 SE on
  `n_eff` non-overlapping windows (the 26b/30b comparison discipline — a hot
  sample is not crowned), **and** show a monotone confidence gradient.
  - **PASS** → a real directional edge exists; write it up; promotion is a
    *separate* decision; 31c unlocks.
  - **FAIL** → `MODEL_DILIGENCE.md` records `factor_composite` real-OOS ❌ no-edge;
    the model's directional claim is honestly retired per S4. **The diligence gap
    closes either way — that is the phase's value.**
- **Provenance:** verdict + run parameters recorded in `MODEL_DILIGENCE.md`
  (§directional row moves out of `unvalidated` in the same commit, S7).

## 31c — `logreg` with alt-data features *(conditional — only if 31b passes)*

Unchanged posture from v1 (extend `_features()` with `storage_delta` +
`cot_net_delta`, per-training-point as-of reconstruction, walk-forward retrain,
pre-registered gate vs price-only logreg; bench-and-say-so on failure). One
revision: if 31c fires, **weather degree-day features rank ahead of COT** in the
candidate queue (forward-looking demand shock vs backward-looking positioning) —
see `MASTER_PLAN.md` Stage D5 for the data-collection prerequisite.

## 31d — Prod EIA flow + observed-derived caveat *(issue #13, ~0.5 day, separate promotion)*

Decoupled from the backfill on purpose (v1's "production decoupling" rule holds):
31a fills *history* for backtests; 31d makes *live* storage flow in prod.

- Wire a scheduled refresh so `/v1/fundamentals?symbol=NG` serves
  `source:"eia"` with a current `as_of` (reuse the B1 env-gated scheduler
  pattern; off by default, `EIA_REFRESH_*` settings).
- Make `data_provenance_caveat()`'s storage clause **observed-derived** (the
  HANDOFF-flagged fragility: once real storage flows, the hardcoded
  "illustrative storage" clause would *understate* the product). Extend
  `tests/test_provenance_caveat.py` for the real-storage configuration.
- **Acceptance = issue #13's:** prod fundamentals `source:"eia"` + fresh `as_of`;
  caveat tracks reality in both states. Close #13 on promotion.

---

## Key design decisions (v2)

- **Petroleum excluded from 31a.** Kills the `report_date = week_ending` leak
  risk at zero cost to the verdict (NG is the feature-richest symbol and the
  storage leg only exists for NG); CL/HO/RB `factor_composite` runs COT-only,
  which is honest and labeled. Petroleum backfill re-enters only with the 31a.0
  release-date mapping already landed.
- **Proxy over guard** for the consensus surprise — a dead storage leg would make
  the 31b "verdict" a test of half a model.
- **Extend the existing scorecard** (`validate_engine_oos.py`) — one table, every
  arm beside its baseline, no way for the new arm to flatter itself.
- **Weekly cadence → 1w/1m horizons; 1d out of scope.** (v1, reaffirmed.)
- **Universe:** COT = 6 commodities; storage = NG. ES/ZN stay out (no COT
  disaggregated coverage mapped; B5 carve-outs remain labeled hand-set).
- **`EIA_API_KEY`** resolved (in `apps/api/.env`, validated live). CFTC keyless.

## Risks & caveats

- Most likely outcome remains "no edge, now proven" — set expectations.
- Backfill is network/rate-limited — manual/cron, never CI (S5's
  network-dependent-diagnostic posture; CI keeps the synthetic locks).
- COT/EIA *revisions* are rare and immaterial for research (v1 judgment holds;
  bitemporal redesign stays out of scope).
- Socrata/EIA schema drift over a 10y window — the range fetchers must validate
  row shape and fail loudly, not coerce.
- 31d touches prod behavior — S8 two-lane, owner sign-off, and the caveat test
  matrix must cover both observed states before the flip.

## Sequencing & gates summary

1. **31a.0** (pre-fixes + locks) → 2. **31a** (backfill, idempotency proven) →
3. **31b** (pre-registered verdict → `MODEL_DILIGENCE.md`) → 4. decide **31c**
from the verdict → 5. **31d** (prod flow + caveat, separate promotion, closes #13).

Universal DoD per `MASTER_PLAN.md §7.4` applies to every step: `pnpm health`
green · S3 proof green · S4 provenance recorded · S5 locks added · S6 claims
gate on any surface change · S7 docs in-commit · `feat/phase-31-*` → `develop`
→ owner-signed `master` promotion.

## Open questions

1. ✅ RESOLVED: `EIA_API_KEY` set + validated (v1).
2. ✅ RESOLVED (2026-07-24): scope = 31a.0+31a+31b now; 31c conditional; 31d
   separate. (Owner agreed after the v2 audit.)
3. ✅ RESOLVED (2026-07-24, [V] column audit): `eia_storage_reports` has **no
   per-series discriminator** — every column is Lower-48 NG national storage
   (`models/orm/eia.py`: report_date UNIQUE, regional `*_bcf` fields). The
   table is structurally NG-only → no migration; 31a.0 codified the guard as
   `_storage_as_of`'s NG-only gate (locked in `tests/db/test_context_scoping.py`).
   Petroleum stays out of this table (its adapter docstring already says so).

## 31a.0 status — ✅ SHIPPED (2026-07-24, `feat/phase-31a0-prefixes`)

All four items landed with locks; `pnpm health` green (974 backend / 420 web),
gated `tests/db` green (46, incl. the two new real-SQL scoping locks):
1. Symbol-scoped context — `_cot_as_of(market_code)` required + filtered;
   `_storage_as_of(symbol)` NG-only; `_context_as_of` maps symbol→market via
   the adapter `MARKETS` table (ES/ZN → no COT, no NG storage). Locks:
   `test_cot_as_of_filters_by_market_code` (fail-without/pass-with) +
   `tests/db/test_context_scoping.py`.
2. Seasonal-surprise proxy — `services/storage_features.py::delta_vs_seasonal_norm`
   (5y norm, min 3 years, ±1 ISO-week tolerance); wired into `_storage_as_of`
   AND the live signals path; `factor_composite` prefers consensus, falls back
   to the labeled proxy, and never crashes on None (TypeError regression locked).
   LLM prompt line labels the proxy honestly.
3. Petroleum `report_date` = publication (week_ending + 5, WPSR Wednesday) —
   leak defused before any future persistence; date-mapping lock added.
4. EIA NG adapter drops the no-delta boundary row (NOT NULL insertable shape).
Note: pre-31a.0 persisted multi-symbol backtest rows contained contaminated
context (see `MODEL_DILIGENCE.md`) — refresh persisted backtests after this
promotes, before citing factor_composite calibration numbers.
*(Done 2026-07-25: 31a.0 promoted to master; backtest refresh re-run on BOTH
the dev DB (6 symbols) and prod (NG) — see HANDOFF.)*

## 31a status — ✅ SHIPPED (2026-07-25, `feat/phase-31a-backfill`)

**All pre-registered gates met on the dev DB:**
- `cot_reports`: **522 real weekly reports/symbol × 6 markets = 3,132 rows**
  (2016-07-26 → 2026-07-21, gate was ≥450) — pure real (`source='cftc'`),
  every mock row replaced. `eia_storage_reports`: **521 real weekly NG rows**
  (2016-07-29 → 2026-07-17, gate ≥500), mock overwritten in place.
- **Idempotency proven:** immediate re-run → net-new 0 on both tables
  (measured as table-rowcount delta; DO UPDATE refreshes values in place).
- Latest rows sanity-real: NG managed-money net −102,694 (release_date =
  the actual Friday), summer injection builds (+32/+41/+61 Bcf → 3,056 Bcf).

**Built:** paginated `get_cot_reports_range` (Socrata `$where`+`$offset`,
kills the 200-row ceiling) + `get_storage_reports_range` (EIA v2 start/end +
offset paging; fetch padded 2 weeks so the oldest requested week keeps its
WoW change) — mirrored on the mock adapters + protocols (null/petroleum =
parity stubs; petroleum stays deliberately un-backfilled). Upsert repos
`cot.upsert_many` / `eia.upsert_many` (chunked `ON CONFLICT DO UPDATE` on
the tables' UNIQUE keys, column-whitelisted). CLI
`seeds/backfill_features.py` (`--symbols`, `--years 10`; replace-mock +
loud per-market duplicate guard; manual/cron, not CI).

**Discovery — live CFTC adapter was silently broken for NG/CL (fixed):**
Socrata renamed the dataset's market names (NG → `"NAT GAS NYME"`, CL →
`"WTI-PHYSICAL"`), so the adapter's defensive `contract_market_name like`
clause matched **zero rows dataset-wide** for both — the live adapter
returned empty and callers fell back to mock (**this explains issue #13's
observed-mock positioning in prod**). Both query paths now filter by the
stable `cftc_contract_market_code` ONLY (never re-add a name filter). The
name instability also means mock long-names don't collide with real
short-names on the `(report_date, contract_market_name)` upsert key — the
backfill therefore purges non-`cftc` rows per market post-fetch and FAILS
LOUDLY if any `(market, report_date)` ends up duplicated (name-churn guard).
A future `UNIQUE (report_date, cftc_contract_market_code)` migration is the
durable fix if churn ever recurs — deferred, guard suffices.

**Known nit:** EIA's three 5-yr stat series (`NW2_EPG0_SAO/SMX/SMN_R48_BCF`)
return nothing on this route — `five_year_avg/max/min_bcf` are NULL on real
rows (regional splits populate fine). Not load-bearing: the consensus-free
proxy derives its own 5-yr norm from `net_change_bcf` history (31a.0).

**Next: 31b** — alt-data arm of `seeds/validate_engine_oos.py` on this real
feature history, pre-registered gate per §31b above.

## 31b status — ✅ RUN, GATE **FAIL** (2026-07-25) — the honest verdict, recorded

Built as planned: a weekly (Friday, post-release) alt-data arm inside
`validate_engine_oos.py` (`--alt-only` for a fast re-run), feeding
`factor_composite` REAL point-in-time features through the **locked
symbol-scoped chokepoint** (`_cot_as_of`/`_storage_as_of`), horizons 1w/1m,
against drift-naive + all four price-only arms at the SAME decision points.
Feature depth extended to **14y** first (`backfill_features --years 14`:
731 COT rows/symbol, 730 storage rows) so the seasonal-norm proxy is warm
across the whole 10y price sample. Coverage: 2,964 decision points, COT at
100%, storage delta at 494 (NG, as designed).

**Pre-registered gate (OOS Brier @1w, paired, n=2,958 non-overlapping):**
- vs drift-naive: **+0.00487 ± 0.00156 — WORSE by ~3 SE** (gate needed better)
- vs best price arm (its own price-only variant): **+0.00536 ± 0.00089 —
  WORSE by ~6 SE**
- decisive hit 48.4% vs base 53.3%; worse-than-drift in 5/6 commodities
  (CL −0.0006, within noise); confidence gradient unreadable (one tier).

**VERDICT: FAIL — real COT/storage add no 1w/1m directional edge through
these rules; they actively hurt.** Recorded in `MODEL_DILIGENCE.md`
(directional lineup now fully real-OOS tested, no edge anywhere; the
structural gap is CLOSED). Most-likely outcome realized — a diligence win,
a prediction miss, exactly as framed in §honest framing.

## 31c — ✋ CLOSED, does not fire

Its pre-registered condition ("only if 31b is promising") was not met.
`logreg` stays price-only (already real-OOS tested, no edge). No alt-data
logreg will be built off this evidence.

## Remaining in Phase 31: only **31d** (prod EIA flow + observed-derived
caveat + prod feature backfill together — issue #13; separate promotion).
Note (correcting an earlier assumption): `/v1/positioning` reads the **DB**
(`services/positioning.py` → `cot_repo`), not the live adapter — so prod
positioning stays mock until 31d's prod backfill, which is the correct
ordering (the caveat must flip in the same promotion as the data).
