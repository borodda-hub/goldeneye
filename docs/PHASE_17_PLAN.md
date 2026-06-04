# Phase 17 Plan — Fill the Thin Tier (HO, RB, GC, SI)

**Goal:** Take the four Phase 16 instruments — **HO** (heating oil), **RB**
(gasoline), **GC** (gold), **SI** (silver) — from *thin tier* (live quote +
chart only) to *data-complete*, so their dashboard cards stop showing empty
or wrong-instrument data. Stop short only where the asset class genuinely
has no honest data source.

**Status:** Drafted 2026-05-18. Base: `e5d39ab` (post-Phase-16 closeout).
**Estimated effort:** ~half to full day.

## What's already done (don't re-do)

Phase 16's live smoke-test follow-ups quietly closed one Phase 17 candidate:

- **Seeded forecasts** — `seeds/example_forecasts.py::seed_forecasts` already
  loops all six symbols (NG, CL, HO, RB, GC, SI) via `demo.py` step 6b
  (commit `2a8415e`). It pulls realized closes from the live market adapter
  when an instrument has no `price_bars`. The Signal Lab history table is
  already non-empty for the quartet. **Phase 17 spot-checks this; it does not
  rebuild it.**

## Thin-tier gap analysis (post-Phase-16)

| Data type | Current state | Phase 17 action |
|---|---|---|
| Quote / chart / switcher / watchlist | ✅ done (Phase 16) | — |
| Signal Lab forecast history | ✅ done (`2a8415e`) | spot-check only |
| News | ⚠️ **wrong content** — `RssNewsAdapter` falls back to `_NG_CONFIG` for unknown symbols, so GC shows natural-gas headlines | 17d — per-symbol configs |
| CFTC positioning | ❌ **empty** — `cftc.py::MARKETS` and `cot_generator` are NG-only | 17b + 17c |
| Energy fundamentals (HO/RB) | ❌ **wrong** — `get_energy()` returns the NG storage adapter for all four | 17a + 17e |
| Energy fundamentals (GC/SI) | ❌ wrong (same fallback) | 17e — honest empty state |

## Approved decisions

1. **HO/RB get real EIA petroleum-product fundamentals.** EIA publishes
   weekly distillate and motor-gasoline stocks; both ride the same
   `petroleum/stoc/wstk/data/` route the Cushing-crude adapter already uses.

2. **GC/SI fundamentals card stays a clean "no data" empty state.** Metals
   have no EIA-style weekly inventory report. Rather than fake one, the
   fundamentals card renders an honest *"No fundamentals for this asset
   class"* state when `instrument.asset_class != "energy"`. A metals macro
   panel (DXY / real yields / FOMC calendar) is a **Phase 18 candidate**,
   not Phase 17.

3. **CFTC positioning for all four.** Both paths get wired:
   - the real `CFTCAdapter` (live `ADAPTER_POSITIONING=cftc`) — extend the
     `MARKETS` code table;
   - the `cot_generator` seed — generalize it to emit per-symbol rows so the
     demo dashboard's positioning card is populated without a live fetch.

4. **News for all four** — per-symbol `SymbolNewsConfig` entries with proper
   feeds and keyword maps. Metals get Kitco + Yahoo metals feeds.

5. **One phase, commit-shaped steps 17a–17f.** Same cadence as Phases 15–16.

6. **This phase touches the frontend** (one small card empty-state — see
   17e). Stated up front; Phase 16's "no frontend code" estimate was wrong
   and that mistake is not repeated here.

## Backend changes

### 17a — EIA petroleum-products fundamentals (HO, RB)

`adapters/energy/eia_petroleum.py` is currently Cushing-crude-specific:
`CUSHING_SERIES` / `TOTAL_EX_SPR_SERIES` are module constants.

Generalize it with a per-symbol series table and a `symbol` constructor arg:

```python
# series IDs verified against EIA Open Data v2 — recheck if EIA reissues
PETROLEUM_SERIES: dict[str, PetroleumSeries] = {
    "CL": PetroleumSeries(primary="WCESTP31",  context="WCESTUS1"),  # Cushing
    "HO": PetroleumSeries(primary="WDISTUS1",  context=None),        # distillate
    "RB": PetroleumSeries(primary="WGTSTUS1",  context=None),        # gasoline
}
```

The `_pivot` output shape (`surprise_bcf`, `net_change_bcf`, `actual_bcf`,
WoW deltas) is unchanged — downstream xgboost stays unit-agnostic. CL keeps
its two-series Cushing+total behavior; HO/RB pivot a single product-stock
series. Existing CL tests must still pass.

### 17b — CFTC market codes for the quartet

Extend `adapters/positioning/cftc.py::MARKETS` with four entries. Codes
**must be verified live against CFTC PRE** before the phase closes
(`16d`-style smoke test) — Socrata occasionally reissues them:

| Symbol | Expected `contract_code` | `name_prefix` | Exchange |
|---|---|---|---|
| HO | `022651` | `NY HARBOR ULSD` (hist. `#2 HEATING OIL`) | NYMEX |
| RB | `111659` | `GASOLINE RBOB` | NYMEX |
| GC | `088691` | `GOLD` | COMEX |
| SI | `084691` | `SILVER` | COMEX |

No other adapter change — `CFTCAdapter(symbol)` already builds per-symbol
instances. This unblocks `get_positioning()` for the quartet (today it
raises `ValueError` for any symbol outside `MARKETS`).

### 17c — Generalize the COT seed generator

`seeds/cot_generator.py::generate()` hardcodes the NG market name, code, and
`OI_BASELINE = 1_400_000`. Parameterize it per symbol — open-interest
baselines differ by an order of magnitude across these markets:

| Symbol | OI baseline (approx) | MM-net band |
|---|---|---|
| NG | 1,400,000 | −150k … +250k |
| CL | 1,800,000 | −100k … +400k |
| HO | 300,000 | −40k … +80k |
| RB | 300,000 | −30k … +90k |
| GC | 500,000 | −50k … +250k |
| SI | 150,000 | −20k … +60k |

`demo.py` step 4 changes from one `generate()` call to a per-symbol loop,
inserting `cot_reports` rows keyed by each market's CFTC code. **Bonus:** CL
gets a COT seed for the first time (it was never in `cot_generator`).

### 17d — Per-symbol news configuration

Add four `SymbolNewsConfig` entries to `adapters/news/rss.py::SYMBOL_CONFIGS`:

- **HO** — EIA Today in Energy + Yahoo `HO=F` + OilPrice; keywords:
  `heating oil, distillate, diesel, ulsd, crack spread, refining, winter
  demand`.
- **RB** — EIA + Yahoo `RB=F` + OilPrice; keywords: `gasoline, rbob,
  refinery, crack spread, driving season, pump price, summer blend`.
- **GC** — Yahoo `GC=F` + Kitco metals RSS; keywords: `gold, bullion, fomc,
  fed, dollar, dxy, real yields, safe haven, central bank`.
- **SI** — Yahoo `SI=F` + Kitco metals RSS; keywords: `silver, bullion,
  industrial demand, solar, gold-silver ratio`.

Extend `_CATEGORY_RULES` with a `monetary` bucket (`fomc, fed, rate cut,
dollar, real yields`) so metals headlines don't all classify as `other`.

### 17e — Adapter routing + the metals empty state

`adapters/registry.py::get_energy()` — route `HO`/`RB` to the generalized
petroleum adapter; `GC`/`SI` return a `NullEnergyAdapter` (empty reports) so
no router 500s.

**Frontend (one card):** the fundamentals card reads `instrument.asset_class`
(already on the `/v1/instruments` payload). When it is not `energy`, render a
*"No fundamentals — metals are not covered by EIA inventory reports"* empty
state instead of calling the energy endpoint. Reuse the existing thin-tier
empty-state pattern (`docs/FRONTEND_COMPONENTS.md`); no new component.

### 17f — Tests

- `tests/test_eia_petroleum_products.py` — HO→`WDISTUS1`, RB→`WGTSTUS1`
  series selection; `_pivot` shape parity with the CL path.
- `tests/test_cftc_markets.py` — `MARKETS` has all six symbols; each
  `CFTCAdapter(sym)` builds without raising.
- `tests/test_cot_generator.py` — per-symbol `generate()` emits rows with the
  right `cftc_contract_market_code` and a plausible OI band.
- `tests/test_news_configs.py` — `SYMBOL_CONFIGS` has all six; GC keyword
  filter rejects a natural-gas headline and keeps a gold one.
- Extend `test_phase16_seed.py` (or add `test_phase17_seed.py`) to assert
  `cot_reports` is populated for the quartet after `demo --fresh`.

## Frontend changes

**One card** (17e): the fundamentals card's metals empty state. Everything
else — watchlist, switcher, news panel, positioning card, Signal Lab — is
already symbol-dynamic and populates automatically once the backend returns
data.

## Acceptance criteria

- [ ] `get_energy("HO")` / `get_energy("RB")` return petroleum-products data;
      `get_energy("GC")` / `get_energy("SI")` return an empty `NullEnergyAdapter`
- [ ] `CFTCAdapter` builds for all six symbols without raising
- [ ] `cot_reports` is seeded for all six symbols after `make seed`
- [ ] News panel shows asset-appropriate headlines for each of the four
      (no natural-gas headlines under GC/SI)
- [ ] Fundamentals card shows real EIA data for HO/RB, honest empty state
      for GC/SI
- [ ] Backend tests stay green
- [ ] Web tests stay green (one card touched in 17e)
- [ ] CFTC codes + EIA series verified live (one curl per symbol)
- [ ] `docs/DATA_SOURCES.md` + `docs/MOCK_DATA_SPEC.md` updated same-commit

## Steps (commit-shaped)

1. **17a** — Generalize `EIAPetroleumAdapter` with a per-symbol series table
2. **17b** — Add HO/RB/GC/SI to `cftc.py::MARKETS`
3. **17c** — Generalize `cot_generator` per symbol; `demo.py` per-symbol loop
4. **17d** — Per-symbol `SymbolNewsConfig` + `monetary` category rule
5. **17e** — `get_energy()` routing + `NullEnergyAdapter` + fundamentals-card
   metals empty state
6. **17f** — Tests + doc updates
7. **17g** — Live smoke-test all four symbols via curl; capture surprises

## Known follow-ups (Phase 18 candidates)

- **Metals macro panel** — repurpose the GC/SI fundamentals card with DXY,
  real yields, and an FOMC calendar. New data source + card variant.
- **EIA petroleum history hypertable** — the petroleum adapter still doesn't
  persist (noted in `eia_petroleum.py`); a backfilled `eia_petroleum_stocks`
  hypertable would let HO/RB join the backtest history properly.
- **More asset classes** — agriculture (ZC/ZS/ZW), treasuries, crypto
  futures. Same thin-tier → fill pattern.

## Closeout (2026-06-04)

Built **backend-only**. Verifying the plan against current code (HEAD `97ca0d7`)
corrected the frontend half:

- **No fundamentals card and no positioning card exist** on the dashboard, so the
  written 17e ("tweak the fundamentals card empty state") had no card to tweak.
  Building those cards is net-new UI → moved to **Phase 18** (cosmetic/usability).
- **The `asset_class != "energy"` gate was buggy** (NG/CL/HO/RB are all
  `commodity`, only GC/SI are `metal`). Dropped entirely: whether a symbol has
  energy fundamentals is now decided by `registry.get_energy()` (→ `NullEnergyAdapter`
  for non-energy), not a UI string compare.
- **News was less broken than stated** — unknown symbols already fell to a generic
  Yahoo per-symbol feed (`_make_default_config`), not literal NG headlines. 17d is
  therefore a quality upgrade (curated Kitco feeds + keyword precision + `monetary`
  category), not a broken→fixed.

As built: 17a `EIAPetroleumAdapter(symbol)` + `PETROLEUM_SERIES`; 17b CFTC `MARKETS`
+ `instruments.json` `cftc_market_code`; 17c per-symbol `cot_generator` (NG
byte-identical) + `demo.py` loop; 17d six `SYMBOL_CONFIGS` + `monetary` rule; 17e
`NullEnergyAdapter` + `get_energy()` routing + `signals.py` generalization. 47 new
tests; backend 711 green; mypy gate clean.

**17g live verification (all passed):**
- CFTC PRE codes: NG 023651→NAT GAS NYME, CL 067651→WTI-PHYSICAL, HO 022651→NY
  HARBOR ULSD, RB 111659→GASOLINE RBOB, GC 088691→GOLD, SI 084691→SILVER.
- EIA series (period 2026-05-29): WCESTP31=252,500, WDISTUS1=102,301 (HO),
  WGTSTUS1=214,955 (RB).
- API: `/v1/signals/current` and `/v1/dashboard/summary` return 200 for all of
  NG/HO/RB/GC/SI (no 500 from the null energy path); GC dashboard news is gold/
  metals (DPM Metals, Gold IRA, Fed/GLD), not natural gas.
