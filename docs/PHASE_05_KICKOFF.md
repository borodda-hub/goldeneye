# Phase 05 — kickoff message (paste into next Sonnet session)

---

Execute Phase 05 per `docs/PHASE_05_PLAN.md`. That plan is the source of truth — it overrides `files/ngti-playbook/ngti-playbook/prompts/05_signal_lab.md` on six locked decisions (tie-break rule, server-side hit/miss with deadband, xgboost reads alt-data, ensemble gains agreement/rationale fields, history ordered by horizon-expiry, full ctx piped into explain_signal).

**Read first:**
- `docs/PHASE_05_PLAN.md` — full plan
- `docs/API_CONTRACTS.md §signals` — current shape (you'll be updating it)
- `docs/AI_BEHAVIOR.md §forbidden_phrases` and `§required_phrasing_patterns` — needed for the LLM eval tests

**Order of work:**
1. **Backend first** — delegate to a single general-purpose agent with the plan doc as input:
   - Extend `ForecastResult` with `inputs_used: list[str]` field
   - Update each model file to populate `inputs_used`; ensure both `supporting` and `contradicting` are non-empty
   - Rewrite `xgboost_placeholder.py` to consume `latest_storage` and `latest_cot` per plan §1.2
   - Extend `ensemble.py` with agreement / input_diversity / confidence_rationale / caveats per plan §1.1; lock the new tie-break rule
   - New `apps/api/services/signal_scoring.py` with the deadband logic
   - Update `routers/signals.py`: populate ForecastContext with alt-data, pipe full ctx into explain_signal, add scoring to /history with new ordering and status filter
   - Update `docs/API_CONTRACTS.md §signals` in the same commit
   - Backend tests per plan §Tests 1-5
2. **Regenerate contracts** — run `pnpm contracts:gen:local` to sync the OpenAPI types
3. **Frontend** — single agent again:
   - `app/(app)/signals/page.tsx` server component pre-fetches /current and /history
   - `app/(app)/signals/SignalsShell.tsx` client component (mirror Phase 04 DashboardShell pattern)
   - `components/signals/` — EnsembleHeader, ModelGrid (with ModelCard subcomponent), ExplanationPanel, HistoryTable
   - Component tests per plan §Tests 6
   - Playwright spec at `apps/web/tests/e2e/signals.spec.ts` per plan §Tests 7
4. **Verify** — run typecheck + test for both stacks before committing
5. **Commit** as `Phase 05: signal lab + ensemble polish`

**Phase 04 gotchas to avoid repeating:**
- Next.js 14 wants `next.config.mjs`, not `.ts` (we already fixed this — don't regress)
- `lightweight-charts` is browser-only — dynamic import with `ssr: false` (not needed here, but Recharts will appear; Recharts works fine in jsdom)
- For client components that use `useChannel` or TanStack Query hooks, tests must mock `../../lib/realtime` and `@tanstack/react-query` respectively
- Use relative imports (`../../../lib/api`) for internal files in tests since the `@/` alias was a source of friction last time — match the existing Phase 04 convention

**Design language to preserve** (locked in Phase 04, must continue):
- Bloomberg/Palantir/TradingView aesthetic — hairlines (`border-line-1/2`), no shadows
- Color = signal only (`text-up/down/flat`, `text-conf-low/medium/high`, `text-accent` for selected state only)
- Numbers always `font-mono tabular-nums` with consistent precision per metric (price 3dp, percent 2dp signed)
- Spacing strictly 4/8/12/16/24/32/48
- Terse terminal copy in empty states ("No scored forecasts in range." not "Nothing here yet!")
- Disclaimer already in AppShell footer — do NOT add another instance

**Run a smoke check before declaring done:**
```
pnpm --filter api run test    # backend tests (existing + new Phase 05)
pnpm --filter web run typecheck
pnpm --filter web run test
```

All three must pass clean. If the Playwright spec exists and `npx playwright install chromium` is available, also run `pnpm --filter web exec playwright test signals.spec.ts` — otherwise note it requires browser install.

When everything's green, commit and update memory at `~/.claude/projects/C--Users-Auror-projects-goldeneye/memory/project_phase_state.md` to reflect Phase 05 complete.
