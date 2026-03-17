"""Database engine, session factory, and declarative base."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.core.config import settings

# Ensure URL uses asyncpg driver
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+psycopg2://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
