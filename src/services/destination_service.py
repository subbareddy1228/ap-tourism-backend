import datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.models.destination import Destination, DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate, DestinationListResponse, DestinationResponse
from src.repositories import destination_repo as repo

from src.core.exceptions import (
    BadRequestException,
    NotFoundException,
)

# ─────────────────────────────────────────
# TEMPORARY HELPERS
# Will be replaced by src/common/responses.py
# and src/common/pagination.py
# ─────────────────────────────────────────

async def success_response(data, message: str = "Success"):
    return {"success": True, "data": data, "message": message}

async def error_response(error: str, code: int = 400):
    return {"success": False, "error": error, "code": code}

async def paginate(items, total: int, page: int, limit: int):
    pages = (total + limit - 1) // limit
    return {
        "data": items,
        "total": total,
        "page": page,
        "pages": pages,
    }

# ─────────────────────────────────────────
# In-memory cache (temporary until redis.py is ready)
# ─────────────────────────────────────────

_cache = {}

async def get_cache(key: str):
    return _cache.get(key)

async def set_cache(key: str, value, ttl: int = 300):
    _cache[key] = value

async def clear_cache(key: str):
    _cache.pop(key, None)

# ---------------------------------------
# CREATE DESTINATION (Admin)
# ---------------------------------------
async def create_destination(db: AsyncSession, data: DestinationCreate):

    if await repo.slug_exists(db, slug=data.slug):
        raise BadRequestException(f"Slug '{data.slug}' is already taken")

    db_destination = Destination(
        name=data.name,
        slug=data.slug,
        district=data.district,
        type=data.type,
        tagline=data.tagline,
        description=data.description,
        best_season=data.best_season,
        temperature_range=data.temperature_range,
        how_to_reach=data.how_to_reach.model_dump() if data.how_to_reach else None,
        attractions=[a.model_dump() for a in data.attractions] if data.attractions else [],
        nearby_temples=[t.model_dump() for t in data.nearby_temples] if data.nearby_temples else [],
        images=[i.model_dump() for i in data.images] if data.images else [],
        is_featured=data.is_featured,
        is_active=data.is_active,
    )

    result = await repo.create(db, db_destination)

    await clear_cache("destinations:featured")
    await clear_cache("destinations:popular")

    return await success_response(
        DestinationListResponse.model_validate(result),
        "Destination created successfully"
    )

# ---------------------------------------
# GET ALL DESTINATIONS
# ---------------------------------------
async def get_destinations(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
):
    skip = (page - 1) * limit
    items = await repo.get_all(db, skip=skip, limit=limit, type=type, district=district)
    total = await repo.get_count(db, type=type, district=district)

    data = await paginate(
        items=[DestinationListResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return await success_response(data)

# ---------------------------------------
# GET FEATURED DESTINATIONS
# ---------------------------------------
async def get_featured_destinations(db: AsyncSession):

    cache_key = "destinations:featured"
    cached = await get_cache(cache_key)

    if cached:
        return await success_response(cached, "Featured destinations (cached)")

    items = await repo.get_featured(db)
    data = [DestinationListResponse.model_validate(i) for i in items]

    await set_cache(cache_key, data)

    return await success_response(data, "Featured destinations")

# ---------------------------------------
# GET POPULAR DESTINATIONS
# ---------------------------------------
async def get_popular_destinations(db: AsyncSession):

    cache_key = "destinations:popular"
    cached = await get_cache(cache_key)

    if cached:
        return await success_response(cached, "Popular destinations (cached)")

    items = await repo.get_popular(db)
    data = [DestinationListResponse.model_validate(i) for i in items]

    await set_cache(cache_key, data)

    return await success_response(data, "Popular destinations")

# ---------------------------------------
# GET DESTINATION TYPES
# ---------------------------------------
async def get_destination_types():
    data = await repo.get_types()
    return await success_response(data, "Destination types")

# ---------------------------------------
# GET DESTINATION BY ID OR SLUG
# ---------------------------------------
async def get_destination(db: AsyncSession, value: str):

    destination = await repo.get_by_id_or_slug(db, value)

    if not destination:
        raise NotFoundException(f"Destination '{value}' not found")

    return await success_response(
        DestinationResponse.model_validate(destination),
        "Destination detail"
        )

# ---------------------------------------
# UPDATE DESTINATION (Admin)
# ---------------------------------------
async def update_destination(
    db: AsyncSession,
    destination_id: str,
    data: DestinationUpdate,
):
    destination = await repo.get_by_id(db, destination_id)
    if not destination:
        raise NotFoundException(f"Destination '{destination_id}' not found")

    if data.slug and data.slug != destination.slug:
        if await repo.slug_exists(db, slug=data.slug, exclude_id=destination_id):
            raise BadRequestException(f"Slug '{data.slug}' is already taken")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(destination, key, value)

    result = await repo.update(db, destination)

    await clear_cache("destinations:featured")
    await clear_cache("destinations:popular")

    return await success_response(
        DestinationResponse.model_validate(result),
        "Destination updated successfully"
    )

async def get_destination_packages(destination_id: str, page: int, limit: int, db: AsyncSession):
    from src.models.package import Package
    offset = (page - 1) * limit
    result = await db.execute(
        select(Package).where(Package.destination_id == destination_id)
        .offset(offset).limit(limit)
    )
    packages = result.scalars().all()
    return {"packages": [{"id": str(p.id), "name": p.name, "price": str(p.base_price)} for p in packages], "page": page, "limit": limit}
 
 
async def get_destination_hotels(destination_id: str, page: int, limit: int, db: AsyncSession):
    from src.models.hotel import Hotel
    offset = (page - 1) * limit
    result = await db.execute(
        select(Hotel).where(Hotel.destination_id == destination_id)
        .offset(offset).limit(limit)
    )
    hotels = result.scalars().all()
    return {"hotels": [{"id": str(h.id), "name": h.name, "star_rating": h.star_rating} for h in hotels], "page": page, "limit": limit}
 
 
async def get_destination_guides(destination_id: str, page: int, limit: int, db: AsyncSession):
    from src.models.guide import Guide
    offset = (page - 1) * limit
    result = await db.execute(
        select(Guide).where(Guide.destination_id == destination_id)
        .offset(offset).limit(limit)
    )
    guides = result.scalars().all()
    return {"guides": [{"id": str(g.id), "name": g.name, "rating": str(g.rating)} for g in guides], "page": page, "limit": limit}
 
 
async def get_destination_temples(destination_id: str, page: int, limit: int, db: AsyncSession):
    from src.models.temple import Temple
    offset = (page - 1) * limit
    result = await db.execute(
        select(Temple).where(Temple.destination_id == destination_id)
        .offset(offset).limit(limit)
    )
    temples = result.scalars().all()
    return {"temples": [{"id": str(t.id), "name": t.name, "deity": t.deity} for t in temples], "page": page, "limit": limit}
 
 
async def delete_destination(destination_id: str, db: AsyncSession):
    from src.models.destination import Destination
    result = await db.execute(
        select(Destination).where(Destination.id == destination_id)
    )
    destination = result.scalar_one_or_none()
    if not destination:
        raise NotFoundException("Destination not found")
    destination.is_active = False
    destination.updated_at = datetime.datetime.utcnow()
    await db.commit()
    return {"message": "Destination deleted successfully"}