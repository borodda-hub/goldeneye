# Phase 10 Plan — Backtest Engine

**Goal:** Replace the synthetic seeded forecasts in `model_forecasts` with the output of a real backtest replay — each row is a forecast the model *would have made* at `generated_at`, scored against the realized price move at `generated_at + horizon`. The Signal Lab's history table and the per-model hit-rate stop being fiction.

**Acceptance:** click "Run backtest" in the Signal Lab → see per-model hit-rate (e.g. *"moving_average_directional: 57.3% on 1d, 134 scored forecasts"*) computed from real NG price history. Numbers are reproducible (deterministic seeds where models have any), survive look-ahead safety tests, and persist in `model_forecasts` so the History table reads the same data.

**Estimated total:** ~8-10 working days. One commit per step.

---

## Step 0 — Plan doc (this file, ~½ day)

Captured here. Approve and step 1 starts.

## Step 1 — Backtest engine core (~2 days)

New module `apps/api/services/backtest.py`. Pure Python; no HTTP, no DB writes yet, just an in-memory replay loop with a clean interface the endpoint will wrap later.

### Signature

```python
@dataclass(frozen=True)
class BacktestConfig:
    model_name: str
    symbol: str = "NG"
    from_date: date
    to_date: date
    horizon: str = "1d"   # "1d" | "1w" | "1m" per docs/SCHEMA.md §horizons
    retrain_cadence_days: int | None = None  # None = stateless reuse


@dataclass(frozen=True)
class BacktestRow:
    generated_at: datetime
    model_name: str
    horizon: str
    direction: str
    confidence: str
    expected_pct: float | None
    realized_pct: float | None
    outcome: str          # "hit" | "miss" | "indeterminate" | "neutral" | "pending"
    delta_from_expected_pct: float | None
    vol_regime: str | None
    supporting: list[dict]
    contradicting: list[dict]
    inputs_used: list[str]


@dataclass(frozen=True)
class BacktestSummary:
    n: int                # total rows
    scored: int           # excludes pending + neutral
    hit_rate: float       # hits / scored
    indeterminate_rate: float
    mean_delta: float     # mean of (realized - expected)
    std_delta: float
    by_horizon: dict[str, dict[str, Any]]  # nested same shape


async def run_backtest(
    session: AsyncSession,
    config: BacktestConfig,
) -> tuple[list[BacktestRow], BacktestSummary]:
    ...
```

### Replay loop

For each calendar date `d` in `[from_date, to_date]`:
1. Build a `ForecastContext` snapshot **as of EOD `d`** (see Step 2 for the look-ahead safety rules).
2. Call the model's `predict(ctx)` to produce a `ForecastResult`.
3. Compute `realized_pct` by looking up the 1d close at `d + horizon_days` and `d`. If either is missing → `outcome=pending`, `realized_pct=None`.
4. Use the existing `services.signal_scoring.score_forecast` to produce the outcome — same ±0.3% deadband as the Signal Lab.
5. Append a `BacktestRow`.

After the loop, compute `BacktestSummary` aggregates.

Retrain cadence applies only to models that hold state (currently just `prophet_trend`). When configured, the loop calls the model's `fit(ctx)` only once every `retrain_cadence_days` days; otherwise `fit` is called once at `from_date` and reused.

## Step 2 — Look-ahead safety + tests (~2 days)

This is the credibility-load-bearing piece. Two failure modes to prevent absolutely:

1. **Price look-ahead** — the model must never see a price bar with `ts >= as_of`. The replay loop's `ForecastContext.closes` must be strictly the closes at `ts < as_of`, ordered chronologically.
2. **Alt-data look-ahead** — `latest_storage` and `latest_cot` snapshots must be the most-recent reports with `published_at < as_of` (or `report_date < as_of` if `published_at` is null on legacy rows). EIA storage is released Thursdays 10:30 ET; COT is Friday 15:30 ET. Treating them as "available" before that timestamp leaks signal.

### Defensive design

- `as_of` parameter on every helper. No globals, no `datetime.utcnow()` shortcuts.
- `_context_as_of(session, instrument_id, as_of) -> ForecastContext` — single chokepoint that builds the ForecastContext from DB queries with explicit `< as_of` filters. Every consumer goes through this. No public method takes a context without going through it.
- Property-based test: for a randomly-generated `as_of`, assert that `ctx.closes[-1].ts < as_of`, `ctx.latest_storage.published_at < as_of`, and `ctx.latest_cot.published_at < as_of`.
- "Cheating model" test: a synthetic model that returns `direction = bullish if ctx.closes[-1] > 0 else bearish` (always trivially right because the future is in `closes`) — if look-ahead is correctly blocked, its hit-rate should be ~50%, not 100%.

## Step 3 — REST endpoint + persistence (~1.5 days)

### Endpoint

`GET /v1/backtest`

| Param | Type | Default | Notes |
|---|---|---|---|
| `model` | string | required | One of the registered model names |
| `symbol` | string | `"NG"` | future-proofing |
| `from` | date | `to - 90d` | inclusive |
| `to` | date | today | inclusive |
| `horizon` | string | `"1d"` | `"1d"\|"1w"\|"1m"` |
| `retrain_days` | int? | null | only used by `prophet_trend` |
| `persist` | bool | `true` | when true, writes rows to `model_forecasts` |

Returns:
```jsonc
{
  "config": { ... echo },
  "summary": { "n": 240, "scored": 188, "hit_rate": 0.573, "indeterminate_rate": 0.05, "mean_delta": -0.0021, "std_delta": 0.018 },
  "rows": [
    { "generated_at": "...", "direction": "bullish", "expected_pct": 0.012, "realized_pct": 0.018, "outcome": "hit", ... },
    ...
  ]
}
```

### Persistence

Existing `model_forecasts` table fits — same columns the live route produces. Adds:
- `source` field is implicit (we already have a free-form column? confirm in step 1; if not, the worker writes `inputs_hash = "backtest:..."` to distinguish).
- Idempotency: dedupe on `(instrument_id, model_name, horizon, generated_at)` via upsert. Re-running a backtest over the same window overwrites without exploding row count.

### Cleanup of synthetic seed

`apps/api/seeds/example_forecasts.py` (commit `c215b4d`) seeded 240 fake rows. Once the backtest endpoint produces ≥ that volume, the seed becomes confusing — both real and fake rows in the history table. Step 3 includes a one-time deletion of `source IS NULL OR source = 'mock'` rows for any model that has backtest output, run inside the backtest's persistence path.

## Step 4 — Signal Lab UI integration (~2 days)

Two additions on `/signals`:

### Backtest card (new Row 5, beneath the news feed)

- Per-model row: `[model name] [hit-rate bar 0-100%] [scored count] [run backtest button]`
- Default state: shows whatever's in the DB from prior runs (so revisits are instant). Empty state: "Run a backtest to see scored performance."
- Click "Run backtest" → POST to a mutation endpoint (or fire the GET with persist=true) → spinner → refresh.

### History table connection

- The existing History table already reads `model_forecasts`. Once the backtest is producing rows, this populates automatically.
- Replace the synthetic seed (`c215b4d`) per Step 3 cleanup.

### Tests

- Component tests for the new card (loading / error / empty / populated states).
- Playwright happy-path: open signals → click run-backtest for one model → assert hit-rate appears.

## Tests required

- `tests/services/test_backtest_replay.py` — engine loop, scoring math, summary aggregation.
- `tests/services/test_backtest_lookahead.py` — the load-bearing property tests + cheating-model test.
- `apps/api/tests/test_backtest_endpoint.py` — route validation, persistence, idempotency.
- Frontend component + Playwright per Step 4.

## Out of scope (deliberately deferred to a later phase)

- **Transaction costs / slippage / P&L backtesting.** This phase is direction-accuracy only. P&L is a separate dimension — the paper-trading screen already has that surface.
- **Walk-forward training.** Prophet's `retrain_cadence_days` is the only nod. True walk-forward + parameter sweeps would be Phase 11+.
- **Multi-instrument backtests.** Symbol is parameterized but only NG is seeded. Adding WTI is its own phase.
- **Backtest comparison reports / PDF export.** The scenario PDF export pattern (commit `20d6cd1`) is reusable later if you want this.
- **Live forecast persistence.** Today the Signal Lab's `current` endpoint computes forecasts but doesn't persist them. A worker-based live-persist loop is Phase 12+ and would supplement the backtest, not replace it.

## Acceptance criteria for Phase 10

- `GET /v1/backtest?model=moving_average_directional` returns ≥ 60 days of scored rows with a non-trivial outcome distribution against the seeded NG price history.
- Look-ahead test suite green: the cheating-model test gets hit-rate ≈ 50% (proves no future data leaks).
- Signal Lab "Backtest" card renders per-model hit-rates.
- The synthetic `example_forecasts.py` seed is removed from `make demo` (or marked dev-only behind a flag).
- All previous tests still pass.
- `pnpm health` + `pytest` green.

## Phase 11 (next)

Deploy to a shareable URL (Vercel + Railway + Upstash) per `docs/DEPLOYMENT.md`. Should be ~1 day once Phase 10 is shipped.

When complete, commit `Phase 10: backtest engine` and stop for review.
