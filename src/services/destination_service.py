from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from src.models.destination import Destination, DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate, DestinationListResponse
from src.repositories import destination_repo as repo


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
# src/services/destination_service.py

import aioredis

redis = None  # initialize as None at module level

async def get_redis():
    global redis
    if redis is None:
        redis = await aioredis.from_url("redis://localhost")
    return redis

async def get_cache(key: str):
    r = await get_redis()
    return await r.get(key)

async def set_cache(key: str, value, ttl: int = 300):
    r = await get_redis()
    await r.set(key, value, ex=ttl)

async def clear_cache(key: str):
    r = await get_redis()
    await r.delete(key)

# ---------------------------------------
# CREATE DESTINATION (Admin)
# ---------------------------------------
async def create_destination(db: Session, data: DestinationCreate):

    if await repo.slug_exists(db, slug=data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{data.slug}' is already taken"
        )

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

    # clear list cache when new destination added
    clear_cache("destinations:featured")
    clear_cache("destinations:popular")

    return success_response(
        DestinationListResponse.model_validate(result),
        "Destination created successfully"
    )


# ---------------------------------------
# GET ALL DESTINATIONS
# page based pagination
# ---------------------------------------
async def get_destinations(
    db: Session,
    page: int = 1,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
):
    skip = (page - 1) * limit
    items = await repo.get_all(db, skip=skip, limit=limit, type=type, district=district)
    total = await repo.get_count(db, type=type, district=district)

    data = paginate(
        items=[DestinationListResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return success_response(data)


# ---------------------------------------
# GET FEATURED DESTINATIONS
# Cached in memory (1 hour = 3600 seconds)
# Will use Redis once LEV148 fills redis.py
# ---------------------------------------
async def get_featured_destinations(db: Session):

    cache_key = "destinations:featured"
    cached = get_cache(cache_key)

    if cached:
        return success_response(cached, "Featured destinations (cached)")

    items = await repo.get_featured(db)
    data = [DestinationListResponse.model_validate(i) for i in items]

    set_cache(cache_key, data)

    return success_response(data, "Featured destinations")


# ---------------------------------------
# GET POPULAR DESTINATIONS
# Cached in memory
# ---------------------------------------
async def get_popular_destinations(db: Session):

    cache_key = "destinations:popular"
    cached = get_cache(cache_key)

    if cached:
        return success_response(cached, "Popular destinations (cached)")

    items = await repo.get_popular(db)
    data = [DestinationListResponse.model_validate(i) for i in items]

    set_cache(cache_key, data)

    return success_response(data, "Popular destinations")


# ---------------------------------------
# GET DESTINATION TYPES
# ---------------------------------------
async def get_destination_types():
    data = await repo.get_types()
    return success_response(data, "Destination types")


# ---------------------------------------
# GET DESTINATION BY ID OR SLUG
# Full detail response
# ---------------------------------------
async def get_destination(db: Session, value: str):

    destination = await repo.get_by_id_or_slug(db, value)

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{value}' not found"
        )

    return success_response(destination, "Destination detail")


# ---------------------------------------
# UPDATE DESTINATION (Admin)
# ---------------------------------------
async def update_destination(
    db: Session,
    destination_id: str,
    data: DestinationUpdate,
):
    destination = await repo.get_by_id(db, destination_id)
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{destination_id}' not found"
        )

    if data.slug and data.slug != destination.slug:
        if await repo.slug_exists(db, slug=data.slug, exclude_id=destination_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{data.slug}' is already taken"
            )

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(destination, key, value)

    result = await repo.update(db, destination)

    # clear cache after update
    clear_cache("destinations:featured")
    clear_cache("destinations:popular")

    return success_response(
        DestinationListResponse.model_validate(result),
        "Destination updated successfully"
    )