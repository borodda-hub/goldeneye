# Phase 13 Plan — Decision Quality

**Goal:** Ship the deck's slide-8 hero: a calibration loop. Two user-visible
artifacts:

1. A **Signal Quality grade** chip (A+ … D) on the dashboard, composed from
   four signals our system already computes.
2. A **/calibration** page with a reliability diagram: claimed conviction
   bucket vs. actual hit rate, plus an auto-generated summary card.

This makes the thesis → journal → outcome loop a real product, not just an
asserted one in the deck. It is what differentiates Goldeneye from any
spreadsheet.

**Status:** Approved 2026-05-12. Base: `2c3df81` (post-Phase 12.5).

## Decisions locked in this plan

1. **Outcome resolution:** add `resolved_direction TEXT NULL` to
   `user_decision_journals` with values `hit | miss | neutral | unresolved`.
   The analyst resolves an entry manually when the thesis plays out.
   Couplings to paper trades are out of scope — that's Phase 14+ work.

2. **Journal ↔ Thesis snapshot:** add `thesis_id_at_write UUID NULL` and
   `thesis_conviction_at_write INT NULL` to `user_decision_journals`. Both
   columns are populated when the entry is created if an active thesis
   exists for the instrument. Both are immutable after write.

3. **Calibration page:** new top-level `/calibration` route in nav. Renders
   on top of the existing journal data — no new tables required for
   calibration itself.

## Schema changes

```sql
-- Migration 006
ALTER TABLE user_decision_journals
  ADD COLUMN resolved_direction TEXT NULL
    CHECK (resolved_direction IS NULL OR
           resolved_direction IN ('hit', 'miss', 'neutral', 'unresolved')),
  ADD COLUMN thesis_id_at_write UUID NULL
    REFERENCES theses(id) ON DELETE SET NULL,
  ADD COLUMN thesis_conviction_at_write INT NULL
    CHECK (thesis_conviction_at_write IS NULL OR
           thesis_conviction_at_write BETWEEN 0 AND 100);

CREATE INDEX journal_calibration_idx
  ON user_decision_journals (thesis_conviction_at_write, resolved_direction)
  WHERE resolved_direction IS NOT NULL;
```

## Signal Quality grade

Composite score on 0–100, mapped to a letter:

| Input | Source | Range → score contribution |
|---|---|---|
| input_diversity | already in `signals.py` enum low/medium/high | low=10, medium=20, high=30 (max 30) |
| model_agreement | already in ensemble result | linear: 25 × (max_agreement_fraction) (max 25) |
| regime_stability | new — variance of `vol_regime` over last 14 days of forecasts | stable=25, mixed=15, volatile=5 (max 25) |
| time_to_decision | new — minutes since latest adapter run for any of EIA/COT/NWS | ≤60min=20, ≤4h=15, ≤24h=10, else=0 (max 20) |

**Total max: 100.** Grade cutoffs: `A+ ≥ 90 · A 80 · B 70 · C 60 · D < 60`.

Renders as a small chip on the dashboard header strip, color-coded:
A-grade → up green; B → cyan; C → amber; D → down red.

New service: `apps/api/services/signal_quality.py` →
`compute_grade(session, symbol) -> SignalQualityResult`. New endpoint
`GET /v1/signal-quality?symbol=NG`.

## Calibration

New service: `apps/api/services/calibration.py` →
`compute_calibration(session, instrument_id, bucket_count=5)
-> CalibrationResult`.

Bucket cutoffs (5 buckets, deck-aligned): `[0–20, 20–40, 40–60, 60–80, 80–100]`.
For each bucket:

- `claimed_mean`: mean of `thesis_conviction_at_write` (or
  `confidence_pct` if the snapshot is null — backwards compat for
  pre-Phase-13 entries)
- `resolved_count`: # of entries with `resolved_direction IN ('hit', 'miss')`
- `hit_rate`: hits / resolved_count
- `total_count`: all entries in bucket regardless of resolution

Hit rate is undefined if `resolved_count < 3` — UI shows "n=2 (need 3+)"
rather than a misleading percentage.

The summary card auto-writes a sentence like:
**"Your 70% theses resolved at 64% (n=14)."** picking the bucket with the
biggest gap between claimed and actual, ≥ 5 percentage points.

New endpoint: `GET /v1/calibration?instrument_code=NG&bucket_count=5`.

## Frontend

- `SignalQualityChip` — colored chip on dashboard `HeaderRow`, click opens
  a popover with the 4 sub-scores.
- `/calibration` page with:
  - **`ReliabilityDiagram`** (Recharts) — claimed % on x, hit rate on y,
    perfect-calibration diagonal in `accent-deep`, observed line in
    `accent-bright`, dots sized by `total_count`.
  - **`CalibrationSummary`** — deck-style serif H2 "Your X% theses resolved
    at Y%" with sample-size + caveat copy below.
  - **`BucketTable`** — fallback table with all 5 rows (claimed_mean,
    total_count, resolved_count, hit_rate).

Journal entries need:
- On creation: backend auto-fills `thesis_id_at_write` +
  `thesis_conviction_at_write` from active thesis if present.
- On edit: new PATCH-able field `resolved_direction`. UI gets a 4-option
  selector in the journal entry detail drawer.

## Effort breakdown

| Step | Scope | Estimate |
|---|---|---|
| 13.1 | Migration 006 + ORM updates + repo updates + 8 tests | 0.5d |
| 13.2 | `signal_quality.py` service + endpoint + 8 tests | 0.5d |
| 13.3 | `calibration.py` service + endpoint + 10 tests | 0.5d |
| 13.4 | Journal endpoints: thesis snapshot on create + resolved_direction patch | 0.5d |
| 13.5 | `SignalQualityChip` on dashboard, 4 sub-score popover | 0.5d |
| 13.6 | `/calibration` page (reliability diagram + summary + table) | 1d |
| 13.7 | Nav item, journal drawer resolve picker, visual QA | 0.5d |

**Total: ~4 working days.**

## Acceptance criteria

1. Dashboard header shows a letter-grade chip; the 4 sub-scores are
   visible on click.
2. `/calibration` page renders a reliability diagram with at least one
   data point from seeded journal entries.
3. New journal entries auto-snapshot the active thesis's id + conviction.
4. Existing journal entries (pre-Phase-13) still render and contribute to
   calibration via the legacy `confidence_pct` field.
5. Marking a journal entry `resolved_direction = 'hit'` flips its bucket
   contribution within one refresh.
6. Backend + frontend tests + typecheck all green.

## Out-of-scope guardrails

- No paper-trade auto-resolution (out, defer).
- No multi-instrument calibration (out, defer to Phase 14).
- No per-thesis sub-grouped reliability — overall calibration only for now.
- No CSV export of calibration data — out for MVP.
