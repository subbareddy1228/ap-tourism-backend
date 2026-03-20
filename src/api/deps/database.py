from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import SessionLocal

async def get_db():
    async with SessionLocal() as db:
        yield db