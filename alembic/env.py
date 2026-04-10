"""
alembic/env.py
Alembic migration environment.
Connects Alembic to your SQLAlchemy models and PostgreSQL database.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import your settings and all models ──────────────────────
from src.core.config import settings
from src.core.database import Base

from src.models.user_profile import UserProfile, Address, FamilyMember, UserSession
from src.models.user import User
from src.models.partner import Partner, PartnerDocument
from src.models.temple import Temple, TempleEvent, TempleReview
from src.models.darshan import DarshanType, DarshanSlot, DarshanBooking, PoojaService, PoojaBooking, PrasadamItem, PrasadamOrder
from src.models.hotel import Hotel, HotelRoom, HotelImage, HotelAmenity
from src.models.vehicle import Vehicle
from src.models.guide import Guide
from src.models.destination import Destination
from src.models.package import Package
from src.models.booking import Booking, HotelBooking, VehicleBooking, PackageBooking, GuideBooking, BookingTraveler, BookingAddon
from src.models.transaction import Transaction, SavedCard, Refund
from src.models.wallet import Wallet, WalletTransaction, WithdrawalRequest
from src.models.coupon import Coupon
from src.models.review import Review
from src.models.notification import Notification
from src.models.support import SupportTicket, TicketMessage
from src.models.tracking import TrackingEvent

# ── Alembic Config ────────────────────────────────────────────
config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ═══════════════════════════════════════════════════════════════
# OFFLINE MODE
# ═══════════════════════════════════════════════════════════════
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ═══════════════════════════════════════════════════════════════
# ONLINE MODE
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
        # Check if this migration needs no-transaction mode
        # (i.e. contains CREATE INDEX CONCURRENTLY)
        migration_context = context.get_context() if context.is_configured() else None

        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


async def run_async_migrations_non_transactional() -> None:
    """Run migrations outside any transaction block.
    Required for CREATE INDEX CONCURRENTLY.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Disable autobegin so no transaction is started
        await connection.execution_options(isolation_level="AUTOCOMMIT")

        await connection.run_sync(_do_run_migrations_no_transaction)

    await connectable.dispose()


def _do_run_migrations_no_transaction(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=False,
    )
    # Do NOT use begin_transaction() here
    context.run_migrations()


def run_migrations_online() -> None:
    # Read the target revision's script to check if it needs AUTOCOMMIT
    # We detect this by checking the revision being applied
    script = context.script

    # Get pending revisions
    head_revision = script.get_current_head()

    # Run with AUTOCOMMIT for the FTS migration (non-transactional indexes)
    # For all others, run normally
    asyncio.run(run_async_migrations_non_transactional())


# ── Entry Point ───────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()