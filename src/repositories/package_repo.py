import re
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.package import Package


# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────

async def _is_uuid(value: str) -> bool:
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, value.lower()))


# ----------------------------------
# CREATE PACKAGE (Admin)
# ----------------------------------
async def create_package(db: AsyncSession, package: Package):

    db.add(package)
    await db.commit()
    await db.refresh(package)

    return package


# ----------------------------------
# GET ALL PACKAGES
# ----------------------------------
async def get_packages(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    type=None,
    destination_id: Optional[str] = None,
    duration_days: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    query = select(Package).where(Package.is_active == True)

    if type:
        query = query.where(Package.type == type)
    if destination_id:
        query = query.where(Package.destination_id == destination_id)
    if duration_days is not None:
        query = query.where(Package.duration_days == duration_days)
    if min_price is not None:
        query = query.where(Package.price >= min_price)
    if max_price is not None:
        query = query.where(Package.price <= max_price)

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_packages_count(
    db: AsyncSession,
    type=None,
    destination_id: Optional[str] = None,
    duration_days: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> int:

    query = select(func.count()).select_from(Package).where(Package.is_active == True)

    if type:
        query = query.where(Package.type == type)
    if destination_id:
        query = query.where(Package.destination_id == destination_id)
    if duration_days is not None:
        query = query.where(Package.duration_days == duration_days)
    if min_price is not None:
        query = query.where(Package.price >= min_price)
    if max_price is not None:
        query = query.where(Package.price <= max_price)

    result = await db.execute(query)
    return result.scalar()


# ----------------------------------
# FEATURED PACKAGES
# ----------------------------------
async def get_featured_packages(db: AsyncSession):

    result = await db.execute(
        select(Package).where(
            Package.is_featured == True,
            Package.is_active == True
        )
    )
    return result.scalars().all()


# ----------------------------------
# POPULAR PACKAGES
# sorted by total_bookings + rating
# ----------------------------------
async def get_popular_packages(db: AsyncSession):

    result = await db.execute(
        select(Package).where(
            Package.is_active == True
        ).order_by(
            Package.total_bookings.desc(),
            Package.rating.desc()
        ).limit(10)
    )
    return result.scalars().all()


# ----------------------------------
# FILTER BY DURATION
# ----------------------------------
async def get_packages_by_duration(
    db: AsyncSession,
    days: int,
    skip: int = 0,
    limit: int = 10,
):
    result = await db.execute(
        select(Package).where(
            Package.duration_days == days,
            Package.is_active == True
        ).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_packages_by_duration_count(db: AsyncSession, days: int) -> int:

    result = await db.execute(
        select(func.count()).select_from(Package).where(
            Package.duration_days == days,
            Package.is_active == True
        )
    )
    return result.scalar()


# ----------------------------------
# FILTER BY BUDGET
# budget   → ₹5k  - ₹15k
# standard → ₹15k - ₹40k
# premium  → ₹40k+ (max_price is None)
# ----------------------------------
async def get_packages_by_budget(
    db: AsyncSession,
    min_price: float,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 10,
):
    query = select(Package).where(
        Package.price >= min_price,
        Package.is_active == True
    )

    if max_price is not None:
        query = query.where(Package.price <= max_price)

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_packages_by_budget_count(
    db: AsyncSession,
    min_price: float,
    max_price: Optional[float] = None,
) -> int:

    query = select(func.count()).select_from(Package).where(
        Package.price >= min_price,
        Package.is_active == True
    )

    if max_price is not None:
        query = query.where(Package.price <= max_price)

    result = await db.execute(query)
    return result.scalar()


# ----------------------------------
# GET PACKAGE BY ID
# ----------------------------------
async def get_package_by_id(db: AsyncSession, package_id: str):

    result = await db.execute(
        select(Package).where(
            Package.id == package_id,
            Package.is_active == True
        )
    )
    return result.scalars().first()


# ----------------------------------
# GET PACKAGE BY SLUG
# ----------------------------------
async def get_package_by_slug(db: AsyncSession, slug: str):

    result = await db.execute(
        select(Package).where(
            Package.slug == slug,
            Package.is_active == True
        )
    )
    return result.scalars().first()


# ----------------------------------
# GET PACKAGE BY ID OR SLUG
# ----------------------------------
async def get_package_by_id_or_slug(db: AsyncSession, value: str):

    if await _is_uuid(value):
        return await get_package_by_id(db, value)
    return await get_package_by_slug(db, value)


# ----------------------------------
# GET PACKAGE IMAGES
# ----------------------------------
async def get_package_images(db: AsyncSession, package_id: str):

    package = await get_package_by_id(db, package_id)
    if not package:
        return None
    return package.images


# ----------------------------------
# GET PACKAGE REVIEWS
# Reviews model handled by review module, so we just return empty list here
# ----------------------------------
async def get_package_reviews(
    db: AsyncSession,
    package_id: str,
    skip: int = 0,
    limit: int = 10,
):
    # from src.models.review import Review
    # result = await db.execute(
    #     select(Review).where(Review.package_id == package_id).offset(skip).limit(limit)
    # )
    # return result.scalars().all()
    return []


async def get_package_reviews_count(db: AsyncSession, package_id: str) -> int:
    # from src.models.review import Review
    # result = await db.execute(
    #     select(func.count()).select_from(Review).where(Review.package_id == package_id)
    # )
    # return result.scalar()
    return 0


# ----------------------------------
# CHECK SLUG EXISTS
# ----------------------------------
async def slug_exists(
    db: AsyncSession,
    slug: str,
    exclude_id: Optional[str] = None,
) -> bool:

    query = select(Package).where(Package.slug == slug)

    if exclude_id:
        query = query.where(Package.id != exclude_id)

    result = await db.execute(query)
    return result.scalars().first() is not None


# ----------------------------------
# UPDATE PACKAGE
# ----------------------------------
async def update_package(db: AsyncSession, package: Package):

    await db.commit()
    await db.refresh(package)

    return package