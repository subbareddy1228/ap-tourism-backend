"""
repositories/base.py
Generic async base repository.
All module-specific repos can inherit from this for standard CRUD.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD repository for any SQLAlchemy model.

    Usage:
        class HotelRepository(BaseRepository[Hotel]):
            def __init__(self, db: AsyncSession):
                super().__init__(Hotel, db)
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db    = db

    async def get_by_id(self, record_id: UUID) -> Optional[ModelType]:
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page:  int = 1,
        limit: int = 20,
    ) -> List[ModelType]:
        result = await self.db.execute(
            select(self.model)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.commit()

    async def save(self, obj: ModelType) -> ModelType:
        """Add and commit without refresh — use for bulk ops."""
        self.db.add(obj)
        await self.db.commit()
        return obj