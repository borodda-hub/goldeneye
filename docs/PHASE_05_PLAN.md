# Phase 05 Plan — Signal Lab + Ensemble Polish

This plan **replaces** the implementation guidance in `files/ngti-playbook/ngti-playbook/prompts/05_signal_lab.md`. The original prompt remains valid for everything not contradicted here. Six decisions are overridden to make the analysis credible rather than superficially rigorous.

## Override decisions (locked)

1. **Tie-break rule changed.** Original spec said a tie defers to `volatility_regime`'s direction in elevated/crisis regimes. That model derives direction from `closes[-1] vs closes[-2]` — a one-tick momentum signal. Inheriting it on a tie is worse than `neutral`. **New rule:** ties always resolve to `direction = "neutral"`. In elevated/crisis regimes the ensemble *confidence* drops to `"low"` and a caveat is added; in compressed/normal regimes confidence is left at whatever the agreement fraction yields. "Defensive" means narrowing conviction, not picking a direction from noise.

2. **Hit/miss computation moves server-side with a deadband.** The original spec implied client-side scoring against bar data. That ships a misleading table (no deadband → coin-flip "hits") and forces 25 round-trips. Backend computes `realized_pct` and `outcome` on each `/v1/signals/history` row. Deadband = **±0.3%** (matches the MA model's internal direction threshold). `docs/API_CONTRACTS.md` is updated in the same commit.

3. **`xgboost_placeholder` consumes alternative data.** All four current models read `closes` only — "ensemble agreement" is correlated agreement of one signal. The placeholder is the natural slot to represent the alt-data voice. It now reads `latest_storage` (EIA build/draw vs consensus) and `latest_cot` (net managed-money change) when present on the `ForecastContext`. When alt-data is missing, it falls back to current momentum-only logic and adds a `"missing alt-data"` contradicting factor.

4. **Ensemble output gains `agreement`, `input_diversity`, and `confidence_rationale`.** The user-facing confidence band has to mean something. The rationale field names *why* the band is what it is (agreement count, input diversity, sample sufficiency). The frontend renders it.

5. **History table orders by horizon expiry desc, not generation date.** Freshest rows are always `pending`. Sort by `generated_at + horizon_days` so scoreable rows surface first. Default filter hides pending (toggle reveals them).

6. **`explain_signal` is called with the full per-model breakdown plus ctx data.** Currently `apps/api/routers/signals.py:43-44` passes only `{direction, confidence, vol_regime}` and `{symbol, closes_count}`. The LLM is generating prose from near-empty context. Pipe `results` (per-model supporting/contradicting), storage, COT, and weather anomaly into the call. This is wiring, not logic — but it's what makes the eval tests meaningful.

---

## Backend deliverables

### 1. `apps/api/services/ensemble.py`

Existing `compute_ensemble` returns `{direction, confidence, vol_regime, expected_pct, range}`. **Extend it** to also return:

```python
{
  # ...existing fields...
  "agreement": {
    "bullish": int,    # count of models calling bullish
    "bearish": int,
    "neutral": int,
    "total": int,
    "input_diversity": "low" | "medium" | "high",
  },
  "confidence_rationale": list[str],  # 2-4 short strings
  "caveats": list[str],                # added by tie-break and other logic
}
```

**`input_diversity` derivation:**
- `high` — at least one model used `latest_storage` OR `latest_cot` OR `weather_anomaly`
- `medium` — at least one model used a non-price signal (e.g., `vol_regime` derived signal) even if input was prices
- `low` — all models read price series only

Models declare what they used via a new field on `ForecastResult`: `inputs_used: list[str]` (e.g. `["closes"]`, `["closes", "latest_storage", "latest_cot"]`). Default `["closes"]`.

**`confidence_rationale` derivation** — assemble 2-4 strings from:
- The agreement count: `"N of M models agree on direction"`
- The input diversity tag: `"All models read price series only (low input diversity)"` / `"Mixed price + fundamental signals (high input diversity)"`
- Sample sufficiency: `"100 bars of history available (sufficient)"` / `"55 bars of history (minimum for full model suite)"`
- If any model returned a `"missing alt-data"` or `"insufficient history"` contradicting factor, add it.

**Tie-break logic (locked rule 1):**
- Detect tie: two or more directions share the max weight, **or** all weights are zero.
- On tie: `direction = "neutral"`. If `vol_regime in {"elevated", "crisis"}`: force `confidence = "low"` and append caveat `"Models disagree in elevated volatility regime; uncertainty is amplified in both directions."` Otherwise append caveat `"Models disagree at low volatility; no clear directional signal."`

### 2. `apps/api/services/models/`

For each of the 4 models, ensure both `supporting` and `contradicting` arrays have **at least one entry** with `factor`, `weight`, `note`. Audit each:

- **`moving_average_directional.py`** — already has both. ✓ Add `inputs_used = ["closes"]`.
- **`prophet_trend.py`** — already has both. ✓ Add `inputs_used = ["closes"]`. The stub branch (Prophet not installed) currently has empty `supporting`. Add a placeholder `supporting` entry like `{"factor": "Stub mode", "weight": 0.0, "note": "Prophet package unavailable; model returning neutral."}` so the array invariant holds.
- **`volatility_regime.py`** — already has both. ✓ Add `inputs_used = ["closes"]`.
- **`xgboost_placeholder.py`** — **rewrite** per locked rule 3:
  - Accept `latest_storage: dict | None` and `latest_cot: dict | None` as optional args.
  - Compute three sub-signals, each producing a direction vote weighted by listed weight:
    - Storage (weight 0.4): if `latest_storage.delta_vs_consensus < 0` (smaller-than-expected build / larger draw) → bullish; if `> 0` → bearish; else neutral.
    - COT (weight 0.3): if `latest_cot.mm_net_delta > 0` (managed-money getting longer) → bullish; if `< 0` → bearish; else neutral.
    - Momentum (weight 0.3): current 5d-vs-10d mean logic.
  - Aggregate: weighted sum per direction; winner takes the call. Confidence: `"medium"` if at least two sub-signals agree, `"low"` otherwise.
  - `inputs_used` reflects what was actually used (e.g. `["closes", "latest_storage", "latest_cot"]` or `["closes"]` if alt-data was None).
  - Contradicting array: keep the "placeholder until training pipeline ships" entry. If `latest_storage` or `latest_cot` was None, add `{"factor": "Missing alt-data", "weight": 0.5, "note": "Storage and/or COT context unavailable; falling back to price momentum only."}`.

`run_all` in `model_registry.py` must pass `ctx.latest_storage` and `ctx.latest_cot` to `xgb_predict`.

### 3. New: `apps/api/services/signal_scoring.py`

Pure scoring module — no DB, no I/O. Public function:

```python
def score_forecast(
    direction: str,
    horizon: str,
    expected_pct: float | None,
    realized_pct: float | None,
    deadband: float = 0.003,
) -> dict[str, Any]:
    """
    Returns: {
      "outcome": "hit" | "miss" | "indeterminate" | "neutral" | "pending",
      "realized_pct": float | None,
      "delta_from_expected_pct": float | None,  # realized - expected, signed
    }
    """
```

Rules:
- `realized_pct is None` → `outcome = "pending"`
- `direction == "neutral"` → `outcome = "neutral"` (display as flat dash; not graded)
- `abs(realized_pct) < deadband` → `outcome = "indeterminate"`
- Else: `hit` if direction matches sign of `realized_pct`, else `miss`
- `delta_from_expected_pct = realized_pct - expected_pct` when both present, else None

Tests cover boundary (exactly ±0.003), zero, NaN/inf (treat as None), missing `expected_pct`.

### 4. `apps/api/routers/signals.py`

**`/v1/signals/current`:**
- Build `ForecastContext` with `latest_storage` and `latest_cot` populated (use the existing repos to fetch the most recent entry of each).
- Pass full `results` list and the same ctx fields to `explain_signal`. The `signal` dict given to the LLM should now include the `agreement` block and `confidence_rationale`. The `ctx` dict should include `models: [...per-model breakdown...]`, `storage: {...}`, `cot: {...}`.
- Response shape (additions over current):
  ```jsonc
  {
    "instrument": "NG",
    "ensemble": {
      "direction": "...",
      "confidence": "...",
      "vol_regime": "...",
      "expected_pct": 0.018,
      "range": { ... },
      "agreement": { "bullish": 3, "bearish": 0, "neutral": 1, "total": 4, "input_diversity": "medium" },
      "confidence_rationale": ["...", "..."],
      "caveats": ["..."]
    },
    "models": [...],
    "explanation": "...",
    "safety": { ... }
  }
  ```

**`/v1/signals/history`:**
- New default ordering: by `generated_at + horizon_days` descending (i.e. horizon-expiry desc, scoreable rows first).
- New query param: `status: "all" | "scored" | "pending"` (default `"scored"`). `"scored"` excludes rows where horizon hasn't elapsed.
- For each row, look up the close at `generated_at` and at `generated_at + horizon_days` using `price_bars` repo. Compute `realized_pct`, then call `signal_scoring.score_forecast`.
- If no bar exists at `generated_at + horizon_days` (horizon not yet elapsed or no data): outcome = `"pending"`.
- Response row shape:
  ```jsonc
  {
    "id": "...",
    "generated_at": "...",
    "horizon_end": "2026-05-11T20:00:00Z",
    "model_name": "...",
    "horizon": "1d",
    "direction": "...",
    "confidence": "...",
    "expected_pct": 0.012,
    "vol_regime": "...",
    "outcome": "hit" | "miss" | "indeterminate" | "neutral" | "pending",
    "realized_pct": 0.018 | null,
    "delta_from_expected_pct": 0.006 | null,
    "scored_at": "2026-05-11T20:00:00Z" | null
  }
  ```
- Horizon days mapping: `1d → 1`, `1w → 7`, `1m → 30`.

### 5. `apps/api/services/llm_explainer.py::explain_signal`

No code changes needed in the explainer itself — the wiring change is in the router (locked rule 6). But:
- Verify the prompt template in `apps/api/services/llm_prompts.py::explain_signal_messages` actually uses the per-model bullets and ctx fields when present. If it doesn't, extend it.
- Ensure the LLM eval test (below) drives this and surfaces any prompt template gaps.

### 6. `docs/API_CONTRACTS.md`

Update `§signals` to reflect the additions above. New fields, new query param on history, new outcome enum. Commit in the same change.

---

## Frontend deliverables

### Layout (single-frame at 1280×800, no scroll inside the page)

```
HeaderRow (full width, slim)         — instrument + ensemble headline + LiveDot
─────────────────────────────────────────────────
EnsembleHeader (full width)          — direction, confidence, vol regime, expected range, agreement, rationale
ModelGrid (4 cards)                  — one card per model
─────────────────────────────────────────────────
ExplanationPanel (left ~60%) + (right ~40%) HistoryTable
```

### `components/signals/EnsembleHeader.tsx`

Props: `{ ensemble: EnsembleData }`. Renders:
- Big direction (`<DirectionChip>` at a larger size) + confidence (`<ConfidenceBar>`) on the left
- Vol regime chip + expected range bar in the middle. Range bar: `realized = expected ± half-range`, rendered as a thin horizontal bar with a marker at expected_pct. If range is missing or expected_pct is None, render `—` not a band.
- Agreement readout on the right: `"3 of 4 bullish · input diversity: medium"` (mono, ink-3). Click reveals the full per-model count and input_diversity tag.
- Confidence rationale: bulleted list of 2-4 strings underneath the headline, in `text-ink-3 text-xs` — always visible (do not hide behind a collapse). This is the trust signal.
- Caveats: same row as rationale, prefixed with `⚠` in `text-conf-low`. If empty, render nothing.

### `components/signals/ModelGrid.tsx`

4 cards in a `grid grid-cols-4 gap-4`. Each card (`<ModelCard>`):
- Header: model name in `font-mono text-ink-2 text-sm` + horizon chip (mono, ink-3).
- Direction chip + confidence bar in one row.
- Expected pct (if present): `<NumberCell value={expected_pct * 100} precision={2} unit="%" />` with signed colored arrow.
- Inputs used: tiny tag row, `font-mono text-xs text-ink-4` — e.g. `closes · storage · cot`. This makes input diversity visible at the model level too.
- Top supporting factor (first entry): green-soft border-left, factor name in ink-2, note in ink-3 (text-xs, line-clamp-2).
- Top contradicting factor (first entry): red-soft border-left, same formatting.

If a model has no usable signal (e.g., insufficient data), the card renders the contradicting factor as the headline and the direction/confidence in muted style (ink-3/4).

### `components/signals/ExplanationPanel.tsx`

- LLM explanation prose in `text-ink-2 text-sm leading-relaxed`, max 5 sentences.
- `<SafetyEnvelopeNote envelope={safety} defaultOpen={true} />` below.
- If LLM call failed (router returned a fallback), render `"Explanation unavailable — see per-model factors above."` in `text-ink-4 italic`.

### `components/signals/HistoryTable.tsx`

- Header row with column labels in `text-ink-3 text-xs uppercase tracking-widest`.
- Columns: `Horizon end` · `Generated` · `Model` · `Direction` · `Confidence` · `Expected %` · `Realized %` · `Δ` · `Outcome`.
- Default: 25 rows, sorted by `horizon_end` desc, scored-only filter active.
- Toggle: `[Show pending]` in the table header — when on, fetch with `status=all` and show pending rows with `outcome = "pending"` rendered as `···` in ink-4.
- Outcome rendering:
  - `hit` → `▲` in text-up
  - `miss` → `▼` in text-down
  - `indeterminate` → `◇` in text-flat (within deadband — no clear signal either way)
  - `neutral` → `—` in text-flat (model called neutral; not graded)
  - `pending` → `···` in text-ink-4
- Numbers right-aligned, `font-mono tabular-nums`. Δ column shows `realized - expected` with the same color logic.
- "Expand to 100" link at the bottom in `text-accent text-xs`.

### `app/(app)/signals/page.tsx`

Server component. Pre-fetches `/v1/signals/current` and `/v1/signals/history?limit=25&status=scored`. Passes both as `initialData` to a `SignalsShell` client component (same pattern as Phase 04 dashboard/chart).

---

## Tests

### Backend

1. **`apps/api/tests/test_signal_scoring.py`** — unit tests for `signal_scoring.score_forecast`:
   - Boundary: exactly `±0.003` realized → indeterminate
   - Just above/below boundary
   - Realized `None` → pending
   - Direction neutral → neutral outcome
   - Realized NaN/inf treated as None
   - Delta computation with/without expected_pct

2. **`apps/api/tests/test_ensemble.py`** (extend existing) — assert:
   - `agreement` counts add up to total
   - `input_diversity` is `"high"` when one model used storage; `"low"` when all read price only
   - Tie produces `direction="neutral"` (never inherits a model direction)
   - Tie in elevated regime drops confidence to `"low"` and adds caveat
   - Tie in normal regime keeps confidence as is, different caveat

3. **`apps/api/tests/test_xgboost_alt_data.py`** — assert:
   - With storage delta_vs_consensus = -10 → direction includes bullish signal
   - With cot mm_net_delta = +5000 → bullish signal
   - With both None → falls back to momentum and adds "Missing alt-data" caveat
   - `inputs_used` reflects what was actually used

4. **`apps/api/tests/test_signals_history.py`** — integration test:
   - Seed forecasts at various ages relative to today
   - Assert `/v1/signals/history?status=scored` returns only past-horizon rows
   - Assert outcome field is present and matches expected per seed
   - Assert ordering is by `horizon_end` desc

5. **`apps/api/tests/llm/test_explain_signal_corpus.py`** — generate 50 explanations from a fixture of varied ensemble inputs (aligned bullish, aligned bearish, mixed, tie, etc.). Assert:
   - Zero forbidden phrase matches across all 50 (acceptance criteria requirement)
   - At least 47/50 (94%) match the inference-marker regex from `docs/AI_BEHAVIOR.md §required_phrasing_patterns`

### Frontend

6. **Component tests** for `EnsembleHeader`, `ModelGrid` (test ModelCard with various model states), `HistoryTable` (test outcome rendering for each outcome value), `ExplanationPanel`. Mock `useChannel` / `useQuery` as needed.

7. **`apps/web/tests/e2e/signals.spec.ts`** — Playwright:
   - Loads `/signals` within 2s
   - At least one model card renders
   - `<SafetyEnvelopeNote>` is present
   - Run a forbidden-phrase regex against `await page.content()` — must match zero times
   - Reload the page 5 times in the test (lighter than the 50-load acceptance — that's covered by the corpus test)

---

## Acceptance criteria

- `/signals` loads with non-empty content within 2s.
- Forbidden-phrase corpus test passes (zero matches over 50 generated explanations).
- `/v1/signals/history?limit=25` returns 25 rows, ordered by `horizon_end` desc, with `outcome` correctly populated for past-horizon forecasts.
- Ensemble response includes `agreement`, `confidence_rationale`, and (when relevant) `caveats`.
- `xgboost_placeholder` reads alt-data when present; `input_diversity` reports `"high"` when at least one alt-data field is available.
- Tie-break never produces a directional inheritance — ties are always `neutral`.
- `pnpm health` and `/contract-check` pass.

## Forbidden

- Do not modify other screens.
- Do not bypass the safety wrapper.
- Do not silently lower confidence to `"low"` when models are unavailable — return a clear `"model unavailable"` caveat and let the ensemble adjust.
- Do not add new models — polish the four that exist.
- Do not compute hit/miss client-side. The server is the source of truth for scoring.

When complete, commit `Phase 05: signal lab + ensemble polish` and stop.
