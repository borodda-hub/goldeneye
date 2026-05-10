import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from apps.api.db.base import Base
import apps.api.models.orm.instruments  # noqa: F401
import apps.api.models.orm.contracts  # noqa: F401
import apps.api.models.orm.eia  # noqa: F401
import apps.api.models.orm.cot  # noqa: F401
import apps.api.models.orm.news  # noqa: F401
import apps.api.models.orm.forecasts  # noqa: F401
import apps.api.models.orm.scenarios  # noqa: F401
import apps.api.models.orm.journal  # noqa: F401
import apps.api.models.orm.paper  # noqa: F401
import apps.api.models.orm.alerts  # noqa: F401
import apps.api.models.orm.adapter_runs  # noqa: F401
import apps.api.models.orm.weather  # noqa: F401
import apps.api.models.orm.prices  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://ngti:ngti@localhost:5432/ngti"
)


def run_migrations_offline() -> None:
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = DATABASE_URL
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
