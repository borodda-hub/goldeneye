# Phase B3 Plan — Accounts GA + per-user data scoping (data isolation)

*Plan-only. Produced in a `/plan` session per `MASTER_PLAN.md §7.1`. Covers **B3 only**. No code
changed by this document. Template follows `MASTER_PLAN.md §7.2`. Maps to DD risk **R3**.*

**Source plan:** `MASTER_PLAN.md §4 (Stage B → B3)` — *"Finish Clerk (PR #7); scope every query by
`user_id`; enforce isolation. (Schema/migrations already present via `007_users`/`009`.) DoD:
multi-user isolation tested; anonymous demo still works; gate green."* Depends-on: F0 (done).

**Headline:** isolation is the deliverable, not a side effect. The risk is **one forgotten query**.
§4 below is an exhaustive file:line checklist of every read/write path so a miss is visible on paper;
§6 specifies **negative** tests ("refuses everyone else's data"), which are the real acceptance bar.

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

## 1. Objective + DoD

**Objective:** Make every personal-artifact path user-aware: writes stamp the requester's scope; reads
and by-id mutations are filtered/ownership-checked by it; anonymous/accounts-off behaviour is unchanged.

**DoD (from `MASTER_PLAN.md §4` B3):**
- Every read/write path in the §4 checklist is scoped or has a documented reason it isn't.
- **Multi-user isolation tested** with **negative tests** (§6): authed as A, denied/empty for B's data on
  every scoped endpoint.
- **Anonymous demo still works** — accounts-off and signed-out both keep the open NULL-scope behaviour;
  no endpoint silently starts requiring auth.
- Look-ahead invariants untouched (S3 N/A — no model/resolution logic changes; auto-resolution worker
  stays system-wide and stamps nothing user-related).
- `pnpm health` green; contracts regenerated + F1 gate green; docs updated in-commit (S7).

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
> A box is *not* done until its row is scoped or has a written reason it isn't.

### 4.1 Journal — `user_decision_journals` (has `user_id`)
| # | Path | file:line | R/W | Scoping to apply |
|---|---|---|---|---|
| J1 | `POST /v1/journal` create_entry | `routers/journal.py:99` | W | stamp `user_id=scope` into `data` before `journal_repo.create` (`:136`) |
| J2 | `GET /v1/journal` list_entries | `routers/journal.py:161` | R | pass `scope` → `journal_repo.get_recent` filters `user_id==scope` (`repos/journal.py:26`) |
| J3 | `GET /v1/journal/{id}` get_entry | `routers/journal.py:184` | ID | ownership check after `get_by_id` (`repos/journal.py:42`) |
| J4 | `PATCH /v1/journal/{id}` patch_entry | `routers/journal.py:195` | ID+W | ownership check before `update` (`repos/journal.py:49`) |
| J5 | `POST /v1/journal/extract-prediction` | `routers/journal.py:69` | — | **no persistence** (LLM only) → no scoping needed |
| J6 | `POST /v1/journal/auto-resolve` | `routers/journal.py:84` | W(sys) | background trigger → **system-wide** (all users); resolves each row's own claim, stamps nothing user-related → no per-user scoping. (Whether the manual trigger stays open vs. admin-gated is a B1/ops concern, not B3 data-scoping.) |
| J7 | `services/calibration.py::compute_calibration` | `services/calibration.py:201` | R | add `user_id` param → scope `list_with_resolutions` (`repos/journal.py:79`); called by `GET /v1/calibration` (`routers/calibration.py:53`) |
| J8 | `services/dq_coach.py::coach_decision_quality` | `services/dq_coach.py:150` | R | same scope param → `list_with_resolutions`; called by `GET /v1/calibration/coaching` (`routers/calibration.py:78`) |
| J9 | `routers/explain.py::explain_journal` | `routers/explain.py:105` | ID | ownership check after `journal_repo.get_by_id` |
| J10 | `services/auto_resolution.py::resolve_open_decisions` | `services/auto_resolution.py:92` | R+W(sys) | system job → unscoped **by design**; verify it never cross-contaminates (it only sets each row's own `resolved_*`) |

### 4.2 Theses — `theses` (**needs `user_id` column added**)
| # | Path | file:line | R/W | Scoping to apply |
|---|---|---|---|---|
| T1 | `GET /v1/thesis/current` get_current | `routers/thesis.py:61` | R | scope `theses_repo.get_active` by `user_id` (`repos/theses.py:22`). **Also fix `getCurrentThesis` to use `apiFetch`** so the token is sent (`api.ts:573`) |
| T2 | `POST /v1/thesis` create_thesis | `routers/thesis.py:136` | W | stamp `user_id=scope`; **scope the deactivate in `replace_active`** (`repos/theses.py:63-67`) by `user_id` — else creating a thesis deactivates *other users'* active theses ⚠️ |
| T3 | `PATCH /v1/thesis/{id}` patch_thesis | `routers/thesis.py:211` | ID+W | ownership check after `get_by_id` (`repos/theses.py:34`) |
| T4 | `POST /v1/thesis/{id}/critique` | `routers/thesis.py:157` | ID | ownership check after `get_by_id` |
| T5 | `POST /v1/thesis/{id}/devils-advocate` | `routers/thesis.py:184` | ID | ownership check after `get_by_id` |
| T6 | `GET /v1/thesis/seed` get_seed_draft | `routers/thesis.py:75` | R | reads forecasts (global) + **`scenarios_repo.get_recent`** (`:113`) for missing-data hints → scope that scenario read to `scope` (ties to S3 below) |
| T7 | active-thesis uniqueness | `repos/theses.py` partial unique index | schema | index must become unique per **(user_id, instrument_code) where active** — covered by the migration |

### 4.3 Scenarios — `scenario_runs` (has `user_id`)
| # | Path | file:line | R/W | Scoping to apply |
|---|---|---|---|---|
| S1 | `POST /v1/scenarios/run` | `routers/scenarios.py:107` | W | stamp `user_id=scope` in `scenario_repo.create` (`repos/scenarios.py:11`) |
| S2 | `GET /v1/scenarios/runs` list_runs | `routers/scenarios.py:158` | R | scope `scenario_repo.get_recent` (`repos/scenarios.py:18`) |
| S3 | `GET /v1/scenarios/runs/{id}` get_run | `routers/scenarios.py:177` | ID | ownership check after `get_by_id` (`repos/scenarios.py:25`) |
| S4 | `GET /v1/scenarios/runs/{id}/export.pdf` | `routers/scenarios.py:201` | ID | ownership check after `get_by_id` |
| S5 | `routers/explain.py::explain_scenario` | `routers/explain.py:90` | ID | ownership check after `scenario_repo.get_by_id` |
| S6 | `GET /v1/scenarios/templates` | `routers/scenarios.py:149` | — | static fixture → no scoping |

### 4.4 Paper trades — `paper_trades` (has `user_id` + index)
| # | Path | file:line | R/W | Scoping to apply |
|---|---|---|---|---|
| P1 | `POST /v1/paper-trades/open` | `routers/paper.py:36` → `paper_engine.open_trade:167` | W | thread `user_id=scope` into `trade_repo.create` (`repos/paper_trades.py:13`) |
| P2 | `POST /v1/paper-trades/{id}/close` | `routers/paper.py:66` → `paper_engine.close_trade:210` | ID+W | ownership check after `get_by_id` (`repos/paper_trades.py:35`) |
| P3 | `GET /v1/paper-trades` list_trades | `routers/paper.py:91` | R | scope `trade_repo.list_trades` (`repos/paper_trades.py:20`) |
| P4 | `GET /v1/paper-trades/{id}` get_trade | `routers/paper.py:112` | ID | ownership check after `get_by_id` |
| P5 | `GET /v1/paper-trades/equity-curve` | `routers/paper.py:82` → `paper_engine.equity_curve:305` | R | scope the trades query by `user_id` |
| P6 | `paper_engine.current_equity` | `services/paper_engine.py:53` | R | scope by `user_id` (used by equity/curve math) |

### 4.5 Alerts — `alerts` (has `user_id`; admin surface)
| # | Path | file:line | R/W | Scoping to apply |
|---|---|---|---|---|
| A1 | `GET /v1/admin/alerts` list_alerts | `routers/admin.py:108/110` | R | **auth-required (admin surface)** per decision §10.2 — enforce sign-in on the admin router so it's not open in multi-tenant |
| A2 | `POST /v1/admin/alerts/{id}/acknowledge` | `routers/admin.py:133` | ID+W | auth-required (admin surface) per §10.2 |

### 4.6 Desk calibration — cross-user **by design** (B2 surface)
| # | Path | file:line | Note |
|---|---|---|---|
| D1 | `GET /v1/calibration/desk` → `compute_desk_calibration` | `routers/calibration.py:20`, `services/desk_calibration.py:53` | Groups Brier **by `user_id` across all users** (the leaderboard). Per decision §10.2: **gate to authenticated-only** in B3, and **explicitly defer the cross-user visibility model (who sees whom) to B2**. B3 must not invent a visibility policy — it only stops the endpoint being open to anonymous |

**Count:** 4 tables to scope at the query layer + `theses` needs a column; **~24 call sites** across 7
routers + 4 services. Every row above must be green or have a written exemption (J5, J6, J10, S6, D1).

---

## 5. Change set (by stack lane)

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

**Backend — repos (add `user_id: uuid.UUID | None` params + `WHERE user_id == scope`):**
`repos/journal.py` (get_recent, get_by_id*, list_with_resolutions, create), `repos/theses.py` (get_active,
replace_active **scoped deactivate**, get_by_id*, +`user_id` on insert), `repos/scenarios.py` (get_recent,
get_by_id*, create), `repos/paper_trades.py` (list_trades, get_by_id*, create, list_open/closed used by
engine), `repos/alerts.py` (get_unread, get_all, get_by_id*). *by-id repos can stay id-only and let the
router do the ownership check — pick one pattern and apply it uniformly (recommend: repo stays id-only,
router enforces ownership, so the check is visible at the endpoint).

**Backend — routers/services (resolve scope + thread it):** add `user=Depends(get_optional_user)` to
every scoped endpoint in §4; compute `scope = user.id if user else None`; pass to repos/services; add the
`row.user_id != scope → 404` check on every by-id path. Services `calibration.py`, `dq_coach.py`,
`paper_engine.py` take a `user_id` param.

**Frontend:** route `getCurrentThesis` through `apiFetch` (`api.ts:573`) so the token is sent. (Everything
else already flows the token.) No new UI required for isolation; sign-in UI already exists.

**Tests:** the isolation suite (§6) + scope-preservation unit tests on each repo.

---

## 6. Isolation tests — NEGATIVE tests are the acceptance bar (S5)

"Returns my own data" is **insufficient**. For **every** scoped endpoint, with Clerk configured and two
distinct users A and B (seed two `users` rows; stub `get_optional_user` to return A or B per request, or
mint/verify test tokens), assert:

1. **Cross-read denied/empty:** A creates a journal entry / thesis / scenario / paper trade; **B's**
   `GET /list` does **not** include it; **B's** `GET /{A's id}` → **404**.
2. **Cross-write denied:** B's `PATCH/POST .../{A's id}` (journal patch, thesis patch/critique/devils,
   paper close, scenario export, explain-journal/scenario) → **404**, and A's row is **unchanged**.
3. **Thesis deactivate isolation (T2 ⚠️):** A has an active thesis for NG; B creates a thesis for NG;
   **A's** thesis stays `active=True` (B's create only deactivated B's own).
4. **Calibration/coaching isolation (J7/J8):** A and B each have resolved decisions; A's
   `GET /v1/calibration` reflects **only A's** entries (counts + buckets), not the union.
5. **Equity isolation (P5/P6):** A's `equity-curve` sums only A's closed trades.
6. **Anonymous pool intact:** with **no** auth (and with Clerk **off**), the seeded NULL-scope demo data
   is still readable/writable exactly as today (a positive test guarding the demo).
7. **Anonymous ↔ signed-in separation:** an anonymous write (user_id NULL) is **not** visible to signed-in
   A, and A's write is **not** visible anonymously.

Each assertion is a row in the matrix; a missing endpoint in this matrix = an untested isolation hole.
Lock the matrix as a parametrized test over the endpoint list.

---

## 7. Gates (S1–S8 — which apply)

- **S1 (WIP=1):** B3 is the single primary thread. (B1 may run first or parallel only if file-disjoint;
  per §5 they overlap on `auto_resolution`/journal — sequence B3 around B1 or coordinate.)
- **S2:** full `pnpm health` green.
- **S3 (look-ahead):** **N/A to model/resolution logic** — B3 changes *who sees* rows, not how forecasts
  resolve. The auto-resolution worker stays system-wide and look-ahead-safe; the cheating-model proof is
  untouched and must still pass.
- **S4 (provenance):** no predictive claim changes.
- **S5 (test-lock):** the §6 isolation matrix is the locked regression.
- **S6 (claims gate):** no public copy change; the demo still reads honestly. Per §10.1 a signed-in user
  starts empty — ensure the empty-state copy reads sensibly (a fresh workspace, not an error).
- **S7 (docs-in-commit):** `SCHEMA.md` (new column/indexes), `API_CONTRACTS.md` (auth header now accepted),
  `ARCHITECTURE.md` auth/tenancy note, `HANDOFF.md`.
- **S8:** `feat/phase-b3-accounts` → `develop` → owner sign-off → `master`.

---

## 8. Migration / contracts / CI impact

- **Migration:** one new revision (down_revision `009_merge_heads`) per §5; run `make migrate`. **No
  multi-head** risk (single head today). Backfill: existing rows keep `user_id NULL` (the anonymous pool)
  — no data migration needed.
- **Contracts / F1 CI — expect a real diff:** adding `Depends(get_optional_user)` (which declares
  `authorization: str | None = Header(default=None)`) makes FastAPI add an **`authorization` header
  parameter** to each scoped path in `openapi.json`. So `packages/contracts` **will** change and the
  **F1 `contracts` job will (correctly) fail until regenerated**. Plan: after wiring, run `curl … ->
  packages/contracts/openapi.json && pnpm contracts:gen:local` (or `pnpm contracts:check`) and commit the
  regenerated artifacts. Response *bodies* are unchanged (no new fields), so the web client types are
  unaffected beyond the header param.
- **Testcontainers:** the isolation suite needs the Timescale test DB (already in CI `test-api`).

---

## 9. Promotion

- **Branch:** `feat/phase-b3-accounts` off `develop`. Close the stale `feat/accounts-clerk` / PR #7
  (its content is already on master; do not merge it).
- **Commit split (suggested):** (1) migration + `SCHEMA.md` (`theses.user_id` + indexes); (2) repos scope
  params + tests; (3) routers/services wire `get_optional_user` + ownership checks; (4) frontend
  `getCurrentThesis` via `apiFetch`; (5) contracts regen; (6) isolation suite; (7) docs (`API_CONTRACTS`,
  `ARCHITECTURE`, `HANDOFF`).
- **Sign-off note:** B3 complete — every §4 path scoped (or exempted with reason); §6 negative-test matrix
  green; anonymous + accounts-off demo unchanged; contracts regenerated (auth header), F1 green; S3 proof
  untouched. `pnpm health` green.
- **After promotion:** B3 unblocks **B2** (per-analyst skill-vs-luck) and **B4** (decision/audit ledger).

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
```
