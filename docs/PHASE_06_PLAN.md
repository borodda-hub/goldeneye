# Phase 06 Plan — Scenario Lab + LLM Narrative

This plan refines `files/ngti-playbook/ngti-playbook/prompts/06_scenario_lab.md` for the realities of the current codebase. Original prompt remains valid for everything not contradicted here.

## Override decisions (locked)

1. **Shock types stay as 4 primitives, not 6 composite types.** The prompt lists `WeatherShock, LngExportShock, ProductionShock, DemandShock, GeopoliticalShock, HurricaneShock`. But the existing fixtures (`packages/fixtures/scenario_templates.json`) and `docs/API_CONTRACTS.md §scenarios` both use only 4 primitive shock types (`weather`, `lng_export`, `production`, `storage`). The 6 fixture templates *compose* the 4 primitives — "hurricane" is `production + lng_export`, "demand" is multiple `weather` shocks, etc. Adding redundant composite classes would mean two parallel ways to express the same shock and a larger blast radius. The 4-primitive discriminated union is what the engine already accepts and what the schema documents.

2. **Strict Pydantic v2 discriminated union with field validators.** Today `routers/scenarios.py::ShockItem` has every field optional with no validation — a `weather` shock with `delta_bcfd` is happily accepted. Phase 06 tightens this: each shock class has only the fields it uses, with bounds via `Field(ge=..., le=...)`.

3. **Structural fields are NOT LLM-generated.** Reaffirming the prompt's "Hard do NOT": `assumptions`, `counterarguments`, and `data_needed_to_validate` come from shock metadata and the model registry deterministically. The LLM only writes the `narrative` prose. The engine already does this; tests will assert it.

4. **LLM eval test mocks the LLM call and uses fixture responses.** Following the Phase 05 corpus test pattern, `tests/llm/test_narrate_scenario.py` does not call a live LLM. It verifies (a) the inference-marker regex passes on fixture responses, (b) the 5 required sections are detectable via keyword regex, (c) the engine produces non-empty structural fields for all 6 templates. A separate `pytest -m llm_live` corpus can be added later for live runs.

5. **Frontend uses a single `ScenariosShell` client component.** Mirrors Phase 04/05 pattern: server `page.tsx` prefetches templates + recent runs, hands them to a client shell that owns shock-builder state and result state.

## Backend deliverables

### 1. Strict shock union in `apps/api/routers/scenarios.py`

Replace `ShockItem` with a discriminated union:

```python
from typing import Literal, Annotated, Union
from pydantic import BaseModel, Field

class WeatherShock(BaseModel):
    type: Literal["weather"]
    region: str = Field(min_length=1, max_length=64)
    delta_temp_f: float = Field(ge=-50, le=50)
    days: int = Field(ge=1, le=60)

class LngExportShock(BaseModel):
    type: Literal["lng_export"]
    delta_bcfd: float = Field(ge=-15, le=15)
    days: int = Field(ge=1, le=60)

class ProductionShock(BaseModel):
    type: Literal["production"]
    delta_bcfd: float = Field(ge=-15, le=15)
    days: int = Field(ge=1, le=60)

class StorageShock(BaseModel):
    type: Literal["storage"]
    delta_bcf: float = Field(ge=-500, le=500)
    days: int = Field(ge=1, le=60)

Shock = Annotated[
    Union[WeatherShock, LngExportShock, ProductionShock, StorageShock],
    Field(discriminator="type"),
]

class ScenarioRunRequest(BaseModel):
    instrument: str = "NG"
    name: str = Field(min_length=1, max_length=200)
    shocks: list[Shock] = Field(min_length=1, max_length=10)
```

### 2. Extract `apply()` from `scenario_engine.py`

Current `run_scenario` inlines shock application. Refactor:

```python
def apply(shocks: list[dict], baseline_ctx: ForecastContext) -> tuple[ForecastContext, list[str]]:
    """
    Apply shocks (composably — later shocks compose on earlier output).
    Returns (shocked_ctx, assumptions).
    """
```

`run_scenario` then becomes:
1. Call `apply(shocks, baseline_ctx)` → `(shocked_ctx, assumptions)`
2. `run_all` both contexts
3. `compute_ensemble` both
4. Compute deltas
5. Compute `counterarguments` and `data_needed_to_validate` structurally
6. Call `narrate_scenario` for prose
7. Wrap with safety envelope (already done by `narrate_scenario`)
8. Return result dict

### 3. New backend tests

- `apps/api/tests/test_scenario_shocks.py` — Pydantic validation: rejects unknown type, rejects out-of-bounds delta, accepts valid each type, requires at least one shock.
- `apps/api/tests/test_scenario_engine.py` — Engine: applies shocks composably, produces non-empty `assumptions`/`counterarguments`/`data_needed_to_validate`/`narrative`, all 6 templates run without error.
- `apps/api/tests/llm/test_narrate_scenario.py` — Corpus test: fixture responses for each of 6 templates pass inference regex + contain keywords for all 5 narrative sections.

## Frontend deliverables

### Layout (1280×800, scrolls vertically — runs are reviewable)

```
HeaderRow (Scenario Lab + last run timestamp)
─────────────────────────────────────────────────
TemplateGallery (6 cards, grid-cols-3, gap-4)
─────────────────────────────────────────────────
ShockBuilder (current shocks list + add/edit/remove) | RunButton (right)
─────────────────────────────────────────────────
ResultPanel (after a run completes)
  ▸ directional pressure chip + confidence + timeframe
  ▸ expected range
  ▸ Assumptions (numbered) · Counterarguments (numbered) · Data needed (numbered)
  ▸ Narrative prose
  ▸ SafetyEnvelopeNote (open by default)
─────────────────────────────────────────────────
ScenarioHistoryList (recent 20 runs, click to re-run)
```

### Components

- `apps/web/app/(app)/scenarios/page.tsx` — async server prefetch of `/templates` + `/runs?limit=20`, passes to client shell.
- `apps/web/app/(app)/scenarios/ScenariosShell.tsx` — client shell, holds shock-builder + result state, owns the mutation call.
- `apps/web/app/(app)/scenarios/types.ts` — TypeScript interfaces.
- `apps/web/components/scenarios/TemplateGallery.tsx` — 6 cards, click loads shocks.
- `apps/web/components/scenarios/ShockBuilder.tsx` — list + per-type form. Simple add/remove (no drag-reorder for MVP — keep scope tight).
- `apps/web/components/scenarios/RunButton.tsx` — disabled on empty, shows "running…" state during mutation.
- `apps/web/components/scenarios/ResultPanel.tsx` — full result render, includes `<SafetyEnvelopeNote>`.
- `apps/web/components/scenarios/ScenarioHistoryList.tsx` — recent runs list.
- Component tests in `components/scenarios/__tests__/` for each.
- Playwright spec `apps/web/tests/e2e/scenarios.spec.ts`.

### Design language (locked from Phase 04/05)
- Hairlines `border-line-1/2`, no shadows.
- Color = signal only (`text-up/down/flat`, `text-conf-*`).
- Numbers `font-mono tabular-nums`.
- Spacing strictly 4/8/12/16/24/32/48.
- Disclaimer is in AppShell footer — DO NOT add another instance.

## Acceptance criteria

- All 6 template scenarios run end-to-end via `/v1/scenarios/run` and persist to `scenario_runs`.
- `ResultPanel` populates all 6 sub-sections after a run.
- Forbidden-phrase regex matches zero times against `/scenarios` page content.
- `pnpm --filter web run typecheck && test` passes; `pytest` in `apps/api` passes.
- Updated `docs/API_CONTRACTS.md §scenarios` in same commit.

## Forbidden

- Do not let the LLM generate structural fields (`assumptions`, `counterarguments`, `data_needed_to_validate`).
- Do not introduce new shock types.
- Do not bypass `services/safety.py::wrap_with_uncertainty`.
- Do not modify other screens.

When complete, commit `Phase 06: scenario lab + narrative`.
