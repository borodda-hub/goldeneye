# Phase 14 Plan — Multi-Asset (WTI Crude)

**Goal:** Add **WTI Crude (CL)** as a second instrument alongside Natural Gas
(NG), proving the multi-asset abstraction. Watchlist sidebar on Dashboard.
Active instrument routes through every page. Adapter parity: CL gets its own
market / energy-stocks / positioning / news feeds.

**Status:** Approved 2026-05-12. Base: `23e6b42` (post-Phase 13.8 LLM fixes).

## Approved decisions

1. **Active-instrument state:** URL query param (`?symbol=CL`) primary,
   `localStorage` fallback when the param is absent. Switching instruments
   pushes a new URL; persistence survives reloads + cross-page navigation.

2. **Switcher UI:** Watchlist sidebar on the Dashboard left rail (matches
   the deck's slide-4 mockup) showing each instrument's last price + change.
   On every other page, a compact dropdown next to the page title.

3. **Adapter scope: full NG parity.** CL gets:
   - **Market** — Yahoo `CL=F` delayed (same `yahoo_delayed` adapter,
     parameterized)
   - **Energy stocks** — EIA Weekly Petroleum Status Report (crude oil
     stocks at Cushing, OK as the canonical NG-storage analogue)
   - **Positioning** — CFTC COT WTI Crude Oil (managed-money net)
   - **News** — RSS feeds with CL-specific keyword filter
   - **Weather** — N/A (skip, mark on the Adapter Health page as
     "not applicable")

## Schema changes

The `instruments`, `contracts`, and downstream tables already key on
`instrument_id`. Phase 14 is **additive** — no new tables, just new rows
and adapter generalization. Migration 007 seeds CL.

```sql
-- Migration 007 — seed CL instrument + initial contract
INSERT INTO instruments (id, symbol, name, exchange, asset_class, currency,
                         unit, contract_size, tick_size, metadata)
VALUES (
  gen_random_uuid(),
  'CL',
  'WTI Crude Oil',
  'NYMEX',
  'commodity',
  'USD',
  'barrel',
  1000,           -- contract_size
  0.01,           -- tick_size
  '{}'::jsonb
)
ON CONFLICT (symbol) DO NOTHING;
```

Front-month contract codes follow CME conventions: `CLM26` (June 2026),
`CLN26` (July), etc. Seeded by the demo seed script (Step 14.8).

## REST contract impact

Routes that already accept `?symbol=` keep working. The ones currently
hardcoded to NG need a `?symbol=` parameter and an `Instrument not found`
fallback. Audit list:

- `GET /v1/dashboard/summary` — already accepts `symbol`, verify
- `GET /v1/signals/current`, `/history` — already accepts `symbol`, verify
- `GET /v1/signal-quality` — already accepts `symbol`, verify
- `GET /v1/chart/curve`, `/bars` — already accepts `symbol`
- `GET /v1/calibration`, `/coaching` — already accepts `instrument_code`
- `GET /v1/thesis/current`, `/seed`, `POST /v1/thesis` — already accepts
  `instrument_code`
- `GET /v1/journal` — currently lists across instruments; add `?symbol=`
  filter
- `GET /v1/paper-trades` — currently across instruments; add `?symbol=`
- `GET /v1/scenarios/runs`, `/templates` — add `?symbol=` filter
- `GET /v1/admin/data-health` — already lists across adapters; add
  per-instrument grouping
- `GET /v1/backtest`, `/summary` — already accepts `symbol`, verify

New route: `GET /v1/instruments` → list of available instruments
with `{symbol, name, asset_class, last_price, change_pct}` for the
watchlist sidebar.

## Adapter generalization

**Market — `yahoo_delayed`:** Already supports arbitrary Yahoo symbols;
make sure the resolution map includes the symbol-→-Yahoo-ticker
translation (`NG=F`, `CL=F`). Parameterize per-instrument adapter
selection via `ADAPTER_MARKET_NG`, `ADAPTER_MARKET_CL` env vars; fall
back to `ADAPTER_MARKET` global.

**Energy — `eia`:** Natural gas storage uses series `NG.NW2_EPG0_SWO_R48_BCF.W`.
Crude oil stocks at Cushing use `PET.W_EPC0_SAX_YCUOK_MBBL.W` (Weekly Crude
Oil Ending Stocks Excluding SPR, Cushing). New service module
`apps/api/adapters/energy/eia_petroleum.py` mirroring `eia_natural_gas.py`,
both implementing `EnergyDataAdapter`.

**Positioning — `cftc`:** Existing adapter already pulls the disaggregated
report. CFTC market codes:
- NG: `023651` (Natural Gas Henry Hub)
- CL: `067651` (WTI Crude Oil)
Parameterize the adapter to take a symbol and look up the code.

**News — `rss`:** Same EIA Today + Yahoo Finance + NWS feeds, but
keyword filter changes per symbol. NG keywords: gas, lng, storage,
weather. CL keywords: crude, oil, opec, refinery, distillate, gasoline.
NWS feed is gas-specific so it gets capped to 0 items for CL.

## Frontend changes

### State

New hook `apps/web/lib/useActiveInstrument.ts` returning
`[activeSymbol, setActiveSymbol]`. Reads `?symbol=` from the URL; if
absent, reads `localStorage['goldeneye:active-instrument']`; if absent,
defaults to `'NG'`. `setActiveSymbol(next)` pushes a new URL via
`useRouter` and updates `localStorage`.

### Components

- `WatchlistSidebar` (Dashboard left rail, ~200px wide) — list of
  rows: symbol bold, name muted, last price tabular-nums right-aligned,
  change_pct color-coded. Active instrument highlighted with the same
  gold accent border-l used elsewhere. Click → `setActiveSymbol`.
- `InstrumentSwitcher` (compact dropdown for non-dashboard pages) —
  rendered in the page-header strip. Same data source as the sidebar.
- `useInstruments` query hook → `GET /v1/instruments`

### Wiring

Every page that currently calls `useDashboardSummary("NG")` etc.
switches to `useDashboardSummary(activeSymbol)`. Server-side prefetch
in `page.tsx` reads the URL search params (`searchParams.symbol`).

### Routes

Add `/calibration?symbol=CL` etc. handling. No new routes — `?symbol=`
is the universal switch.

## Effort breakdown

| Step | Scope | Estimate |
|---|---|---|
| 14.1 | Migration 007 + CL seed in `instruments_seed.py` + 4 contract rows + tests | 0.5d |
| 14.2 | Yahoo market adapter — per-symbol selection + env wiring + tests | 0.5d |
| 14.3 | CFTC adapter — parameterize symbol → market-code map + tests | 0.5d |
| 14.4 | EIA Petroleum adapter (new) — Cushing stocks + tests | 1d |
| 14.5 | RSS news filter — per-symbol keyword sets + tests | 0.5d |
| 14.6 | `GET /v1/instruments` route + audit existing endpoints for `?symbol=` filter | 0.5d |
| 14.7 | `useActiveInstrument` hook (URL + localStorage) + tests | 0.5d |
| 14.8 | `WatchlistSidebar` + `InstrumentSwitcher` components + tests | 1d |
| 14.9 | Wire activeSymbol through all 8 pages + server-prefetch | 1d |
| 14.10 | Demo seed adds CL forecasts + journal + paper trades | 0.5d |
| 14.11 | E2E + visual QA | 0.5d |

**Total: ~7 working days (~1.5 weeks).**

## Acceptance criteria

1. Dashboard has a watchlist sidebar with NG and CL rows. Clicking CL
   switches every dashboard widget to CL data and updates the URL to
   `?symbol=CL`.
2. Refreshing on `?symbol=CL` keeps CL selected. Removing the param
   and reloading falls back to whatever's in localStorage.
3. Chart page, Signal Lab, Scenario Lab, Journal, Paper Trading,
   Calibration, and Admin all respect the active instrument.
4. CL gets a Yahoo delayed quote stream, EIA Cushing stocks pulls
   succeed, CFTC WTI positioning is in the alt-data block, and the
   news filter shows oil/crude articles.
5. Working Thesis card works for CL — separate active thesis per
   instrument (already enforced by the partial unique index).
6. Calibration page shows separate stats per instrument; switching
   refetches.
7. All existing 595+241 tests still pass; new tests for adapters +
   active-instrument hook bring the total north of 900.

## Out-of-scope guardrails

- No more than 2 instruments (NG + CL) — Phase 15 expands to the full
  watchlist (HO, RB, ZC, ZS, ZW).
- No cross-asset correlation features (deck slide 6 "Cross-Asset
  Propagation") — that needs ≥ 3 instruments and is a separate effort.
- No multi-instrument journal entries — each entry remains tied to one
  instrument via `instrument_id` (already the schema).
- No splitting `theses` per-instrument in the LLM coach — coaching is
  per-instrument already via `instrument_code`.

## Risks

- **EIA petroleum series stability:** the Cushing crude series ID hasn't
  changed in years, but EIA occasionally renames. Adapter falls back to
  mock data if the API returns a non-200 response.
- **CFTC CL market code:** verified `067651` against current CFTC docs.
  If the code shifts the new adapter test suite will catch it.
- **Yahoo CL=F throttling:** Yahoo aggressively rate-limits per IP. Same
  retry/backoff we wired for NG=F covers it.
- **Frontend regressions:** wiring activeSymbol through every page is
  the most error-prone step. The visual QA pass at the end has to
  exercise each page with both symbols.
