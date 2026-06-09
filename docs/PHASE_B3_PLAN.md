# Phase B3 Plan — Accounts GA + per-user data scoping (data isolation) — **split into B3a + B3b**

*Plan-only. Produced in a `/plan` session per `MASTER_PLAN.md §7.1`. Covers **B3 only**. No code
changed by this document. Template follows `MASTER_PLAN.md §7.2`. Maps to DD risk **R3**.*

**Source plan:** `MASTER_PLAN.md §4 (Stage B → B3)` — *"Finish Clerk (PR #7); scope every query by
`user_id`; enforce isolation. (Schema/migrations already present via `007_users`/`009`.) DoD:
multi-user isolation tested; anonymous demo still works; gate green."* Depends-on: F0 (done).

**This plan is split into two independently-promotable phases along the data/identity *layer* seam:**
- **B3a — data layer.** Migration + per-user scoping *capability* in the repos/services (a `user_id`
  param, default `None`) + the `replace_active` landmine fix + **query-layer** isolation tests (direct
  repo calls with explicit `user_id`s). Touches **no routers**, adds **no auth**, changes **no
  contracts**, and is **behavior-identical to today** (every caller still passes `None`). It de-risks the
  migration and proves the hard correctness on a small, auth-free surface.
- **B3b — identity + enforcement.** Wire `Depends(get_optional_user)` into the ~24 endpoints, thread the
  scope, add the by-id ownership `404` checks, gate admin/desk, fix the one frontend token gap, **own the
  contracts regen** (the `authorization`-header diff, F1 red→green), and prove isolation **end-to-end**
  (authed A vs. B over HTTP). This is the phase that actually turns multi-user on.

*Why this seam (vs. the literal "scoping vs. auth" cut): at the router layer "scope an endpoint" and "add
the auth dependency" are the same edit and both change contracts, so they can't be cleanly separated
there. One layer down (repo/service vs. router) they separate perfectly. Critically, there is **no
half-enabled-isolation window**: between B3a and B3b the app is exactly today (all-NULL, anonymous), so
B3a never claims an isolation it hasn't enforced.*

**Headline:** isolation is the deliverable, not a side effect. The risk is **one forgotten query**.
§4 below is an exhaustive file:line checklist of every read/write path (now tagged by phase) so a miss is
visible on paper; §6 specifies **negative** tests ("refuses everyone else's data") at both layers.

---

## 0. Current state — what PR #7 actually left done vs. undone (verified)

**DONE and already on `master`** (PR #7 / `feat/accounts-clerk` is fully behind master — its work
landed; the branch is stale and should be closed, not merged):
- **Backend identity:** `auth/clerk.py` (JWKS RS256 verify from the publishable key, `sub` → user id),
  `auth/deps.py` (`get_optional_user` → `User | None`; `get_current_user` → requires sign-in **only when
  Clerk is configured**, else `None`). `[V]`
- **Users schema:** `users` + `user_settings` tables (migration `007_users`, head `009_merge_heads`);
  `repos/users.py` upserts on first authed request. `[V]`
- **Identity + settings endpoints:** `/v1/me`, `/v1/me/settings` GET/PUT (`routers/me.py`) — the **only**
  router wired to the user today. `[V]`
- **Frontend:** `lib/clerk.ts` (`clerkEnabled` flag), `middleware.ts`, `AccountControls`/
  `LandingAccountControls`/`WelcomeModal`, `ProfileSync.tsx` (settings follow the user across devices),
  and crucially `lib/api.ts::apiFetch` **already attaches `Authorization: Bearer <clerk token>`** when
  signed in (`api.ts:26`). `[V]`

**UNDONE — this is all of B3** (the data-scoping half R3 calls out):
- **No personal-artifact router resolves the user.** Only `me.py` uses the auth deps; journal, thesis,
  scenarios, paper, calibration, explain, admin do **not**. `[V]` (grep: `get_optional_user`/
  `get_current_user` appears only in `me.py`).
- **No repo filters by `user_id`.** The columns exist (below) but every query is global. `[V]`
- **`theses` has no `user_id` column at all** — the `007_users` docstring claims "008 scopes them + adds
  it to `theses`," but `008_auto_resolution` only adds `resolved_at`/`auto_resolved`; the scoping was
  **never implemented** (stale docstring). `[V]`
- **Calibration/coaching/equity services aggregate across *all* users** → a signed-in user's scorecard
  would mix in everyone's decisions (a leak, and wrong numbers).
- **By-id endpoints have no ownership check (IDOR):** anyone can read/modify any journal entry, thesis,
  scenario, or paper trade by guessing/knowing its UUID.
- **One frontend gap:** `getCurrentThesis` (`api.ts:573`) uses raw `fetch`, **not** `apiFetch`, so it
  sends **no token** → `/v1/thesis/current` can't be user-scoped until it's routed through `apiFetch`.

---

## 1. Objective + per-phase DoD

**Overall objective:** Make every personal-artifact path user-aware: writes stamp the requester's scope;
reads and by-id mutations are filtered/ownership-checked by it; anonymous/accounts-off behaviour is
unchanged. Delivered in two layers (B3a data, B3b identity), each independently promotable.

### B3a — data layer · DoD
- The migration (§5.A) lands and runs: `theses.user_id` (nullable FK) + indexes + the swapped active
  uniqueness index. No multi-head; existing rows stay `user_id NULL`.
- Repos/services gain a `user_id: UUID | None = None` param and filter on it; the `replace_active`
  deactivate is scoped (the landmine fix).
- **Query-layer isolation tests pass** (§6.A): direct repo/service calls with explicit `user_id`s prove
  filtering + the `replace_active` non-cross-deactivation, *without any HTTP or auth*.
- **No user-facing isolation yet, and that is stated plainly.** Every caller still passes `None`, so the
  running app is **behavior-identical to today** (anonymous NULL pool); the `user_id` params are a
  **tested-but-not-yet-wired seam**. No router touched → **no contracts change → F1 stays green**.
- `pnpm health` green. The HANDOFF note for B3a must say exactly this (no isolation enforced yet).

### B3b — identity + enforcement · DoD
- Every router site in §4 resolves `scope` via `Depends(get_optional_user)` and threads it into the B3a
  repos/services; every by-id path has the `row.user_id != scope → 404` check; admin/desk gated (§10.2).
- The frontend token gap is closed (`getCurrentThesis` → `apiFetch`).
- **Multi-user isolation proven end-to-end** (§6.B): the authed-A-vs-B HTTP negative matrix is green.
- **Anonymous demo still works** — accounts-off and signed-out keep the open NULL-scope behaviour; no
  endpoint silently starts forcing auth (data endpoints use `get_optional_user`, never `get_current_user`).
- **Contracts regenerated** (the `authorization`-header diff) and the **F1 gate green** — B3b owns the
  red→green (§8).
- Look-ahead invariants untouched (S3 N/A; the auto-resolution worker stays system-wide). `pnpm health`
  green; docs updated in-commit (S7).

---

## 2. Verified facts (`[V]` = confirmed in code this session)

**Schema present today**
- `[V]` Nullable bare `user_id UUID` (no FK) on **`user_decision_journals`, `scenario_runs`,
  `paper_trades`, `alerts`** — created in `002_relational.py:139/151/170/191`; `paper_trades` also has
  `paper_trades_user_status_idx (user_id, status)` (`002:185`). Documented in `SCHEMA.md:149/182/218/239`.
- `[V]` **`theses` has NO `user_id`** (`models/orm/theses.py`; `005_theses`). Its active-thesis uniqueness
  is global per `instrument_code` (the partial unique index + `replace_active`'s `WHERE instrument_code
  AND active` at `repos/theses.py:63-67`).
- `[V]` `users` / `user_settings` exist (`007_users`); single alembic head = **`009_merge_heads`**
  (revises `("007", "008_auto_resolution")`). `[V]`

**Auth wiring**
- `[V]` `get_optional_user` returns `User | None` from the bearer token (`auth/deps.py:20`);
  `get_current_user` raises 401 only when `clerk_configured()` and no user (`deps.py:36`), else returns
  `None` → open demo preserved. `clerk_configured()` is false when no publishable key (`clerk.py:35`).
- `[V]` Frontend `apiFetch` attaches the token to **all** calls except `getCurrentThesis` (raw `fetch`,
  `api.ts:573-582`).

**No existing isolation tests** — `[V]` only `test_desk_calibration.py` references `user_id` (it groups
by it for the leaderboard). B3 adds the isolation suite.

---

## 3. The scoping model (anonymous ↔ authenticated coexistence) — design

One rule, applied everywhere. Define the **requester scope** once per request:

```
scope = current_user.id if current_user else None       # None = anonymous / accounts-off
```

- **Reads / list:** filter `Model.user_id == scope`. SQLAlchemy renders `== None` as `IS NULL`, so
  anonymous and accounts-off both see exactly the **shared NULL pool** (today's seeded demo data),
  while a signed-in user sees **only their own rows**. Zero-friction demo preserved by construction.
- **Writes:** stamp `user_id = scope`. Anonymous writes → NULL (as today); signed-in writes → their id.
- **By-id reads/mutations:** load the row, then `if row.user_id != scope: raise HTTPException(404)`
  (404, not 403 — don't reveal that someone else's row exists). This closes the IDOR holes.
- **Auth dependency:** scoped endpoints use `Depends(get_optional_user)` (never forces sign-in). We do
  **not** switch any data endpoint to `get_current_user` — that would break the open demo (violates DoD).

**Confirmed consequence (decision §10.1):** a signed-in user starts with an empty workspace — they do
**not** see the seeded NULL-scope showcase journal/theses. This is intentional: cloning the demo would
pollute the real calibration ledger with synthetic decisions. The seeded demo stays strictly the anonymous
experience.

---

## 4. THE ENUMERATION CHECKLIST — every user-data read/write path

> Legend: **W** write · **R** read/list · **ID** by-id (needs ownership check). "Scope" = the fix.
> **Phase** column: **B3a** = data-layer half (repo/service `user_id` param + filter, migration,
> `replace_active` fix); **B3b** = identity half (router resolves `scope`, threads it, by-id `404`
> ownership checks, gating, frontend). **B3a+B3b** = the row has work in both layers; **B3b** alone =
> router-only (ownership checks / gating, nothing for the data layer to add). A box is *not* done until
> its row is scoped (in its phase) or has a written reason it isn't.

### 4.1 Journal — `user_decision_journals` (has `user_id`)
| # | Path | file:line | R/W | Phase | Scoping to apply |
|---|---|---|---|---|---|
| J1 | `POST /v1/journal` create_entry | `routers/journal.py:99` | W | B3a+B3b | B3a: `journal_repo.create` accepts `user_id`. B3b: router stamps `user_id=scope` into `data` before create (`:136`) |
| J2 | `GET /v1/journal` list_entries | `routers/journal.py:161` | R | B3a+B3b | B3a: `journal_repo.get_recent` filters `user_id==scope` (`repos/journal.py:26`). B3b: router passes `scope` |
| J3 | `GET /v1/journal/{id}` get_entry | `routers/journal.py:184` | B3b | router 404 ownership check after `get_by_id` (`repos/journal.py:42`) |
| J4 | `PATCH /v1/journal/{id}` patch_entry | `routers/journal.py:195` | B3b | router 404 ownership check before `update` (`repos/journal.py:49`) |
| J5 | `POST /v1/journal/extract-prediction` | `routers/journal.py:69` | — | — | **no persistence** (LLM only) → no scoping in either phase |
| J6 | `POST /v1/journal/auto-resolve` | `routers/journal.py:84` | W(sys) | — | background trigger → **system-wide**; resolves each row's own claim, stamps nothing user-related → no per-user scoping. (Open-vs-admin-gated is a B1/ops concern.) |
| J7 | `services/calibration.py::compute_calibration` | `services/calibration.py:201` | R | B3a+B3b | B3a: add `user_id` param → scope `list_with_resolutions` (`repos/journal.py:79`). B3b: `GET /v1/calibration` passes `scope` (`routers/calibration.py:53`) |
| J8 | `services/dq_coach.py::coach_decision_quality` | `services/dq_coach.py:150` | R | B3a+B3b | B3a: same `user_id` param → `list_with_resolutions`. B3b: `GET /v1/calibration/coaching` passes `scope` (`routers/calibration.py:78`) |
| J9 | `routers/explain.py::explain_journal` | `routers/explain.py:105` | B3b | router 404 ownership check after `journal_repo.get_by_id` |
| J10 | `services/auto_resolution.py::resolve_open_decisions` | `services/auto_resolution.py:92` | — | system job → unscoped **by design**; B3a verifies it never cross-contaminates (it only sets each row's own `resolved_*`) — no behavior change |

### 4.2 Theses — `theses` (**needs `user_id` column added**)
| # | Path | file:line | R/W | Phase | Scoping to apply |
|---|---|---|---|---|---|
| T1 | `GET /v1/thesis/current` get_current | `routers/thesis.py:61` | R | B3a+B3b | B3a: `theses_repo.get_active` filters `user_id` (`repos/theses.py:22`). B3b: router passes `scope` **and** fix `getCurrentThesis` → `apiFetch` so the token is sent (`api.ts:573`) |
| T2 | `POST /v1/thesis` create_thesis | `routers/thesis.py:136` | W | B3a+B3b | **B3a (the ⚠️ landmine): scope `replace_active`'s deactivate** (`repos/theses.py:63-67`) by `user_id` + insert `user_id` — else creating a thesis deactivates *other users'* active theses. B3b: router passes `scope` |
| T3 | `PATCH /v1/thesis/{id}` patch_thesis | `routers/thesis.py:211` | ID+W | B3b | router 404 ownership check after `get_by_id` (`repos/theses.py:34`) |
| T4 | `POST /v1/thesis/{id}/critique` | `routers/thesis.py:157` | ID | B3b | router 404 ownership check after `get_by_id` |
| T5 | `POST /v1/thesis/{id}/devils-advocate` | `routers/thesis.py:184` | ID | B3b | router 404 ownership check after `get_by_id` |
| T6 | `GET /v1/thesis/seed` get_seed_draft | `routers/thesis.py:75` | R | B3a+B3b | B3a: `scenarios_repo.get_recent` (`:113`) gains `user_id` filter. B3b: router passes `scope` |
| T7 | active-thesis uniqueness | `repos/theses.py` partial unique index | schema | B3a | migration: unique per **(user_id, instrument_code) where active** (see §5.A) |

### 4.3 Scenarios — `scenario_runs` (has `user_id`)
| # | Path | file:line | R/W | Phase | Scoping to apply |
|---|---|---|---|---|---|
| S1 | `POST /v1/scenarios/run` | `routers/scenarios.py:107` | W | B3a+B3b | B3a: `scenario_repo.create` accepts `user_id` (`repos/scenarios.py:11`). B3b: router stamps `scope` |
| S2 | `GET /v1/scenarios/runs` list_runs | `routers/scenarios.py:158` | R | B3a+B3b | B3a: `scenario_repo.get_recent` filters `user_id` (`repos/scenarios.py:18`). B3b: router passes `scope` |
| S3 | `GET /v1/scenarios/runs/{id}` get_run | `routers/scenarios.py:177` | ID | B3b | router 404 ownership check after `get_by_id` (`repos/scenarios.py:25`) |
| S4 | `GET /v1/scenarios/runs/{id}/export.pdf` | `routers/scenarios.py:201` | ID | B3b | router 404 ownership check after `get_by_id` |
| S5 | `routers/explain.py::explain_scenario` | `routers/explain.py:90` | ID | B3b | router 404 ownership check after `scenario_repo.get_by_id` |
| S6 | `GET /v1/scenarios/templates` | `routers/scenarios.py:149` | — | — | static fixture → no scoping |

### 4.4 Paper trades — `paper_trades` (has `user_id` + index)
| # | Path | file:line | R/W | Phase | Scoping to apply |
|---|---|---|---|---|---|
| P1 | `POST /v1/paper-trades/open` | `routers/paper.py:36` → `paper_engine.open_trade:167` | W | B3a+B3b | B3a: `open_trade`/`trade_repo.create` accept `user_id` (`repos/paper_trades.py:13`). B3b: router stamps `scope` |
| P2 | `POST /v1/paper-trades/{id}/close` | `routers/paper.py:66` → `paper_engine.close_trade:210` | ID+W | B3b | router 404 ownership check after `get_by_id` (`repos/paper_trades.py:35`) |
| P3 | `GET /v1/paper-trades` list_trades | `routers/paper.py:91` | R | B3a+B3b | B3a: `trade_repo.list_trades` filters `user_id` (`repos/paper_trades.py:20`). B3b: router passes `scope` |
| P4 | `GET /v1/paper-trades/{id}` get_trade | `routers/paper.py:112` | ID | B3b | router 404 ownership check after `get_by_id` |
| P5 | `GET /v1/paper-trades/equity-curve` | `routers/paper.py:82` → `paper_engine.equity_curve:305` | R | B3a+B3b | B3a: `equity_curve` filters trades by `user_id`. B3b: router passes `scope` |
| P6 | `paper_engine.current_equity` | `services/paper_engine.py:53` | R | B3a+B3b | B3a: `current_equity` filters by `user_id`. B3b: callers pass `scope` |

### 4.5 Alerts — `alerts` (admin surface; gating-only, not per-user scoping in B3)
| # | Path | file:line | R/W | Phase | Scoping to apply |
|---|---|---|---|---|---|
| A1 | `GET /v1/admin/alerts` list_alerts | `routers/admin.py:108/110` | R | B3b | **auth-required (admin surface)** per §10.2 — enforce sign-in on the admin router. (Per-user *scoping* of alerts is deferred with the visibility model; B3 only stops it being open) |
| A2 | `POST /v1/admin/alerts/{id}/acknowledge` | `routers/admin.py:133` | ID+W | B3b | auth-required (admin surface) per §10.2 |

### 4.6 Desk calibration — cross-user **by design** (B2 surface)
| # | Path | file:line | Phase | Note |
|---|---|---|---|---|
| D1 | `GET /v1/calibration/desk` → `compute_desk_calibration` | `routers/calibration.py:20`, `services/desk_calibration.py:53` | B3b | Groups Brier **by `user_id` across all users** (the leaderboard). Per §10.2: **gate to authenticated-only** in B3 and **defer the cross-user visibility model (who sees whom) to B2**. B3 only stops it being open to anonymous — no data-layer scoping change |

**Count:** **B3a** = 4 tables' repo/service scoping (journal, theses, scenarios, paper) + the migration +
the `replace_active` fix (~12 repo/service edits, no routers). **B3b** = ~24 router sites wired
(`scope` threading + by-id 404s) + admin/desk gating + the frontend fix + contracts. Every row above must
be green **in its phase** or carry a written exemption (J5, J6, J10, S6).

---

## 5. Change set (by phase, then stack lane)

### 5.0 — B3a.1 (CI lock for the isolation suite) — SHIP BEFORE B3b ✅ DONE

The B3a isolation suite lives in `tests/db` (testcontainer), which the fast mocked `test-api`
job does **not** run — so the `replace_active` landmine regression didn't gate the codebase.
B3a.1 closes that: a **separate `db-tests` CI job** (`.github/workflows/ci.yml`) that runs
`uv run --project apps/api pytest tests/db` from the repo root, gating the **whole `tests/db`
dir** (the 5 isolation tests + the existing migrations-run/seed/generators tests). Own job, not
folded into `test-api` — it needs Docker (testcontainers) and is slower. **CI-cost trade
(flagged in the PR):** pulls `timescale/timescaledb:latest-pg16` per run (~+1 min) — deliberate,
so isolation actually gates. **Proven to bite** (red→green, same bar as the contracts F1 lock):
landed green → reintroduced the unscoped `replace_active` → `db-tests` went RED on
`test_replace_active_isolation` → reverted → green. Ships on `feat/phase-b3a1-ci-lock` →
`develop` → `master`, fully promoted before any B3b code.

### 5.A — B3a (data layer) — no routers, no auth, no contracts change

**Schema / migration (one new Alembic revision, down_revision `009_merge_heads`):**
- `ALTER TABLE theses ADD COLUMN user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT;` — nullable FK
  (decision §10.3): real users get integrity, `NULL` preserves the anonymous pool, and `RESTRICT` means a
  user with theses cannot be deleted out from under their decision-ledger data (no silent cascade/orphan).
- Replace the global active-thesis partial unique index with a per-user one: `UNIQUE (user_id,
  instrument_code) WHERE active`. Postgres treats `NULL` `user_id` as distinct, so this index does **not**
  by itself constrain the anonymous pool; per decision §10.4 the anonymous/NULL pool is **one shared demo
  user** (one active thesis per instrument globally), enforced in the repo by scoping `replace_active`'s
  deactivate to the requester scope **including the `user_id IS NULL` branch**. (Verify both the index and
  the repo deactivate in this revision.)
- Add helpful indexes: `(user_id, created_at)` on `user_decision_journals` and `scenario_runs`,
  `(user_id, active)` on `theses`. The other artifact tables keep their existing bare nullable `user_id`
  (no new FKs in B3 — matching FKs on journal/scenarios/paper are a noted follow-up, not B3 scope).
- Update `SCHEMA.md` in the same commit (S7): add `theses.user_id` (FK) + the new indexes; correct the
  stale "008 scopes them" note inherited into `007_users`'s docstring lineage.

**Repos — add `user_id: uuid.UUID | None = None` params + `WHERE user_id == scope`** (default `None`
keeps every current caller behavior-identical): `repos/journal.py` (get_recent, list_with_resolutions,
create), `repos/theses.py` (get_active, **`replace_active` scoped deactivate — the landmine fix**,
`user_id` on insert), `repos/scenarios.py` (get_recent, create), `repos/paper_trades.py` (list_trades,
create, the list/aggregate helpers the engine uses). **By-id repo getters stay id-only** — ownership is a
router 404 in B3b (keeps the check visible at the endpoint, not buried in the repo). **`repos/alerts.py`
is untouched in B3a** (alerts is admin-gating in B3b, not per-user data scoping).

**Services — add a `user_id` param + thread it to the repo:** `calibration.py::compute_calibration`,
`dq_coach.py::coach_decision_quality`, `paper_engine.py` (`current_equity`, `equity_curve`, `open_trade`).
Default `None`. (`auto_resolution.py` stays system-wide — unchanged.)

**Tests:** §6.A query-layer isolation suite (direct repo/service calls with explicit `user_id`s) +
per-repo scope-preservation unit tests. No HTTP/auth.

### 5.B — B3b (identity + enforcement) — routers, ownership, gating, contracts

**Routers/services wiring:** add `user=Depends(get_optional_user)` to every scoped endpoint in §4;
compute `scope = user.id if user else None`; pass `scope` into the B3a repo/service params; stamp it on
writes. Add the `if row.user_id != scope: raise HTTPException(404)` check on **every by-id path** (J3, J4,
J9, T3, T4, T5, S3, S4, S5, P2, P4). Gate `/v1/admin/*` (A1/A2) and `/v1/calibration/desk` (D1) to
authenticated-only per §10.2 — **without** inventing a leaderboard visibility policy (deferred to B2).

**Frontend:** route `getCurrentThesis` through `apiFetch` (`api.ts:573`) so the token is sent. Everything
else already flows the token. No new UI (sign-in already exists).

**Contracts:** regen after wiring (the `authorization`-header diff) — B3b owns the F1 red→green (§8).

**Tests:** §6.B end-to-end HTTP isolation matrix (authed A vs. B).

---

## 6. Isolation tests — NEGATIVE tests are the acceptance bar (S5)

"Returns my own data" is **insufficient** — the bar is "refuses everyone else's." The proof is split to
match the layers: B3a proves it at the **query layer** (no HTTP), B3b proves it **end-to-end** (HTTP, real
identities). Together: unit + integration, each shipping with the code it covers.

### 6.A — B3a query-layer isolation (direct repo/service calls, explicit `user_id`s)

No auth, no HTTP. Seed two `users` rows (A, B) — needed because `theses.user_id` is now an FK — and insert
artifact rows directly with `user_id = A`, `user_id = B`, and `user_id = NULL`. Then call the repos/services
**with an explicit `user_id`** and assert:

1. **List filtering:** `journal_repo.get_recent(user_id=A)` / `scenario_repo.get_recent(user_id=A)` /
   `trade_repo.list_trades(user_id=A)` / `theses_repo.get_active(user_id=A)` return **only A's** rows —
   never B's, never the NULL pool.
2. **`replace_active` non-cross-deactivation (the ⚠️ landmine, T2):** with A and B both holding an active
   NG thesis, `theses_repo.replace_active(user_id=B, instrument_code="NG", …)` leaves **A's** row
   `active=True` and deactivates only B's. Repeat for the NULL pool (anonymous = one shared demo user):
   `replace_active(user_id=None, …)` collapses only the NULL pool's active row.
3. **Service scoping:** `compute_calibration(user_id=A)` / `coach_decision_quality(user_id=A)` /
   `paper_engine.equity_curve(user_id=A)` aggregate **only A's** resolved rows/trades.
4. **Default-`None` is behavior-preserving:** calling any of the above with no `user_id` (the current
   call convention) returns the NULL pool exactly as today — the seam is inert until B3b wires it.

Lock as a parametrized suite over (repo/service × A/B/NULL). This is the B3a acceptance gate.

### 6.B — B3b end-to-end HTTP isolation matrix (authed A vs. B)

With Clerk configured and two distinct users A and B (stub `get_optional_user` to return A or B per
request, or mint/verify test tokens), over the real endpoints assert:

1. **Cross-read denied/empty:** A creates a journal entry / thesis / scenario / paper trade; **B's**
   `GET /list` does **not** include it; **B's** `GET /{A's id}` → **404**.
2. **Cross-write denied:** B's `PATCH/POST .../{A's id}` (journal patch, thesis patch/critique/devils,
   paper close, scenario export, explain-journal/scenario) → **404**, and A's row is **unchanged**.
3. **Thesis deactivate isolation (T2 ⚠️), end-to-end:** A has an active NG thesis; B `POST /v1/thesis` for
   NG; **A's** thesis stays `active=True` (re-asserts 6.A.2 through the HTTP path).
4. **Calibration/coaching isolation (J7/J8):** A's `GET /v1/calibration` reflects **only A's** entries.
5. **Equity isolation (P5/P6):** A's `equity-curve` sums only A's closed trades.
6. **Anonymous pool intact:** with **no** auth (and with Clerk **off**), the seeded NULL-scope demo data is
   still readable/writable exactly as today (a positive test guarding the demo).
7. **Anonymous ↔ signed-in separation:** an anonymous write (user_id NULL) is **not** visible to signed-in
   A, and A's write is **not** visible anonymously.
8. **Admin/desk gating (§10.2):** anonymous `GET /v1/admin/alerts` and `GET /v1/calibration/desk` are
   **denied** when accounts are configured.

Each assertion is a matrix row; a missing endpoint = an untested isolation hole. Lock as a parametrized
test over the endpoint list. This is the B3b acceptance gate.

---

## 7. Gates (S1–S8 — which apply)

- **S1 (WIP=1):** B3a and B3b are **strictly sequential** (B3b depends on B3a's repo/service params +
  migration) — one primary thread, promoted in order, never overlapping. (B1 overlaps `auto_resolution`/
  journal — coordinate around it.)
- **S2:** full `pnpm health` green **for each phase** (B3a green with no router/contract change; B3b green
  including the regenerated contracts).
- **S3 (look-ahead):** **N/A to model/resolution logic** — B3 changes *who sees* rows, not how forecasts
  resolve. The auto-resolution worker stays system-wide and look-ahead-safe; the cheating-model proof is
  untouched and must still pass (both phases).
- **S4 (provenance):** no predictive claim changes.
- **S5 (test-lock):** §6.A is B3a's locked regression; §6.B is B3b's.
- **S6 (claims gate):** **B3a — affirmatively state "no user-facing isolation yet"** (so no one reads the
  merged capability as enforced). **B3b** — per §10.1 a signed-in user starts empty; ensure the empty-state
  copy reads sensibly (a fresh workspace, not an error). No public copy change either phase.
- **S7 (docs-in-commit):** B3a → `SCHEMA.md` (new column/indexes) + `HANDOFF.md` (the "seam, not enforced
  yet" note). B3b → `API_CONTRACTS.md` (auth header now accepted), `ARCHITECTURE.md` auth/tenancy note,
  `HANDOFF.md` (isolation live).
- **S8:** two-lane, **two promotions** — `feat/phase-b3a-scoping` → `develop` → `master`, then
  `feat/phase-b3b-identity` → `develop` → `master` (each with its own owner sign-off).

---

## 8. Migration / contracts / CI impact

- **Migration (B3a):** one new revision (down_revision `009_merge_heads`) per §5.A; run `make migrate`.
  **No multi-head** risk (single head today). Backfill: existing rows keep `user_id NULL` (the anonymous
  pool) — no data migration needed.
- **Contracts — B3a stays GREEN, B3b owns the RED→GREEN.**
  - **B3a touches no routers**, so `openapi.json` is **unchanged** → the F1 `contracts` job passes with no
    regen. (Sanity: `pnpm contracts:check` should be a no-op on the B3a branch.)
  - **B3b** adds `Depends(get_optional_user)` (which declares `authorization: str | None =
    Header(default=None)`), so FastAPI adds an **`authorization` header parameter** to each scoped path →
    `packages/contracts` **will** change and the **F1 job will (correctly) fail until regenerated**. B3b's
    flow: wire → `curl … -> packages/contracts/openapi.json && pnpm contracts:gen:local` (or `pnpm
    contracts:check`) → commit the regenerated artifacts → F1 green. Response *bodies* are unchanged (no
    new fields), so the web client types are unaffected beyond the header param.
- **Testcontainers:** both isolation suites need the Timescale test DB (already in CI `test-api`).

---

## 9. Promotion — two independent promotions

Close the stale `feat/accounts-clerk` / PR #7 (its content is already on master; do not merge it).

### B3a — `feat/phase-b3a-scoping` off `develop`
- **Commits:** (1) migration + `SCHEMA.md` (`theses.user_id` FK + indexes + swapped active index);
  (2) repos `user_id` params + filters + the `replace_active` scoped-deactivate fix; (3) services
  `user_id` params; (4) §6.A query-layer isolation suite; (5) `HANDOFF` note.
- **Sign-off note:** B3a complete — per-user scoping **capability** landed at the data layer + the
  `replace_active` landmine fixed; query-layer isolation (incl. non-cross-deactivation) proven by direct
  repo tests. **No user-facing isolation yet — every caller passes `None`, app behavior-identical to
  today; the `user_id` params are a tested-but-unwired seam.** No router/contract change → F1 green.
  `pnpm health` green.

### B3b — `feat/phase-b3b-identity` off `develop` (after B3a on `master`)
- **Commits:** (1) routers/services wire `get_optional_user` + thread `scope`; (2) by-id `404` ownership
  checks; (3) admin/desk gating; (4) frontend `getCurrentThesis` → `apiFetch`; (5) **contracts regen**;
  (6) §6.B HTTP isolation matrix; (7) docs (`API_CONTRACTS`, `ARCHITECTURE`, `HANDOFF`).
- **Sign-off note:** B3b complete — every §4 router site scoped (or exempted); §6.B negative matrix green;
  anonymous + accounts-off demo unchanged; admin/desk gated (no B2 visibility policy invented); contracts
  regenerated (auth header), F1 red→green; S3 proof untouched. `pnpm health` green. **Multi-user isolation
  is now live.**
- **After B3b:** unblocks **B2** (per-analyst skill-vs-luck) and **B4** (decision/audit ledger).

---

## 10. Decisions (settled by the owner — these are now requirements)

1. **Signed-in users start empty — CONFIRMED.** A new account does **not** inherit the seeded NULL-scope
   demo data; cloning it would pollute the real calibration ledger with synthetic decisions. The seeded
   pool remains strictly the anonymous experience.
2. **Leaderboard / admin gating — auth-required, no visibility policy invented in B3.**
   - `GET /v1/admin/alerts` + `POST /v1/admin/alerts/{id}/acknowledge` (A1/A2): **auth-required** (admin
     surface) — use `get_current_user`-style enforcement on the admin router so it's not open in
     multi-tenant.
   - `GET /v1/calibration/desk` (D1): **gate to authenticated-only** for now. **Explicitly DEFER the
     cross-user visibility model** (who can see whom on the leaderboard) to **B2** — B3 must **not** invent
     a visibility policy. B3's only job here is "not open to anonymous"; the per-analyst leaderboard
     semantics (self-only vs. desk-wide vs. admin) are a B2 decision.
3. **`theses.user_id` = NULLABLE FK → `users.id`, `ON DELETE RESTRICT`.** Real users get referential
   integrity; `NULL` preserves the anonymous pool. **Delete behaviour is `ON DELETE RESTRICT`, NOT cascade
   and NOT set-null** — thesis rows are decision-ledger data we must never silently delete or orphan;
   deleting a user with theses must fail loudly (handled deliberately, not implicitly). *(The other
   artifact tables keep their existing bare nullable `user_id` for now; adding matching FKs to journal/
   scenarios/paper is a follow-up, not B3 scope — note it but don't expand.)*
4. **Active-thesis uniqueness = per-(`user_id`, `instrument_code`) where `active`; anonymous is a single
   shared demo user.** Postgres treats `NULL` `user_id` as distinct in a unique index, so that index alone
   would **not** constrain the anonymous pool. **Assumption, now documented as a requirement:** the
   anonymous/NULL-scope pool behaves as **one shared demo user** — exactly one active thesis per instrument
   globally. Enforce it by scoping `replace_active`'s deactivate to match the requester scope (including the
   `user_id IS NULL` branch for anonymous), so the anonymous pool collapses to a single active row per
   instrument just like a real user. This is a deliberate product assumption (anonymous = the shared
   showcase desk), called out here so it is never a future surprise.
