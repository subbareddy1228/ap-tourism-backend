"""Database session dependency."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
