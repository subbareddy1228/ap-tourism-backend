import re
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.destination import Destination, DestinationType


# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────

async def _is_uuid(value: str) -> bool:
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, value.lower()))


# ─────────────────────────────────────────
# READ
# ─────────────────────────────────────────

async def get_all(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
) -> List[Destination]:

    query = select(Destination).where(Destination.is_active == True)

    if type:
        query = query.where(Destination.type == type)
    if district:
        query = query.where(Destination.district.ilike(f"%{district}%"))

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_count(
    db: AsyncSession,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
) -> int:

    query = select(func.count()).select_from(Destination).where(Destination.is_active == True)

    if type:
        query = query.where(Destination.type == type)
    if district:
        query = query.where(Destination.district.ilike(f"%{district}%"))

    result = await db.execute(query)
    return result.scalar()


async def get_by_id(db: AsyncSession, destination_id: str) -> Optional[Destination]:

    result = await db.execute(
        select(Destination).where(
            Destination.id == destination_id,
            Destination.is_active == True
        )
    )
    return result.scalars().first()


async def get_by_slug(db: AsyncSession, slug: str) -> Optional[Destination]:

    result = await db.execute(
        select(Destination).where(
            Destination.slug == slug,
            Destination.is_active == True
        )
    )
    return result.scalars().first()


async def get_by_id_or_slug(db: AsyncSession, value: str) -> Optional[Destination]:

    if await _is_uuid(value):
        return await get_by_id(db, value)
    return await get_by_slug(db, value)


async def get_featured(db: AsyncSession) -> List[Destination]:

    result = await db.execute(
        select(Destination).where(
            Destination.is_featured == True,
            Destination.is_active == True
        )
    )
    return result.scalars().all()


async def get_popular(db: AsyncSession) -> List[Destination]:

    result = await db.execute(
        select(Destination).where(
            Destination.is_active == True
        ).order_by(
            Destination.reviews_count.desc(),
            Destination.rating.desc()
        ).limit(9)
    )
    return result.scalars().all()


async def get_types() -> List[str]:
    return [e.value for e in DestinationType]


async def slug_exists(
    db: AsyncSession,
    slug: str,
    exclude_id: Optional[str] = None
) -> bool:

    query = select(Destination).where(Destination.slug == slug)
    if exclude_id:
        query = query.where(Destination.id != exclude_id)

    result = await db.execute(query)
    return result.scalars().first() is not None


# ─────────────────────────────────────────
# WRITE
# ─────────────────────────────────────────

async def create(db: AsyncSession, destination: Destination) -> Destination:

    db.add(destination)
    await db.commit()
    await db.refresh(destination)

    return destination


async def update(db: AsyncSession, destination: Destination) -> Destination:

    await db.commit()
    await db.refresh(destination)

    return destination