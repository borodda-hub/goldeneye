# docs/SCHEMA.md — NGTI Database Schema

Single source of truth. All migrations in `infra/migrations/` derive from this. Update this file in the same commit as any schema change.

## §extensions

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- news search
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
```

## §enums

```sql
CREATE TYPE direction_t          AS ENUM ('bullish','bearish','neutral');
CREATE TYPE confidence_t         AS ENUM ('low','medium','high');
CREATE TYPE volatility_regime_t  AS ENUM ('compressed','normal','elevated','crisis');
CREATE TYPE bar_resolution_t     AS ENUM ('1m','5m','15m','1h','1d');
CREATE TYPE trade_side_t         AS ENUM ('long','short');
CREATE TYPE trade_status_t       AS ENUM ('open','closed','cancelled');
CREATE TYPE alert_severity_t     AS ENUM ('info','warning','critical');
CREATE TYPE adapter_health_t     AS ENUM ('ok','degraded','down','unknown');
```

## §relational_tables

```sql
-- Tradable instruments (NG, HH, etc.)
CREATE TABLE instruments (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol        TEXT NOT NULL UNIQUE,        -- 'NG' for NYMEX Henry Hub natgas
  name          TEXT NOT NULL,
  exchange      TEXT NOT NULL,
  asset_class   TEXT NOT NULL DEFAULT 'commodity',
  currency      TEXT NOT NULL DEFAULT 'USD',
  unit          TEXT NOT NULL,                -- 'MMBtu'
  contract_size NUMERIC NOT NULL,             -- 10_000 for NG
  tick_size     NUMERIC NOT NULL,             -- 0.001
  metadata      JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Specific futures contracts (front-month, deferred, etc.)
CREATE TABLE contracts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id   UUID NOT NULL REFERENCES instruments(id),
  contract_code   TEXT NOT NULL,             -- 'NGF26' for Jan 2026
  expiry_date     DATE NOT NULL,
  is_front_month  BOOLEAN NOT NULL DEFAULT false,
  metadata        JSONB NOT NULL DEFAULT '{}',
  UNIQUE (instrument_id, contract_code)
);
CREATE INDEX contracts_front_month_idx ON contracts (instrument_id) WHERE is_front_month;

-- EIA weekly natural gas storage reports
CREATE TABLE eia_storage_reports (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_date           DATE NOT NULL UNIQUE,         -- date EIA published
  week_ending           DATE NOT NULL,                -- Friday data refers to
  total_lower_48_bcf    NUMERIC NOT NULL,
  east_bcf              NUMERIC,
  midwest_bcf           NUMERIC,
  mountain_bcf          NUMERIC,
  pacific_bcf           NUMERIC,
  south_central_bcf     NUMERIC,
  net_change_bcf        NUMERIC NOT NULL,
  five_year_avg_bcf     NUMERIC,
  five_year_max_bcf     NUMERIC,
  five_year_min_bcf     NUMERIC,
  consensus_estimate    NUMERIC,                       -- analyst median if available
  surprise_bcf          NUMERIC,                       -- actual - consensus
  source                TEXT NOT NULL DEFAULT 'EIA',
  fetched_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CFTC Commitments of Traders (Disaggregated for natgas)
CREATE TABLE cot_reports (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_date                 DATE NOT NULL,           -- Tuesday data date
  release_date                DATE NOT NULL,           -- Friday published
  contract_market_name        TEXT NOT NULL,           -- 'NATURAL GAS - NEW YORK MERCANTILE EXCHANGE'
  cftc_contract_market_code   TEXT NOT NULL,
  -- Disaggregated categories
  producer_long               BIGINT,
  producer_short              BIGINT,
  swap_long                   BIGINT,
  swap_short                  BIGINT,
  managed_money_long          BIGINT,
  managed_money_short         BIGINT,
  other_reportable_long       BIGINT,
  other_reportable_short      BIGINT,
  nonreportable_long          BIGINT,
  nonreportable_short         BIGINT,
  open_interest_total         BIGINT NOT NULL,
  -- Convenience derived columns (computed on insert)
  managed_money_net           BIGINT GENERATED ALWAYS AS (managed_money_long - managed_money_short) STORED,
  source                      TEXT NOT NULL DEFAULT 'CFTC_PRE',
  fetched_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (report_date, contract_market_name)
);

-- News and event intelligence
CREATE TABLE news_events (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  published_at      TIMESTAMPTZ NOT NULL,
  source            TEXT NOT NULL,
  url               TEXT,
  headline          TEXT NOT NULL,
  body              TEXT,
  -- LLM-extracted
  category          TEXT,                              -- 'production','demand','weather','policy','geopolitical','infrastructure'
  sentiment         NUMERIC,                           -- -1.0 to +1.0
  impact_score      NUMERIC,                           -- 0.0 to 1.0
  affected_regions  TEXT[],
  entities          JSONB NOT NULL DEFAULT '[]',
  raw               JSONB NOT NULL DEFAULT '{}',
  ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX news_events_published_idx ON news_events (published_at DESC);
CREATE INDEX news_events_headline_trgm ON news_events USING gin (headline gin_trgm_ops);

-- Forecast outputs from the model registry
CREATE TABLE model_forecasts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  instrument_id   UUID NOT NULL REFERENCES instruments(id),
  model_name      TEXT NOT NULL,                      -- 'moving_average_directional'
  horizon         TEXT NOT NULL,                      -- '1d','1w','1m'
  direction       direction_t NOT NULL,
  confidence      confidence_t NOT NULL,
  expected_pct    NUMERIC,                            -- expected pct move, optional
  range_low_pct   NUMERIC,
  range_high_pct  NUMERIC,
  vol_regime      volatility_regime_t,
  supporting      JSONB NOT NULL DEFAULT '[]',        -- [{factor, weight, note}]
  contradicting   JSONB NOT NULL DEFAULT '[]',
  features        JSONB NOT NULL DEFAULT '{}',
  inputs_hash     TEXT,
  caveats         TEXT[]
);
CREATE INDEX model_forecasts_instrument_time_idx
  ON model_forecasts (instrument_id, generated_at DESC);

-- Scenario runs
CREATE TABLE scenario_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id       UUID,                                 -- nullable in MVP single-user mode
  instrument_id UUID NOT NULL REFERENCES instruments(id),
  name          TEXT NOT NULL,
  shocks        JSONB NOT NULL,                       -- list of ScenarioShock objects
  result        JSONB NOT NULL,                       -- direction, confidence, narrative, assumptions, counterargs, data_needed
  baseline_ref  UUID REFERENCES model_forecasts(id)
);

-- Decision Journal entries (decision-quality framework)
CREATE TABLE user_decision_journals (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id               UUID,
  instrument_id         UUID NOT NULL REFERENCES instruments(id),
  hypothesis            TEXT NOT NULL,
  evidence              JSONB NOT NULL DEFAULT '[]',  -- [{source, summary, weight}]
  confidence_pct        INT NOT NULL CHECK (confidence_pct BETWEEN 0 AND 100),
  planned_action        TEXT,                          -- e.g. 'paper-long 2 contracts'
  risk_factors          TEXT[],
  invalidation_criteria TEXT,
  outcome               TEXT,                          -- filled later
  reflection            TEXT,                          -- filled later
  llm_review            JSONB                          -- assumption-finding feedback
);

-- Paper trading (simulated only)
CREATE TABLE paper_trades (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  opened_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at       TIMESTAMPTZ,
  user_id         UUID,
  instrument_id   UUID NOT NULL REFERENCES instruments(id),
  contract_id     UUID REFERENCES contracts(id),
  side            trade_side_t NOT NULL,
  size_contracts  NUMERIC NOT NULL,
  entry_price     NUMERIC NOT NULL,
  exit_price      NUMERIC,
  stop_loss       NUMERIC,
  take_profit     NUMERIC,
  status          trade_status_t NOT NULL DEFAULT 'open',
  rationale       TEXT,
  outcome_pnl     NUMERIC,                            -- computed on close
  reflection      TEXT,
  journal_ref     UUID REFERENCES user_decision_journals(id)
);
CREATE INDEX paper_trades_user_status_idx ON paper_trades (user_id, status);

-- Alerts (price thresholds, signal flips, data-health flags)
CREATE TABLE alerts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id       UUID,
  kind          TEXT NOT NULL,                        -- 'price_threshold','signal_flip','data_stale'
  severity      alert_severity_t NOT NULL DEFAULT 'info',
  payload       JSONB NOT NULL,
  read          BOOLEAN NOT NULL DEFAULT false,
  acknowledged  BOOLEAN NOT NULL DEFAULT false
);

-- Adapter health (rolled up by /admin/data-health)
CREATE TABLE adapter_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  adapter_name    TEXT NOT NULL,
  started_at      TIMESTAMPTZ NOT NULL,
  finished_at     TIMESTAMPTZ,
  status          adapter_health_t NOT NULL,
  rows_ingested   INT NOT NULL DEFAULT 0,
  error           TEXT
);
CREATE INDEX adapter_runs_name_time_idx ON adapter_runs (adapter_name, started_at DESC);
```

## §hypertables

All bar/tick/observation tables are TimescaleDB hypertables.

```sql
-- OHLCV bars
CREATE TABLE price_bars (
  ts            TIMESTAMPTZ NOT NULL,
  contract_id   UUID NOT NULL REFERENCES contracts(id),
  resolution    bar_resolution_t NOT NULL,
  open          NUMERIC NOT NULL,
  high          NUMERIC NOT NULL,
  low           NUMERIC NOT NULL,
  close         NUMERIC NOT NULL,
  volume        BIGINT,
  source        TEXT NOT NULL DEFAULT 'mock',
  PRIMARY KEY (contract_id, resolution, ts)
);
SELECT create_hypertable('price_bars', 'ts', chunk_time_interval => INTERVAL '7 days');

-- Optional: tick-level data for future Databento integration
CREATE TABLE tick_data (
  ts            TIMESTAMPTZ NOT NULL,
  contract_id   UUID NOT NULL REFERENCES contracts(id),
  price         NUMERIC NOT NULL,
  size          BIGINT NOT NULL,
  side          TEXT,
  source        TEXT NOT NULL DEFAULT 'mock',
  PRIMARY KEY (contract_id, ts)
);
SELECT create_hypertable('tick_data', 'ts', chunk_time_interval => INTERVAL '1 day');

-- Futures curve snapshots
CREATE TABLE futures_curve_snapshots (
  ts            TIMESTAMPTZ NOT NULL,
  instrument_id UUID NOT NULL REFERENCES instruments(id),
  curve         JSONB NOT NULL,                       -- [{contract_code, expiry, mid_price}, ...]
  PRIMARY KEY (instrument_id, ts)
);
SELECT create_hypertable('futures_curve_snapshots', 'ts', chunk_time_interval => INTERVAL '30 days');

-- Weather observations + forecasts
CREATE TABLE weather_observations (
  ts            TIMESTAMPTZ NOT NULL,
  region        TEXT NOT NULL,                        -- 'midwest','northeast', etc.
  temp_f        NUMERIC,
  hdd           NUMERIC,
  cdd           NUMERIC,
  precip_in     NUMERIC,
  anomaly_f     NUMERIC,                              -- vs 30-yr normal
  source        TEXT NOT NULL DEFAULT 'mock',
  PRIMARY KEY (region, ts)
);
SELECT create_hypertable('weather_observations', 'ts', chunk_time_interval => INTERVAL '30 days');

CREATE TABLE weather_forecasts (
  ts            TIMESTAMPTZ NOT NULL,                 -- forecast valid time
  issued_at     TIMESTAMPTZ NOT NULL,                 -- when the forecast was made
  region        TEXT NOT NULL,
  horizon_days  INT NOT NULL,
  temp_f        NUMERIC,
  hdd           NUMERIC,
  cdd           NUMERIC,
  anomaly_f     NUMERIC,
  source        TEXT NOT NULL DEFAULT 'mock',
  PRIMARY KEY (region, issued_at, ts)
);
SELECT create_hypertable('weather_forecasts', 'issued_at', chunk_time_interval => INTERVAL '7 days');
```

## §retention_compression

Demo defaults; tighten in production.

```sql
SELECT add_retention_policy('tick_data',         INTERVAL '90 days');
SELECT add_retention_policy('weather_forecasts', INTERVAL '180 days');
ALTER TABLE price_bars  SET (timescaledb.compress, timescaledb.compress_segmentby = 'contract_id, resolution');
SELECT add_compression_policy('price_bars', INTERVAL '30 days');
```

## §seeds

The MVP demo seed creates:
- 1 instrument (`NG`)
- 12 contracts (next 12 monthly expiries)
- 730 daily bars on the front month (2 years of history)
- 20,000 1-minute bars covering the last 14 trading days
- 100 weekly EIA storage reports (2 years)
- 100 weekly COT reports (2 years)
- 60 days of weather observations + 14-day forecast for 6 regions
- 50 news events spanning 2 years
- 5 historical scenario runs
- 3 sample journal entries with one closed paper trade

Seed is implemented in `apps/api/seeds/demo.py`. Detailed fixture shapes in `docs/MOCK_DATA_SPEC.md`.

## §contracts

Pydantic models in `apps/api/models/` mirror these tables. The OpenAPI schema generated from those models becomes `packages/contracts/`. Run `pnpm contracts:gen` after any model change. The `/contract-check` slash command runs that and fails the build on drift.

## §migration_rules

- Every change to this file requires a new Alembic revision.
- Squash-style "init" migration is allowed only for Phase 01. After Phase 01, all changes are forward-only.
- Hypertable creation goes in a separate migration step from `CREATE TABLE` (TimescaleDB requirement).
- Generated columns and check constraints documented inline in this file are part of the contract; tests in `tests/db/test_constraints.py` enforce them.
