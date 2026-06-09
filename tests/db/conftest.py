import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

TIMESCALE_IMAGE = "timescale/timescaledb:latest-pg16"
# tests/db/conftest.py -> repo root. Resolve alembic paths absolutely so the
# fixture works regardless of pytest's CWD (the ini's script_location is relative).
_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer(image=TIMESCALE_IMAGE, username="ngti", password="ngti", dbname="ngti") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg").replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def migrated_url(postgres_url):
    alembic_cfg = Config(str(_ROOT / "apps" / "api" / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", str(_ROOT / "infra" / "migrations")
    )
    os.environ["DATABASE_URL"] = postgres_url
    command.upgrade(alembic_cfg, "head")
    return postgres_url


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
