# Phase 07 Plan — Decision Journal + Paper Trading

Refines `files/ngti-playbook/ngti-playbook/prompts/07_journal_paper.md` against the current codebase.

## Existing scaffolding

- `apps/api/routers/journal.py` — full CRUD already implemented. **Currently calls `review_journal_entry` synchronously** inside `POST /v1/journal` and stores the result on the entry before returning.
- `apps/api/routers/paper.py` — `/open`, `/{id}/close`, list, get already implemented. Calls `paper_trades` repo directly.
- `apps/api/models/orm/{journal,paper}.py` — schemas already defined; migrations applied.
- `apps/api/repos/{journal,paper_trades}.py` — basic create/get/list with simple `close_trade` PnL math.
- `apps/web/app/(app)/{journal,paper}/page.tsx` — placeholder pages only.

## Override decisions (locked)

1. **LLM review stays synchronous.** Prompt asks for async + WebSocket push on `journal.{user_id}`. The existing implementation calls `review_journal_entry` synchronously inside `POST /v1/journal` and stores `llm_review` before returning. With the mock LLM client this is ~0s; with a real LLM ~5s. Synchronous keeps the code paths simple, avoids per-request task lifecycle management, and means the frontend gets the review in the create response. The WS channel/async-task plumbing is deferred.

2. **No user scope, no auth.** `user_id` stays NULL on all rows (this matches the existing seed data). The journal/paper feature is effectively single-tenant for the demo.

3. **Tick value hardcoded for NG.** Natural Gas futures are 10,000 MMBtu per contract; PnL = `(exit - entry) × size × 10,000 USD/MMBtu`. Encoded as a constant `NG_TICK_VALUE_USD = 10_000` in `paper_engine.py`. Out-of-scope: per-instrument tick lookup.

4. **Leverage cap = 10× simulated equity, with $100,000 starting balance.** Implementable as a soft check on `open_trade`: reject if `notional > 10 × current_equity` (current equity = $100k start + sum of closed PnL). Returns `409` with a clear message. Documented in `API_CONTRACTS.md`.

5. **Equity curve = daily resampling.** Start at $100k. For each day `d` in range: equity = $100k + sum of closed-trade PnL up to `d` + sum of MTM PnL on positions open at `d`. MTM uses the daily close from `price_bars` (1d resolution).

6. **CSV export is client-side only.** `ClosedTradesTable` builds a CSV blob and triggers a download. No backend export endpoint.

7. **No drag-to-reorder for evidence rows.** Add/remove only. Drag adds complexity without demo value.

## Backend deliverables

### 1. New: `apps/api/services/paper_engine.py`

Pure-Python service module. Public functions:

```python
NG_TICK_VALUE_USD = 10_000.0
STARTING_EQUITY_USD = 100_000.0
LEVERAGE_CAP = 10.0

def compute_pnl(side: str, size: float, entry: float, exit_: float) -> float:
    """PnL in USD. Long: (exit - entry) × size × tick. Short: inverted."""

async def current_equity(session) -> float:
    """STARTING_EQUITY_USD + sum(closed outcome_pnl)."""

async def validate_open(session, req) -> None:
    """Raises HTTPException 400/409 on invalid size, broken stops, or leverage breach."""

async def open_trade(session, req) -> PaperTrade:
    """Validates + persists via repo."""

async def close_trade(session, trade_id, exit_price: float | None) -> PaperTrade:
    """If exit_price is None, mark-to-market off latest 1d bar mid. Computes PnL."""

async def equity_curve(session, since: date | None) -> list[dict]:
    """Daily series: [{date, equity}]. Equity = starting + closed-to-date PnL + open-position MTM."""
```

### 2. Refactor `apps/api/routers/paper.py`

- Move open/close logic into `paper_engine` calls. Router stays thin.
- Add new `GET /v1/paper-trades/equity-curve?since=YYYY-MM-DD` endpoint.
- Make `CloseTradeRequest.exit_price` optional; engine marks to market if absent.

### 3. New: `apps/api/repos/paper_trades.py` additions

- `list_open(session) -> list[PaperTrade]` (filtered helper).

### 4. Journal stays as-is

The existing `journal.py` router meets the spec apart from the async deviation. Confirm `routers/journal.py`'s LLM review continues to wrap with `wrap_with_uncertainty` (it does — `review_journal_entry` returns `(text, SafetyEnvelope)`).

### 5. Tests

- `apps/api/tests/test_paper_engine.py` — open/close round-trip, PnL math (long/short), leverage cap rejection, MTM close uses latest bar, equity curve daily resample.
- `apps/api/tests/llm/test_review_journal_entry.py` — 50 fixture responses: forbidden-phrase scan, inference markers, "no directional view" check (no `\b(bullish|bearish)\b` in directional-claim contexts; review should be assumption-focused), 4-6 bullet structure.

### 6. Docs

Update `docs/API_CONTRACTS.md`:
- New `GET /v1/paper-trades/equity-curve` endpoint
- Optional `exit_price` on `/close`
- `409` leverage breach on `/open`

## Frontend deliverables

### Journal

- `app/(app)/journal/page.tsx` — async server prefetch of `/v1/journal?limit=20`.
- `app/(app)/journal/JournalShell.tsx` — client shell, holds selected-entry state.
- `app/(app)/journal/types.ts`.
- `components/journal/EntryList.tsx` — cards with hypothesis preview + `<ConfidenceBar>` (mapped from confidence_pct to low/med/high band).
- `components/journal/NewEntryForm.tsx` — hypothesis textarea + evidence rows (`{source, summary, weight}` add/remove) + confidence slider 0-100 + planned action + risk-factor tag input + invalidation criteria.
- `components/journal/EntryDetailDrawer.tsx` — full entry + LLM review bullets + linked paper trade if any. With sync review the bullets are always present on first load.
- Component tests.

### Paper

- `app/(app)/paper/page.tsx` — async server prefetch of `/v1/paper-trades?status=open` + `/closed` + `/equity-curve?since=<90d-ago>`.
- `app/(app)/paper/PaperShell.tsx` — client shell.
- `app/(app)/paper/types.ts`.
- `components/paper/OpenPositionsTable.tsx` — open trades + live MTM via `useChannel('price.NG.front')`.
- `components/paper/ClosedTradesTable.tsx` — sortable, CSV export button.
- `components/paper/NewTradeForm.tsx` — contract code, side toggle, size, entry (current mid), stop, take, rationale, journal_ref dropdown.
- `components/paper/EquityCurveChart.tsx` — Recharts line chart.
- Component tests.

### Playwright

- `apps/web/tests/e2e/journal_paper_flow.spec.ts` — create entry → open trade linked → MTM updates → close trade → row in closed table.

## Acceptance criteria

- `POST /v1/journal` returns the entry with `llm_review` populated (synchronous).
- Opening a paper trade and waiting 5s shows live MTM in the open positions table (driven by WS ticks).
- `GET /v1/paper-trades/equity-curve` returns a valid daily series.
- Playwright flow passes (skipped if browser unavailable).
- All existing tests still pass.

## Forbidden

- No real broker calls; mock-only.
- No journal review output that gives a directional view ("this is a good idea", "I would take this trade").
- No skipping the safety wrapper on LLM output.
- No leverage above 10× simulated equity.

When complete, commit `Phase 07: decision journal + paper trading`.
