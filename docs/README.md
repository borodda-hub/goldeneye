# Goldeneye — Documentation Index

This is the map of the `docs/` tree. Before planning or building, find the right doc here
and **read it, don't infer** (per `CLAUDE.md`). Each row lists the doc's **role** and the
date it was **last reviewed** for accuracy against the code.

**Roles:**
- **SOT (roadmap)** — the single source of truth for *what to build next* and in what order.
- **SOT (claims)** — the authoritative ledger of what is validated and on what data.
- **SOT (design)** — authoritative for its own domain (schema, contracts, AI behavior, etc.); kept current in-commit (S7).
- **Living-state** — where the project is *right now*; updated every session.
- **Reference** — strategy, audit, or background context; not a build instruction.
- **Phase plan** — a per-phase `/plan` output; historical once its phase ships.
- **Superseded** — retained for history; do **not** plan from it.

## Top of the hierarchy (read these first)

| Doc | Role | Last reviewed |
|---|---|---|
| `MASTER_PLAN.md` | **SOT (roadmap)** — the only roadmap; all "what next" references it | 2026-06-08 |
| `HANDOFF.md` | **Living-state** — current session state; points to `MASTER_PLAN.md`, never re-specifies it | (per session) |
| `MODEL_DILIGENCE.md` | **SOT (claims)** — provenance ledger; "no claim without provenance" | 2026-06-07 |

## Design source-of-truth docs

| Doc | Role | Last reviewed |
|---|---|---|
| `SCHEMA.md` | SOT (design) — database schema + hypertable rules | — |
| `API_CONTRACTS.md` | SOT (design) — REST + WebSocket contracts | — |
| `AI_BEHAVIOR.md` | SOT (design) — LLM persona, disclaimer, forbidden phrases | — |
| `FRONTEND_COMPONENTS.md` | SOT (design) — component tree + design tokens | — |
| `MOCK_DATA_SPEC.md` | SOT (design) — mock fixtures + seed rules | — |
| `DATA_SOURCES.md` | SOT (design) — real data source endpoints (note: reads mock-first; confirm per F2/§6.3) | — |
| `ARCHITECTURE.md` | SOT (design) — system architecture. §6 model registry + §12 corrected 2026-06-08 (Holt not Prophet; vol-regime is context; backtest engine exists). Defer to `MODEL_DILIGENCE.md` for current model truth | 2026-06-08 |

## Reference (strategy, audit, background)

| Doc | Role | Last reviewed |
|---|---|---|
| `STRATEGY.md` | Reference — strategy & mission realignment | 2026-06-08 |
| `TECHNICAL_AUDIT.md` | Reference — technical due-diligence report (commit `2c5daad`) | 2026-06-08 |
| `INNOVATION_BRIEF.md` | Reference — earlier code-grounded audit + repositioning | — |
| `DEMO_SCRIPT.md` | Reference — demo walkthrough | — |
| `DEPLOYMENT.md` | Reference — deployment runbook | — |
| `THEMING.md` | Reference — theming notes | — |
| `CHARTING_ROADMAP.md` | Reference — charting track roadmap (charting-specific) | — |
| `CHARTING_DEEP_DIVE.md` | Reference — charting design deep dive | — |

## Phase plans

| Doc | Role | Last reviewed |
|---|---|---|
| `PHASE_05_KICKOFF.md`, `PHASE_05_PLAN.md` … `PHASE_17_PLAN.md` | Phase plan (historical) | — |
| `PHASE_31_PLAN.md` | Phase plan — real COT/EIA ingestion (= Master Plan C3) | — |
| `DILIGENCE_AND_30C_PLAN.md` | Phase plan (historical) — diligence wrap-up + 30c | — |

*New `PHASE_*_PLAN.md` files are added here as they are created (per `MASTER_PLAN.md §7.1`).*

## Archived / superseded

| Doc | Role | Superseded |
|---|---|---|
| `archive/BUILD_ROADMAP.md` | **Superseded** by `MASTER_PLAN.md` | 2026-06-08 |
| `archive/ROADMAP.md` | **Superseded** by `MASTER_PLAN.md` | 2026-06-08 |
| `archive/CALIBRATION_ROADMAP.md` | **Superseded** by `MASTER_PLAN.md` | 2026-06-08 |
