import asyncio
import os
import pytest
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

TIMESCALE_IMAGE = "timescale/timescaledb:latest-pg16"


@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer(image=TIMESCALE_IMAGE, username="ngti", password="ngti", dbname="ngti") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg").replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def migrated_url(postgres_url):
    alembic_cfg = Config("apps/api/alembic.ini")
    os.environ["DATABASE_URL"] = postgres_url
    command.upgrade(alembic_cfg, "head")
    return postgres_url


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
