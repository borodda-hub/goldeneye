-- Run once on first container boot via docker-entrypoint-initdb.d
-- TimescaleDB extension must be created before Alembic migrations run.
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
