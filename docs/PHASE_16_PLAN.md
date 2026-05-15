# Phase 16 Plan — Watchlist Expansion (HO, RB, GC, SI)

**Goal:** Add four more commodities — **HO** (heating oil), **RB** (gasoline),
**GC** (gold), **SI** (silver) — to the watchlist at the *thin tier*: live
Yahoo price, candlestick chart, instrument switcher entry, watchlist quote.
Demo gets dramatically denser without architectural change.

**Status:** Drafted 2026-05-14. Base: `7d22cc2` (post-deploy-prep).
**Estimated effort:** ~90 minutes.

## Approved decisions

1. **Thin tier only.** No forecasts, no positioning, no journal/paper-trade
   seed for these four. The dashboard cards for those features will show
   "no data" / empty states — same as any non-NG/CL instrument would today.

2. **Energy fundamentals** (EIA petroleum) extends to **HO and RB** for free
   if we're willing to map their EIA series codes. **Out of scope** for
   Phase 16 — flagged as a follow-up. Their cards will read "no fundamentals."

3. **Metals exchange suffix.** GC and SI trade on COMEX (`.CMX`), not NYMEX
   (`.NYM`). Extend `contract_to_yahoo_symbol` to take an exchange suffix
   sourced from `instruments.metadata.yahoo_exchange_suffix` (default `.NYM`).
   Keeps the adapter generic for future asset classes.

4. **Contract chain depth.** Seed 6 front-month contracts per instrument
   (matches the NG/CL precedent — enough for a one-year curve view, doesn't
   bloat the seed). Live curve fetch fills the rest as needed.

5. **Positioning (CFTC).** Out of scope. The CFTC adapter is already
   generalized (Phase 14 step 3) and would only need each commodity's
   market code, but mapping + verifying that against the COT report
   schema is a separate ~30 min per commodity. Defer.

6. **No `useActiveInstrument` changes.** It already accepts arbitrary
   symbols from the URL / localStorage. Watchlist and switcher both
   render whatever `/v1/instruments` returns. Frontend is fully dynamic.

## Backend changes

### 16a — Adapter: exchange-suffix indirection

`adapters/market/yahoo_delayed.py::contract_to_yahoo_symbol` currently
hardcodes `.NYM`. Two-line change:

```python
def contract_to_yahoo_symbol(
    contract_code: str | None,
    symbol: str = "NG",
    exchange_suffix: str = ".NYM",
) -> str:
    ...
    return f"{code}{exchange_suffix}"
```

Callers (curve fetch, bar fetch) read the suffix from the instrument's
`metadata["yahoo_exchange_suffix"]` and pass it through. Default stays
`.NYM` so NG/CL/HO/RB keep working without metadata changes.

### 16b — Seed: 4 new instruments + 24 contracts

Alembic migration 00X seeds:

| Symbol | Name | Asset class | Unit | Tick | Yahoo exchange |
|---|---|---|---|---|---|
| HO | NY Harbor ULSD (Heating Oil) | energy | gallon | 0.0001 | `.NYM` |
| RB | RBOB Gasoline | energy | gallon | 0.0001 | `.NYM` |
| GC | Gold | metal | troy oz | 0.10 | `.CMX` |
| SI | Silver | metal | troy oz | 0.005 | `.CMX` |

Plus 6 contract rows per instrument (front 6 months from today). Initial
`is_front_month=True` flag on the nearest non-expired contract per symbol.

Reuse the existing `seeds/contract_chain.py` helper that Phase 14 used
for CL — just call it 4 more times.

### 16c — Tests

`tests/test_yahoo_symbol_mapping.py` — extend with cases for the new
symbols:
- `contract_to_yahoo_symbol("HOM26", "HO", ".NYM")` → `"HOM26.NYM"`
- `contract_to_yahoo_symbol("GCM26", "GC", ".CMX")` → `"GCM26.CMX"`
- Continuous fallback: `contract_to_yahoo_symbol(None, "SI")` → `"SI=F"`

`tests/test_phase16_seed.py` — verifies the migration seeds 4 instruments
and ≥6 contracts each, and that `instruments.metadata.yahoo_exchange_suffix`
is set correctly for GC and SI.

## Frontend changes

**None expected.** The watchlist (`WatchlistSidebar`) and switcher
(`InstrumentSwitcher`) both query `/v1/instruments` and render whatever
comes back. Adding rows to the table populates them automatically.

Spot-check after seed:
- `/dashboard?symbol=HO` should load the chart with live HO bars
- The watchlist shows all 6 symbols (NG, CL, HO, RB, GC, SI) with live quotes
- The InstrumentSwitcher dropdown includes all 6

## Acceptance criteria

- [ ] `GET /v1/instruments` returns 6 rows (was 2)
- [ ] All 4 new symbols have non-empty live quotes from Yahoo
- [ ] Chart page loads candlesticks for each at the 1d resolution
- [ ] Indicators endpoint works for each (proves the front-month resolution
      + market-adapter pull from the indicators fix still applies)
- [ ] Backend tests stay green
- [ ] No new frontend code; web tests stay green
- [ ] Yahoo's `=F` and `<contract>.CMX` mappings verified live (one curl
      per symbol)

## Steps (commit-shaped)

1. **16a** — `contract_to_yahoo_symbol` takes optional `exchange_suffix`,
   curve + bar callers pass it through from instrument metadata
2. **16b** — Alembic migration: seed HO/RB/GC/SI instruments + 24 contracts
3. **16c** — Tests: Yahoo symbol mapping cases + seed verification
4. **16d** — Live smoke-test all 4 symbols via curl, capture any surprises

## Known follow-ups (Phase 17 candidates)

- **EIA fundamentals for HO and RB** — add petroleum-product series codes
  to the petroleum adapter. ~20 min per symbol.
- **CFTC positioning for the energy + metals quartet** — look up each
  market code, extend the adapter's symbol map. ~30 min per symbol.
- **Seeded forecasts + backtests** — run the existing model seed generators
  with the new symbols so Signal Lab / Backtest cards aren't empty for
  them. ~15 min per symbol.
- **News keyword maps** — per-symbol RSS filter terms (e.g. for GC:
  "gold, bullion, FOMC, dollar"). The RSS adapter already supports per-symbol
  filtering; just needs the keyword dictionary extended.
- **More asset classes** — agriculture (ZC corn, ZS soybeans, ZW wheat),
  treasuries (ZB, ZN), crypto futures (BTC). Same thin-tier pattern.
