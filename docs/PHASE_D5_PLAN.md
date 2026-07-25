# Phase D5 Plan — Weather-Forecast Archival (start the validation clock)

**Objective (MASTER_PLAN §4 D5):** weather *forecasts* cannot be backtested
without an archive of what was forecast *at the time* — no vintage archive,
no validation, ever. D5 persists a daily vintage of whatever the platform's
weather adapter serves, so that in ~2 seasons a degree-day feature
(`MASTER_PLAN` C3b's preferred candidate) can be validated honestly. This is
an ACTIVATE/collection phase — **no predictive claim is made or possible
yet**; the ledger entry is explicitly `collecting — unvalidatable yet`.

**Status:** built + shipped 2026-07-25 on `feat/phase-d5-weather-archive`.

## Verified facts ([V])

- `WeatherDataAdapter` protocol: `get_forecast(region)` → per-day dicts
  (region, horizon_days, temps, `anomaly_f`) for the 6 regions in
  `adapters/weather/regions.py`; `get_national_hdd_anomaly()` → float
  (population-weighted). Real `NWSAdapter` implements both (prod runs
  `ADAPTER_WEATHER=nws`); mock serves generator output.
- Migration head: `011_decision_ledger`.
- The 31d feature-refresh scheduler (`FEATURE_REFRESH_ENABLED=true` in prod)
  already ticks every 6h — the archival leg rides it (one vintage/day).

## Design

- **Table `weather_forecast_vintages`** (migration `012_weather_vintages`):
  `vintage_date` + `region` UNIQUE, `forecast` JSONB (the adapter's daily
  list, verbatim — schema-flexible on purpose: we archive what was served),
  `national_hdd_anomaly` (on the `US` aggregate row), `source` (the
  configured adapter name — **mock vintages are labeled and excludable**;
  a mixed archive must never silently pass as real), `fetched_at`.
- **Vintages are immutable history:** the repo is **insert-only with
  `ON CONFLICT DO NOTHING`** — a past vintage is never updated (updating an
  archive of "what we believed then" would be falsification). Re-ticks on
  the same day are no-ops by the UNIQUE key.
- **Archival leg in `feature_refresh.refresh_tick`:** once per tick, insert
  today's vintage (6 regions + the `US` anomaly row) via the registry's
  configured adapter. Failures log and continue (never kill the COT/EIA
  legs). Not a new scheduler — no new knobs.
- Plain table, not a hypertable (7 rows/day).

## Gates

`pnpm health` green · migration runs in the gated `tests/db` job
(`test_migrations_run`) · new `tests/db` lock: same-day re-insert is a
no-op (vintage immutability semantics), next-day insert appends · S3
untouched (no model/resolution path) · S4: `MODEL_DILIGENCE.md` row
`collecting — unvalidatable yet` · S7: `SCHEMA.md` + this plan in-commit ·
S8 two-lane promotion. **Validation re-entry trigger:** ≥ ~180 daily real
(`nws`) vintages spanning a winter → design the degree-day feature probe
with pre-registered gates (a separate plan; the archive makes it possible,
nothing more).
