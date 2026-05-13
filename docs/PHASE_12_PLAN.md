# Phase 12 Plan — Working Thesis Card

**Goal:** Add the deck's hero feature (slide 5) — a persistent dashboard panel
where the user writes their current thesis, sees evidence auto-pulled from the
latest forecast and scenario run, and sets a conviction level. The active
thesis becomes the anchor for journal entries and Phase 13 calibration.

**Status:** Approved 2026-05-12. Branch base: `cd74f07` (post-Phase 11).

## Scope

In-scope for Phase 12:
- One active thesis per instrument (NG only for MVP)
- Statement, supporting / contradicting / missing-data lists, conviction 0–100
- Auto-population from latest ensemble forecast + latest scenario run
- LLM critique endpoint returning missed-risks / blind-spots / questions
- Dashboard top row with edit modal and critique drawer

Deferred to Phase 13 (Decision Quality):
- Journal entries snapshotting active thesis + conviction at write time
- Personal-calibration reliability diagram
- Conviction-band hit rates ("your 70% theses resolved at 64%")

Deferred to later phases:
- Multi-instrument theses (Phase 14)
- Multi-user / workspace concept

## Data model

```sql
CREATE TABLE theses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_code TEXT NOT NULL DEFAULT 'NG',
  statement TEXT NOT NULL,
  supporting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  contradicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  missing_data JSONB NOT NULL DEFAULT '[]'::jsonb,
  conviction_pct INT NOT NULL CHECK (conviction_pct BETWEEN 0 AND 100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX one_active_thesis_per_instrument
  ON theses (instrument_code) WHERE active;
```

Each evidence entry: `{factor: str, weight: float | null, note: str, source: str | null}`.
`missing_data` is a flat list of strings. Replacing the active thesis sets
`active=false` on the old row and inserts a new row — history is retained for
Phase 13 calibration.

## REST contract

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/v1/thesis/current` | Active thesis or 404 |
| `GET` | `/v1/thesis/seed` | Returns auto-populated draft (not persisted) from latest forecast + scenario |
| `POST` | `/v1/thesis` | Creates new thesis, deactivates previous |
| `PATCH` | `/v1/thesis/{id}` | Update statement / conviction / evidence (only on active rows) |
| `POST` | `/v1/thesis/{id}/critique` | LLM critique → `{missed_risks, blind_spots, questions, safety}` |

All POST/PATCH bodies validate via Pydantic; conviction_pct must be int
0–100, statement non-empty up to 2 000 chars, each evidence array capped at 20.

## LLM critique

New method in `apps/api/services/llm_prompts.py`: `critique_thesis(thesis: dict) -> PromptParts`.
Routes to Sonnet (same tier as scenario narrate). Returns:

```json
{
  "missed_risks": ["short string", ...],
  "blind_spots": ["short string", ...],
  "questions": ["short string", ...]
}
```

Wrapped by `wrap_with_uncertainty(...)` per `safety.py` rules. Forbidden-phrase
scanned. Persona block cached. New service `services/thesis_critique.py`
composes the call.

## Frontend

### Layout

New top row on `/dashboard`, above the existing Row 1 (Live Bar + Front Month +
Recent Events). Existing rows shift down. Mobile (<768 px) wraps to single
column.

```
┌─────────────────────────────────────────────────────────────┐
│  WORKING THESIS · NG                          [⚙ Edit]      │
│  ─────────────────────────────────────────────────────────  │
│  "Cold mid-March extends NE heating demand by 7-10 days;    │
│   storage draws should exceed 5-yr avg through Mar 24."     │
│                                                              │
│  Conviction ████████░░ 78%       Last updated · 4h ago      │
│                                                              │
│  Supporting · 4    Contradicting · 2    Missing data · 3    │
│  [→ Critique]                                                │
└─────────────────────────────────────────────────────────────┘
```

### Components

- `WorkingThesisCard` (server-prefetched) — read view
- `ThesisEditModal` (client) — statement, slider, evidence arrays, save/cancel
- `ThesisCritiqueDrawer` (client) — fetches critique on open, renders three
  bulleted lists with safety envelope
- `EvidenceList` — reusable for both supporting / contradicting in the modal
- `ConvictionSlider` — labeled 0–100 with bucket markers at 25/50/75

### Auto-population

When `/v1/thesis/current` returns 404, the card shows an empty state with a
"Draft a thesis" button. Clicking it calls `/v1/thesis/seed`, which returns a
draft populated from:

- **Supporting** ← top 3 entries by weight from the latest ensemble forecast's
  `supporting` array
- **Contradicting** ← top 3 entries from `contradicting`
- **Missing data** ← deduped union of latest scenario run's
  `data_needed_to_validate` plus the fixed list: "EIA Weekly Storage (Thu)",
  "NWS 6-10 day temp anomaly", "CFTC COT (Fri)"
- **Statement** ← empty (user writes it)
- **Conviction** ← 50

The seed is not persisted until the user clicks Save.

## Effort breakdown

| Step | Scope | Estimate |
|---|---|---|
| 12.1 | Alembic migration, ORM model, `repos/theses.py`, contract tests | 0.5d |
| 12.2 | REST endpoints (5) + 12 route tests | 1d |
| 12.3 | LLM critique service + prompt + safety wrap + 4 tests | 0.5d |
| 12.4 | `WorkingThesisCard` + edit modal + critique drawer | 1d |
| 12.5 | Dashboard integration + seed auto-population | 0.5d |
| 12.6 | E2E happy path + visual QA | 0.5d |

**Total: ~4 working days.**

## Acceptance criteria

1. Dashboard top row shows the active thesis or an empty state with seed button.
2. Editing the statement, slider, or evidence arrays persists and re-renders
   without a full reload.
3. Replacing an active thesis sets the old row to `active=false` and inserts a
   new row — `GET /v1/thesis/current` returns the new one.
4. Critique drawer returns missed-risks / blind-spots / questions in under 5 s,
   wrapped in a safety envelope with the standard disclaimer.
5. All new endpoints have route tests + contract tests; OpenAPI regenerates
   cleanly via `pnpm contracts:gen`.
6. Backend `pytest` + frontend `pnpm test` + `tsc --noEmit` all green.

## Out-of-scope guardrails

- No journal coupling in Phase 12 — keep `theses` table independent.
- No new top-level package; everything fits in existing `apps/api/routers`,
  `apps/api/services`, `apps/api/repos`, `apps/web/components/dashboard`.
- No real-time WebSocket push of thesis edits (single user, edits are local).
- Statement text is plaintext; no markdown rendering, no rich text.
