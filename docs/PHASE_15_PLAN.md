# Phase 15 Plan — Chart Indicators: Moving Averages

**Goal:** First wave of NinjaTrader-style chart tools. Ships **Category 2
(Moving Averages)** as a complete vertical slice: backend indicator-compute
service, REST endpoint, frontend picker UI, and per-symbol persistence. The
indicator-engine architecture (`services/indicators/`, `/v1/chart/indicators`,
frontend registry) is built so subsequent phases bolt on additional indicator
families with no rework.

**Status:** Approved 2026-05-13. Base: `a6f8253` (post-walkthrough tutorial).
Stays on Lightweight Charts v4.2 — no TradingView swap.

## Approved decisions

1. **Charting stack:** Stay on Lightweight Charts. Build native. (NT8-feature
   parity via TradingView Advanced Charts was the alternative; rejected to
   preserve the Goldeneye look and let our forecast/scenario overlays sit
   first-class on the chart.)

2. **Compute side:** Backend. One pandas/numpy function per indicator under
   `apps/api/services/indicators/`. Lets backtest, scenarios, and signals
   reuse the same primitives. Cached by `(symbol, type, params, time range)`.

3. **Persistence:** `localStorage[ngti.chart.indicators.<symbol>]` — array of
   indicator specs. Per-symbol, per-browser. Upgrades to a Postgres-backed
   `chart_indicators` table when real auth lands.

4. **In-scope MAs (7 + ribbon):** SMA, EMA, WMA, HMA, DEMA, TEMA, VWMA, plus
   a Ribbon preset (one click → 12 MAs of lengths 5/8/13/21/34/55/89/100/144/
   200/233/377 with a graduated palette).

5. **Out of scope — parked for 16+:**
   - Trend strength (ADX/DMI, MACD, Parabolic SAR, SuperTrend, Ichimoku,
     Linear Regression) — needs sub-pane work
   - Channels (Bollinger/Keltner/Donchian) — needs band-fill rendering
   - Volume tools (VWAP/OBV) — straightforward but separate phase
   - Drawing tools (trendline, ray, fibonacci, pitchfork, regression channel)
   - Bar types (Heikin-Ashi/Renko cheap; tick/volume/range need data we
     don't have)
   - Goldeneye-only overlays (forecast bands, scenario markers, AI signals
     on chart) — Phase 17

6. **Data-gap acknowledgements** (won't ship, ever, without more data):
   - **Cumulative Delta** — needs bid/ask tick-by-tick order flow
   - **Real Volume Profile** — needs intra-bar volume distribution
   - **Tick / Volume / Range bars** — need transaction-level data

## Backend

### 15a — Indicator service module

New package: `apps/api/services/indicators/`

```
apps/api/services/indicators/
  __init__.py
  base.py              # IndicatorSpec, IndicatorPoint types + registry
  moving_averages.py   # sma, ema, wma, hma, dema, tema, vwma
  tests/
    test_moving_averages.py
```

Function shape (one per indicator):

```python
def ema(closes: pd.Series, period: int) -> pd.Series:
    """Exponential moving average. Returns Series indexed identically to input."""
    return closes.ewm(span=period, adjust=False).mean()
```

VWMA additionally takes `volumes: pd.Series`.

`base.py` exposes:
- `IndicatorSpec` — Pydantic v2: `{type: Literal[...], params: dict}`
- `IndicatorPoint` — `{t: datetime, v: float | None}`
- `IndicatorSeries` — `{type, params, points: list[IndicatorPoint]}`
- `compute(spec, ohlcv_df) -> IndicatorSeries` — registry dispatch

Indicator output points where computation is undefined (the first N-1 bars
of an N-period MA) emit `v=None` — chart renders gaps, not zeros.

### 15b — REST endpoint

New router: `apps/api/routers/indicators.py` → mounted at `/v1/chart`.

```
GET /v1/chart/indicators
  ?symbol=NG
  &spec=ema:21,sma:50,hma:21
  &from=2026-01-01T00:00:00Z   (optional; default = last 365 days)
  &to=2026-05-13T23:59:59Z     (optional; default = now)
```

`spec` is a comma-separated list of `type:param1[:param2...]`. Parsing rules:
- `sma:20` → `{type: "sma", params: {period: 20, source: "close"}}`
- `vwma:20` → requires volume, error if instrument has no volume data
- Unknown types → 400 with the list of supported types

Response:
```json
{
  "symbol": "NG",
  "indicators": [
    {"type": "ema", "params": {"period": 21, "source": "close"},
     "points": [{"t": "2026-01-02T00:00:00Z", "v": 3.421}, ...]}
  ]
}
```

Repository: reuse existing `repos/prices.py` for OHLCV pull. Cache result in
Redis with key `chart:ind:<symbol>:<sorted-spec>:<from>:<to>` and TTL 5 min
(matches Phase 09 market adapter cadence). Cache miss → compute → set.

### 15c — Tests

`tests/services/indicators/test_moving_averages.py`:
- Numerical accuracy: feed a 200-row OHLCV fixture, assert last 5 values of
  each MA against hand-computed reference values (committed in
  `tests/fixtures/ma_reference.json`)
- Edge cases: period > data length → all None; period = 1 → equals close;
  empty input → empty output
- VWMA: errors when volume is absent

`tests/routers/test_indicators.py`:
- 200 OK with valid `spec`, response shape matches contract
- 400 on unknown type
- 400 on VWMA when symbol lacks volume
- Multi-indicator single call returns all in one response
- Redis cache hit on second identical call (skip if Redis unavailable)

## Frontend

### 15d — Indicator registry

New file: `apps/web/lib/chart/indicatorRegistry.ts`

```ts
type IndicatorSpec = { type: MAType; period: number; source: PriceSource; color: string; weight: 1|2|3; };
type MAType = "sma" | "ema" | "wma" | "hma" | "dema" | "tema" | "vwma";

export const DEFAULTS: Record<MAType, Partial<IndicatorSpec>> = {
  sma:  { period: 20, source: "close", color: tokens.gold[400], weight: 2 },
  ema:  { period: 21, source: "close", color: tokens.gold[300], weight: 2 },
  hma:  { period: 21, source: "close", color: tokens.amber[400], weight: 2 },
  // ...
};

export function specToLabel(s: IndicatorSpec): string {
  return `${s.type.toUpperCase()}(${s.period})`;
}

export function specToQueryFragment(s: IndicatorSpec): string {
  return `${s.type}:${s.period}`;
}
```

Renderer is intentionally trivial — each MA is a single `LineSeries` on the
main pane. The registry is what scales: Phase 16 adds entries for channels
(band renderer), Phase 17 adds entries for trend-strength (sub-pane renderer)
without touching this module's public API.

### 15e — IndicatorPicker modal

`apps/web/components/chart/IndicatorPicker.tsx`

- Triggered from a new "Indicators" button in `ChartToolbar.tsx`
- Fields:
  - Type (dropdown, 7 MA options)
  - Period (number input, validated 2-500)
  - Source (dropdown: close/open/high/low/hl2/hlc3)
  - Color (palette swatches from `docs/FRONTEND_COMPONENTS.md §tokens` — no
    raw hex)
  - Line weight (1/2/3)
- "Add" appends to active indicators; "Cancel" closes
- Below the form: a list of currently active indicators with toggle visibility,
  edit (reopens modal pre-filled), delete

### 15f — Chart wiring

`apps/web/components/chart/PriceChart.tsx`:
- New prop `indicators: IndicatorSpec[]`
- On mount + on indicators change: call
  `GET /v1/chart/indicators?symbol=...&spec=...`
- For each returned series, add a `LineSeries` with the spec's color/weight
- Cleanup: remove series when an indicator is deleted

`apps/web/app/(app)/chart/ChartShell.tsx`:
- Owns `indicators` state, persists to `localStorage[ngti.chart.indicators.<symbol>]`
  via a `useLocalStorage` hook (already exists from Phase 14's
  `useActiveInstrument`)
- Re-keys state on symbol switch so each instrument has its own indicator set

### 15g — Ribbon preset

`apps/web/components/chart/RibbonPresetButton.tsx` (or inline in
IndicatorPicker as a "Presets" tab):
- One click → appends 12 EMAs with periods
  `[5, 8, 13, 21, 34, 55, 89, 100, 144, 200, 233, 377]`
- Colors graduated through the gold→amber ramp
  (`tokens.gold[500] → tokens.amber[700]`)
- Single "Remove Ribbon" affordance to clear all 12 at once

### 15h — Tests

`apps/web/components/chart/__tests__/IndicatorPicker.test.tsx`:
- Renders all 7 MA types in the dropdown
- Validates period bounds
- Calls onAdd with the right spec shape
- Edit flow pre-fills correctly

`apps/web/components/chart/__tests__/PriceChart.indicators.test.tsx`:
- Given 2 indicators, calls the API exactly once with combined spec
- Renders one line series per returned indicator
- Removing an indicator removes its series

`apps/web/lib/chart/__tests__/indicatorRegistry.test.ts`:
- `specToQueryFragment` round-trip
- Default lookup for each MA type

## Acceptance criteria

- [ ] All 7 MA functions return numerically correct values vs. fixture
- [ ] `GET /v1/chart/indicators` ships in OpenAPI; `pnpm contracts:gen:local`
      produces typed shapes consumed by the frontend
- [ ] IndicatorPicker UI works end-to-end: add, edit, delete, toggle
- [ ] Selection persists across reloads, per-symbol
- [ ] Ribbon preset is one click; ribbon spreads/converges visibly in
      trend vs. range periods on the CL chart
- [ ] All colors come from design tokens (no raw hex in component code)
- [ ] `pnpm health` green on both stacks
- [ ] No new disclaimer needed — MAs are descriptive, not forecasts. The
      existing AppShell footer disclaimer remains the sole source.

## Steps (commit-shaped)

1. **15a.1** — `services/indicators/` package: `base.py` + 7 MA functions + unit tests
2. **15a.2** — Redis-cached compute wrapper
3. **15b**   — `routers/indicators.py` + spec parser + router tests
4. **15c**   — OpenAPI export + `pnpm contracts:gen:local`
5. **15d**   — Frontend `indicatorRegistry.ts` + types
6. **15e**   — `IndicatorPicker` modal component + tests
7. **15f**   — Wire `PriceChart` to consume indicator state, fetch, render
8. **15g**   — Ribbon preset button
9. **15h**   — Empty-state polish + final UI pass + `pnpm health`

## Known follow-ups (Phase 16 candidates)

- Channels (Bollinger / Keltner / Donchian) — extends registry with band renderer
- Trend strength (MACD / ADX / DMI / SAR / SuperTrend) — adds sub-pane renderer
- Drawing tools (trendline / ray / fibonacci / pitchfork) — separate layer
  on top of the chart canvas
- LWC v4 → v5 migration (gates proper multi-pane support)
- Postgres-backed chart preferences (gates real auth)
