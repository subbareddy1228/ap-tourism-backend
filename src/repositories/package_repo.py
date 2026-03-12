import re
from typing import Optional

from sqlalchemy.orm import Session

from src.models.package import Package
from src.schemas.package import PackageUpdate


# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────

def _is_uuid(value: str) -> bool:
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, value.lower()))


# ----------------------------------
# CREATE PACKAGE (Admin)
# ----------------------------------
def create_package(db: Session, package: Package):

    db.add(package)
    db.commit()
    db.refresh(package)

    return package


# ----------------------------------
# GET ALL PACKAGES
# ----------------------------------
def get_packages(
    db: Session,
    skip: int = 0,
    limit: int = 10,
):

    return db.query(Package).filter(
        Package.is_active == True
    ).offset(skip).limit(limit).all()


def get_packages_count(db: Session) -> int:

    return db.query(Package).filter(
        Package.is_active == True
    ).count()


# ----------------------------------
# FEATURED PACKAGES
# ----------------------------------
def get_featured_packages(db: Session):

    return db.query(Package).filter(
        Package.is_featured == True,
        Package.is_active == True
    ).all()


# ----------------------------------
# POPULAR PACKAGES
# sorted by total_bookings + rating
# ----------------------------------
def get_popular_packages(db: Session):

    return db.query(Package).filter(
        Package.is_active == True
    ).order_by(
        Package.total_bookings.desc(),
        Package.rating.desc()
    ).limit(10).all()


# ----------------------------------
# FILTER BY DURATION
# ----------------------------------
def get_packages_by_duration(
    db: Session,
    days: int,
    skip: int = 0,
    limit: int = 10,
):

    return db.query(Package).filter(
        Package.duration_days == days,
        Package.is_active == True
    ).offset(skip).limit(limit).all()


def get_packages_by_duration_count(db: Session, days: int) -> int:

    return db.query(Package).filter(
        Package.duration_days == days,
        Package.is_active == True
    ).count()


# ----------------------------------
# FILTER BY BUDGET
# budget   → ₹5k  - ₹15k
# standard → ₹15k - ₹40k
# premium  → ₹40k+ (max_price is None)
# ----------------------------------
def get_packages_by_budget(
    db: Session,
    min_price: float,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 10,
):

    query = db.query(Package).filter(
        Package.price >= min_price,
        Package.is_active == True
    )

    if max_price is not None:
        query = query.filter(Package.price <= max_price)

    return query.offset(skip).limit(limit).all()


def get_packages_by_budget_count(
    db: Session,
    min_price: float,
    max_price: Optional[float] = None,
) -> int:

    query = db.query(Package).filter(
        Package.price >= min_price,
        Package.is_active == True
    )

    if max_price is not None:
        query = query.filter(Package.price <= max_price)

    return query.count()


# ----------------------------------
# GET PACKAGE BY ID
# ----------------------------------
def get_package_by_id(db: Session, package_id: str):

    return db.query(Package).filter(
        Package.id == package_id,
        Package.is_active == True
    ).first()


# ----------------------------------
# GET PACKAGE BY SLUG
# ----------------------------------
def get_package_by_slug(db: Session, slug: str):

    return db.query(Package).filter(
        Package.slug == slug,
        Package.is_active == True
    ).first()


# ----------------------------------
# GET PACKAGE BY ID OR SLUG
#
# Examples:
#   /packages/araku-valley-3-days      → slug lookup
#   /packages/f3a1b2c4-9d8e-...       → UUID lookup
# ----------------------------------
def get_package_by_id_or_slug(db: Session, value: str):

    if _is_uuid(value):
        return get_package_by_id(db, value)
    return get_package_by_slug(db, value)


# ----------------------------------
# GET PACKAGE IMAGES
# ----------------------------------
def get_package_images(db: Session, package_id: str):

    package = get_package_by_id(db, package_id)
    if not package:
        return None
    return package.images


# ----------------------------------
# GET PACKAGE REVIEWS
# Reviews model handled by colleague
# Uncomment when colleague finishes review module
# Agree on: src/models/review.py → Review.package_id
# ----------------------------------
def get_package_reviews(
    db: Session,
    package_id: str,
    skip: int = 0,
    limit: int = 10,
):
    # from src.models.review import Review
    # return db.query(Review).filter(
    #     Review.package_id == package_id
    # ).offset(skip).limit(limit).all()
    pass


def get_package_reviews_count(db: Session, package_id: str) -> int:
    # from src.models.review import Review
    # return db.query(Review).filter(
    #     Review.package_id == package_id
    # ).count()
    pass


# ----------------------------------
# CHECK SLUG EXISTS
# Used before create/update
# ----------------------------------
def slug_exists(
    db: Session,
    slug: str,
    exclude_id: Optional[str] = None,
) -> bool:

    query = db.query(Package).filter(Package.slug == slug)

    if exclude_id:
        query = query.filter(Package.id != exclude_id)

    return query.first() is not None


# ----------------------------------
# UPDATE PACKAGE
# ----------------------------------
def update_package(db: Session, package: Package):

    db.commit()
    db.refresh(package)

    return package
