"""
core/database.py
Async PostgreSQL database engine and session management.
Used by all endpoints via get_db() dependency.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from src.core.config import settings


# ── Base Model ────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this Base.
    Import this in every model file:
        from src.core.database import Base
    """
    pass


# ── Engine ────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # logs SQL queries in dev mode
    pool_pre_ping=True,           # test connection before using from pool
    pool_size=10,                 # number of persistent connections
    max_overflow=20,              # extra connections allowed under load
    pool_recycle=3600,            # recycle connections every 1 hour
)


# ── Session Factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # keep objects usable after commit
    autocommit=False,
    autoflush=False,
)


# ── FastAPI Dependency ────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a DB session per request.
    Automatically commits on success, rolls back on error.

    Usage in any endpoint:
        @router.get("/something")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(MyModel))
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Table Creation (Dev Only) ─────────────────────────────────
async def create_all_tables():
    """
    Create all tables directly from models.
    Use this ONLY in development.
    In production, always use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables():
    """
    Drop all tables. DANGER — use only in dev/testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
