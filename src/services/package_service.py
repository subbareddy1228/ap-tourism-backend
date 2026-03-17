from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from src.schemas.package import PackageCreate, PackageUpdate, PackageResponse
from src.models.package import Package, PackageType
from src.repositories import package_repo as repo

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
async def create_new_package(db: Session, data: PackageCreate):

    if await repo.slug_exists(db, slug=data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{data.slug}' is already taken"
        )

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

    # clear cache when new package added
    clear_cache("packages:featured")
    clear_cache("packages:popular")

    return success_response(
        PackageResponse.model_validate(result),
        "Package created successfully"
    )


# ---------------------------------------------------
# GET ALL PACKAGES
# Filters: type, destination, duration, min/max price
# ---------------------------------------------------
async def get_all_packages(
    db: Session,
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

    data = paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return success_response(data)


# ---------------------------------------------------
# GET FEATURED PACKAGES
# ---------------------------------------------------
async def get_featured_packages_list(db: Session):

    cache_key = "packages:featured"
    cached = get_cache(cache_key)

    if cached:
        return success_response(cached, "Featured packages (cached)")

    items = await repo.get_featured_packages(db)
    data = [PackageResponse.model_validate(i) for i in items]

    set_cache(cache_key, data)

    return success_response(data, "Featured packages")


# ---------------------------------------------------
# GET POPULAR PACKAGES
# ---------------------------------------------------
async def get_popular_packages_list(db: Session):

    cache_key = "packages:popular"
    cached = get_cache(cache_key)

    if cached:
        return success_response(cached, "Popular packages (cached)")

    items = await repo.get_popular_packages(db)
    data = [PackageResponse.model_validate(i) for i in items]

    set_cache(cache_key, data)

    return success_response(data, "Popular packages")


# ---------------------------------------------------
# GET PACKAGES BY DURATION
# ---------------------------------------------------
async def get_packages_duration(
    db: Session,
    days: int,
    page: int = 1,
    limit: int = 10,
):
    skip = (page - 1) * limit
    items = await repo.get_packages_by_duration(db, days=days, skip=skip, limit=limit)
    total = await repo.get_packages_by_duration_count(db, days=days)

    data = paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return success_response(data)


# ---------------------------------------------------
# GET PACKAGES BY BUDGET RANGE
# range: budget | standard | premium
# ---------------------------------------------------
async def get_packages_budget(
    db: Session,
    budget_range: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 10,
):
    # Use preset ranges only if custom min/max not provided
    if min_price is None and max_price is None:
        if budget_range == "budget":
            min_price, max_price = BUDGET_MIN, BUDGET_MAX
        elif budget_range == "standard":
            min_price, max_price = STANDARD_MIN, STANDARD_MAX
        elif budget_range == "premium":
            min_price, max_price = PREMIUM_MIN, None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid budget range. Use: budget | standard | premium"
            )

    skip = (page - 1) * limit
    items = await repo.get_packages_by_budget(
        db, min_price=min_price, max_price=max_price, skip=skip, limit=limit
    )
    total = await repo.get_packages_by_budget_count(
        db, min_price=min_price, max_price=max_price
    )

    data = paginate(
        items=[PackageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

    return success_response(data)


# ---------------------------------------------------
# GET PACKAGE DETAILS
# ---------------------------------------------------
async def get_package_details(db: Session, value: str):

    package = await repo.get_package_by_id_or_slug(db, value)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{value}' not found"
        )

    return success_response(PackageResponse.model_validate(package), "Package detail")


# ---------------------------------------------------
# GET PACKAGE IMAGES
# ---------------------------------------------------
async def get_package_images_list(db: Session, package_id: str):

    images = await repo.get_package_images(db, package_id)

    if images is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    return success_response(images, "Package images")


# ---------------------------------------------------
# GET PACKAGE REVIEWS
# Reviews handled by colleague LEV152
# ---------------------------------------------------
async def get_package_reviews_list(
    db: Session,
    package_id: str,
    page: int = 1,
    limit: int = 10,
):
    package = await repo.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    skip = (page - 1) * limit
    items = await repo.get_package_reviews(db, package_id=package_id, skip=skip, limit=limit)
    total = await repo.get_package_reviews_count(db, package_id=package_id)

    data = paginate(items=items, total=total, page=page, limit=limit)

    return success_response(data, "Package reviews")


# ---------------------------------------------------
# UPDATE PACKAGE (ADMIN)
# ---------------------------------------------------
async def update_existing_package(
    db: Session,
    package_id: str,
    package_update: PackageUpdate,
):
    package = await repo.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    if package_update.slug and package_update.slug != package.slug:
        if await repo.slug_exists(db, slug=package_update.slug, exclude_id=package_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{package_update.slug}' is already taken"
            )

    update_data = package_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(package, key, value)

    result = await repo.update_package(db, package)

    # clear cache after update
    clear_cache("packages:featured")
    clear_cache("packages:popular")

    return success_response(
        PackageResponse.model_validate(result),
        "Package updated successfully"
    )