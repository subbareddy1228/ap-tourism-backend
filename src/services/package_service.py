from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.schemas.package import PackageCreate, PackageUpdate
from src.models.package import Package
from src.repositories.package_repo import (
    create_package,
    get_packages,
    get_featured_packages,
    get_popular_packages,
    get_packages_by_duration,
    get_packages_by_budget,
    get_package_by_id,
    get_package_by_id_or_slug,
    get_package_images,
    get_package_reviews,
    slug_exists,
    update_package,
)

# Budget range constants
BUDGET_MIN   = 5000
BUDGET_MAX   = 15000
STANDARD_MIN = 15000
STANDARD_MAX = 40000
PREMIUM_MIN  = 40000


# ---------------------------------------------------
# CREATE PACKAGE (ADMIN)
# ---------------------------------------------------
def create_new_package(db: Session, data: PackageCreate):

    # Check slug already taken
    if slug_exists(db, slug=data.slug):
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
        itinerary=data.itinerary,
        inclusions=data.inclusions,
        exclusions=data.exclusions,
        pricing_rules=data.pricing_rules,
        departure_dates=data.departure_dates,
        images=data.images,
        is_featured=data.is_featured,
        is_active=data.is_active,
    )

    return create_package(db, db_package)


# ---------------------------------------------------
# GET ALL PACKAGES
# ---------------------------------------------------
def get_all_packages(db: Session, skip: int = 0, limit: int = 10):

    return get_packages(db, skip=skip, limit=limit)


# ---------------------------------------------------
# GET FEATURED PACKAGES
# ---------------------------------------------------
def get_featured_packages_list(db: Session):

    return get_featured_packages(db)


# ---------------------------------------------------
# GET POPULAR PACKAGES
# ---------------------------------------------------
def get_popular_packages_list(db: Session):

    return get_popular_packages(db)


# ---------------------------------------------------
# GET PACKAGES BY DURATION
# ---------------------------------------------------
def get_packages_duration(
    db: Session,
    days: int,
    skip: int = 0,
    limit: int = 10,
):

    return get_packages_by_duration(db, days=days, skip=skip, limit=limit)


# ---------------------------------------------------
# GET PACKAGES BY BUDGET RANGE
# range: budget | standard | premium
# ---------------------------------------------------
def get_packages_budget(
    db: Session,
    budget_range: str,
    skip: int = 0,
    limit: int = 10,
):

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

    return get_packages_by_budget(
        db,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=limit,
    )


# ---------------------------------------------------
# GET PACKAGE DETAILS
# Accepts both UUID and slug
# ---------------------------------------------------
def get_package_details(db: Session, value: str):

    package = get_package_by_id_or_slug(db, value)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{value}' not found"
        )

    return package


# ---------------------------------------------------
# GET PACKAGE IMAGES
# ---------------------------------------------------
def get_package_images_list(db: Session, package_id: str):

    images = get_package_images(db, package_id)

    if images is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    return images


# ---------------------------------------------------
# GET PACKAGE REVIEWS
# Reviews handled by colleague
# ---------------------------------------------------
def get_package_reviews_list(
    db: Session,
    package_id: str,
    skip: int = 0,
    limit: int = 10,
):
    # Check package exists first
    package = get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    return get_package_reviews(db, package_id=package_id, skip=skip, limit=limit)


# ---------------------------------------------------
# UPDATE PACKAGE (ADMIN)
# ---------------------------------------------------
def update_existing_package(
    db: Session,
    package_id: str,
    package_update: PackageUpdate,
):
    # Check package exists
    package = get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{package_id}' not found"
        )

    # If slug is being updated check not taken by another package
    if package_update.slug and package_update.slug != package.slug:
        if slug_exists(db, slug=package_update.slug, exclude_id=package_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{package_update.slug}' is already taken"
            )

    update_data = package_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(package, key, value)

    return update_package(db, package)