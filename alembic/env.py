"""
alembic/env.py
Alembic migration environment.
Connects Alembic to your SQLAlchemy models and PostgreSQL database.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import your settings and all models ──────────────────────
# IMPORTANT: Import ALL models here so Alembic can detect them
from src.core.config import settings
from src.core.database import Base

# Import every model so Alembic sees them in Base.metadata
from src.models.user import User          # noqa: F401
# Add more models here as you create them:
# from src.models.hotel import Hotel      # noqa: F401
# from src.models.booking import Booking  # noqa: F401
# from src.models.temple import Temple    # noqa: F401
# from src.models.vehicle import Vehicle  # noqa: F401
# from src.models.partner import Partner  # noqa: F401
# from src.models.wallet import Wallet    # noqa: F401

# ── Alembic Config ────────────────────────────────────────────
config = context.config

# Set the database URL from your .env (overrides alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to compare against (your models)
target_metadata = Base.metadata


# ═══════════════════════════════════════════════════════════════
# OFFLINE MODE — generates SQL without connecting to DB
# Run with: alembic upgrade head --sql
# ═══════════════════════════════════════════════════════════════
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,           # detect column type changes
        compare_server_default=True, # detect default value changes
    )
    with context.begin_transaction():
        context.run_migrations()


# ═══════════════════════════════════════════════════════════════
# ONLINE MODE — connects to DB and runs migrations
# Run with: alembic upgrade head
# ═══════════════════════════════════════════════════════════════
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry Point ───────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
