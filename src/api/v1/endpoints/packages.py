from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.database import get_db
from src.models.package import PackageType
from src.schemas.package import PackageCreate, PackageUpdate
from src.services.package_service import (
    get_all_packages,
    get_featured_packages_list,
    get_popular_packages_list,
    get_packages_duration,
    get_packages_budget,
    get_package_images_list,
    get_package_reviews_list,
    get_package_details,
    create_new_package,
    update_existing_package,
)

router = APIRouter(prefix="/packages", tags=["Packages"])


# ---------------------------------------
# GET ALL PACKAGES
# GET /api/v1/packages/
# ---------------------------------------
@router.get("/")
async def list_packages(
    type: Optional[PackageType] = Query(None, description="PILGRIMAGE | LEISURE | ADVENTURE"),
    destination_id: Optional[str] = Query(None, description="Filter by destination UUID"),
    duration_days: Optional[int] = Query(None, description="Filter by number of days"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    return await get_all_packages(
        db,
        page=page,
        limit=limit,
        type=type,
        destination_id=destination_id,
        duration_days=duration_days,
        min_price=min_price,
        max_price=max_price,
    )


# ---------------------------------------
# GET FEATURED PACKAGES
# GET /api/v1/packages/featured
# ---------------------------------------
@router.get("/featured")
async def list_featured_packages(db: AsyncSession = Depends(get_db)):
    return await get_featured_packages_list(db)


# ---------------------------------------
# GET POPULAR PACKAGES
# GET /api/v1/packages/popular
# ---------------------------------------
@router.get("/popular")
async def list_popular_packages(db: AsyncSession = Depends(get_db)):
    return await get_popular_packages_list(db)


# ---------------------------------------
# GET PACKAGES BY DURATION
# GET /api/v1/packages/by-duration/{days}
# ---------------------------------------
@router.get("/by-duration/{days}")
async def list_packages_by_duration(
    days: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_packages_duration(db, days=days, page=page, limit=limit)


# ---------------------------------------
# GET PACKAGES BY BUDGET
# GET /api/v1/packages/by-budget
# ---------------------------------------
@router.get("/by-budget")
async def list_packages_by_budget(
    range: str = Query(..., description="budget | standard | premium"),
    min: Optional[float] = Query(None, description="Custom min price"),
    max: Optional[float] = Query(None, description="Custom max price"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_packages_budget(
        db,
        budget_range=range,
        min_price=min,
        max_price=max,
        page=page,
        limit=limit,
    )


# ---------------------------------------
# GET PACKAGE IMAGES
# GET /api/v1/packages/{package_id}/images
# NOTE: must be before /{value}
# ---------------------------------------
@router.get("/{package_id}/images")
async def retrieve_package_images(package_id: str, db: AsyncSession = Depends(get_db)):
    return await get_package_images_list(db, package_id)


# ---------------------------------------
# GET PACKAGE REVIEWS
# GET /api/v1/packages/{package_id}/reviews
# NOTE: must be before /{value}
# ---------------------------------------
@router.get("/{package_id}/reviews")
async def retrieve_package_reviews(
    package_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_package_reviews_list(db, package_id=package_id, page=page, limit=limit)


# ---------------------------------------
# GET PACKAGE BY ID OR SLUG
# GET /api/v1/packages/{value}
# NOTE: always last
# ---------------------------------------
@router.get("/{package_id}")
async def retrieve_package(package_id: str, db: AsyncSession = Depends(get_db)):
    return await get_package_details(db, package_id)


# ---------------------------------------
# CREATE PACKAGE (Admin)
# POST /api/v1/packages/
# ---------------------------------------
@router.post("/")
async def create_package(
    data: PackageCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_new_package(db, data)


# ---------------------------------------
# UPDATE PACKAGE (Admin)
# PUT /api/v1/packages/{package_id}
# ---------------------------------------
@router.put("/{package_id}")
async def update_package(
    package_id: str,
    data: PackageUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await update_existing_package(db, package_id, data)