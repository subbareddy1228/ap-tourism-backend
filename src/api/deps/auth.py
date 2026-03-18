from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.api.deps.database import get_db
from fastapi import Depends


async def require_partner(db: AsyncSession = Depends(get_db)) -> str:
    """Auth disabled for testing — returns dummy partner ID"""
    return "00000000-0000-0000-0000-000000000000"
  