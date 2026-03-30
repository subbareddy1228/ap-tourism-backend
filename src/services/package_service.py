from select import select

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.schemas.package import PackageCreate, PackageUpdate, PackageResponse
from src.models.package import Package, PackageType
from src.repositories import package_repo as repo

from src.core.exceptions import (
    BadRequestException,
    NotFoundException,
)

# Budget range constants
BUDGET_MIN   = 5000
BUDGET_MAX   = 15000
STANDARD_MIN = 15000
STANDARD_MAX = 40000
PREMIUM_MIN  = 40000

# ─────────────────────────────────────────
# TEMPORARY HELPERS
# Will be replaced by src/common/responses.py
# and src/common/pagination.py once LEV148 fills them
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

async def set_cache(key: str, value):
    _cache[key] = value

async def clear_cache(key: str):
    _cache.pop(key, None)

# ---------------------------------------------------
# CREATE PACKAGE (ADMIN)
# ---------------------------------------------------
async def create_new_package(db: AsyncSession, data: PackageCreate):

    if await repo.slug_exists(db, slug=data.slug):
        raise BadRequestException(f"Slug '{data.slug}' is already taken")

    db_package = Package(
        name=data.name,
        slug=data.slug,
        destination_id=data.destination_id,
        duration_days=data.duration_days,
        duration_nights=data.duration_nights,
        type=data.type,
        price=data.price,
        group_size=data.group_size,
        itinerary=[i.model_dump() for i in data.itinerary] if data.itinerary else [],
        inclusions=data.inclusions,
        exclusions=data.exclusions,
        pricing_rules=[p.model_dump() for p in data.pricing_rules] if data.pricing_rules else [],
        departure_dates=data.departure_dates,
        images=[i.model_dump() for i in data.images] if data.images else [],
        is_featured=data.is_featured,
        is_active=data.is_active,
    )

    result = await repo.create_package(db, db_package)

    await clear_cache("packages:featured")
    await clear_cache("packages:popular")

    return await success_response(
        PackageResponse.model_validate(result),
        "Package created successfully"
    )

# ---------------------------------------------------
# GET ALL PACKAGES
# ---------------------------------------------------
async def get_all_packages(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    type: Optional[PackageType] = None,
    destination_id: Optional[str] = None,
    duration_days: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    skip = (page - 1) * limit
    items = await repo.get_packages(
        db, skip=skip, limit=limit,
        type=type, destination_id=destination_id,
        duration_days=duration_days,
        min_price=min_price, max_price=max_price,
    )
    total = await repo.get_packages_count(
        db, type=type, destination_id=destination_id,
        duration_days=duration_days,
        min_price=min_price, max_price=max_price,
    )

    data = await paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return await success_response(data)

# ---------------------------------------------------
# GET FEATURED PACKAGES
# ---------------------------------------------------
async def get_featured_packages_list(db: AsyncSession):

    cache_key = "packages:featured"
    cached = await get_cache(cache_key)

    if cached:
        return await success_response(cached, "Featured packages (cached)")

    items = await repo.get_featured_packages(db)
    data = [PackageResponse.model_validate(i) for i in items]

    await set_cache(cache_key, data)

    return await success_response(data, "Featured packages")

# ---------------------------------------------------
# GET POPULAR PACKAGES
# ---------------------------------------------------
async def get_popular_packages_list(db: AsyncSession):

    cache_key = "packages:popular"
    cached = await get_cache(cache_key)

    if cached:
        return await success_response(cached, "Popular packages (cached)")

    items = await repo.get_popular_packages(db)
    data = [PackageResponse.model_validate(i) for i in items]

    await set_cache(cache_key, data)

    return await success_response(data, "Popular packages")

# ---------------------------------------------------
# GET PACKAGES BY DURATION
# ---------------------------------------------------
async def get_packages_duration(
    db: AsyncSession,
    days: int,
    page: int = 1,
    limit: int = 10,
):
    skip = (page - 1) * limit
    items = await repo.get_packages_by_duration(db, days=days, skip=skip, limit=limit)
    total = await repo.get_packages_by_duration_count(db, days=days)

    data = await paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return await success_response(data)

# ---------------------------------------------------
# GET PACKAGES BY BUDGET RANGE
# ---------------------------------------------------
async def get_packages_budget(
    db: AsyncSession,
    budget_range: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 10,
):
    if min_price is None and max_price is None:
        if budget_range == "budget":
            min_price, max_price = BUDGET_MIN, BUDGET_MAX
        elif budget_range == "standard":
            min_price, max_price = STANDARD_MIN, STANDARD_MAX
        elif budget_range == "premium":
            min_price, max_price = PREMIUM_MIN, None
        else:
            raise BadRequestException("Invalid budget range. Use: budget | standard | premium")

    skip = (page - 1) * limit
    items = await repo.get_packages_by_budget(
        db, min_price=min_price, max_price=max_price, skip=skip, limit=limit
    )
    total = await repo.get_packages_by_budget_count(
        db, min_price=min_price, max_price=max_price
    )

    data = await paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return await success_response(data)

# ---------------------------------------------------
# GET PACKAGE DETAILS
# ---------------------------------------------------
async def get_package_details(db: AsyncSession, value: str):

    package = await repo.get_package_by_id_or_slug(db, value)

    if not package:
        raise NotFoundException(f"Package '{value}' not found")

    return await success_response(PackageResponse.model_validate(package), "Package detail")

# ---------------------------------------------------
# GET PACKAGE IMAGES
# ---------------------------------------------------
async def get_package_images_list(db: AsyncSession, package_id: str):

    images = await repo.get_package_images(db, package_id)

    if images is None:
        raise NotFoundException(f"Package '{package_id}' not found")

    return await success_response(images, "Package images")

# ---------------------------------------------------
# GET PACKAGE REVIEWS
# ---------------------------------------------------
async def get_package_reviews_list(
    db: AsyncSession,
    package_id: str,
    page: int = 1,
    limit: int = 10,
):
    package = await repo.get_package_by_id(db, package_id)
    if not package:
        raise NotFoundException(f"Package '{package_id}' not found")

    skip = (page - 1) * limit
    items = await repo.get_package_reviews(db, package_id=package_id, skip=skip, limit=limit)
    total = await repo.get_package_reviews_count(db, package_id=package_id)

    data = await paginate(items=items, total=total, page=page, limit=limit)

    return await success_response(data, "Package reviews")

# ---------------------------------------------------
# UPDATE PACKAGE (ADMIN)
# ---------------------------------------------------
async def update_existing_package(
    db: AsyncSession,
    package_id: str,
    package_update: PackageUpdate,
):
    package = await repo.get_package_by_id(db, package_id)
    if not package:
        raise NotFoundException(f"Package '{package_id}' not found")

    if package_update.slug and package_update.slug != package.slug:
        if await repo.slug_exists(db, slug=package_update.slug, exclude_id=package_id):
            raise BadRequestException(f"Slug '{package_update.slug}' is already taken")

    update_data = package_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(package, key, value)

    result = await repo.update_package(db, package)

    await clear_cache("packages:featured")
    await clear_cache("packages:popular")

    return await success_response(
        PackageResponse.model_validate(result),
        "Package updated successfully"
    )

async def calculate_price(data: dict, db: AsyncSession) -> dict:
    package_id = data.get("package_id")
    group_size = data.get("group_size", 1)
    travel_date = data.get("travel_date")
 
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise NotFoundException("Package not found")
 
    base_price = float(package.base_price) * group_size
 
    # Basic surge pricing — weekends +10%, peak months (Oct-Jan) +20%
    surge_multiplier = 1.0
    if travel_date:
        from datetime import date
        td = date.fromisoformat(travel_date)
        if td.weekday() >= 5:
            surge_multiplier += 0.10
        if td.month in [10, 11, 12, 1]:
            surge_multiplier += 0.20
 
    final_price = round(base_price * surge_multiplier, 2)
 
    return {
        "package_id": package_id,
        "group_size": group_size,
        "base_price": base_price,
        "surge_multiplier": surge_multiplier,
        "final_price": final_price,
        "currency": "INR"
    }
 
 
async def customize_package(data: dict, current_user, db: AsyncSession) -> dict:
    destination_ids = data.get("destination_ids", [])
    hotel_id = data.get("hotel_id")
    vehicle_id = data.get("vehicle_id")
    guide_id = data.get("guide_id")
    num_days = data.get("num_days", 1)
    group_size = data.get("group_size", 1)
 
    # Basic price estimate — DS engine integration in PEND-015
    estimated_price = num_days * group_size * 2500
 
    return {
        "destination_ids": destination_ids,
        "hotel_id": hotel_id,
        "vehicle_id": vehicle_id,
        "guide_id": guide_id,
        "num_days": num_days,
        "group_size": group_size,
        "estimated_price": estimated_price,
        "currency": "INR",
        "note": "This is an estimate. Final price confirmed at booking."
    }
 
 
async def get_itinerary(package_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise NotFoundException("Package not found")
 
    itinerary = package.itinerary if hasattr(package, "itinerary") and package.itinerary else []
 
    return {
        "package_id": package_id,
        "package_name": package.name,
        "num_days": package.duration_days,
        "itinerary": itinerary
    }
 
 
async def delete_package(package_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise NotFoundException("Package not found")
    package.is_active = False
    await db.commit()
    return {"message": "Package deleted successfully"}