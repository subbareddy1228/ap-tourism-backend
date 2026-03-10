import re
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.destination import Destination
from src.models.destination import DestinationType


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _is_uuid(value: str) -> bool:
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, value.lower()))


# ─────────────────────────────────────────
# READ
# ─────────────────────────────────────────

def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
) -> List[Destination]:

    query = db.query(Destination).filter(Destination.is_active == True)

    if type:
        query = query.filter(Destination.type == type)
    if district:
        query = query.filter(Destination.district.ilike(f"%{district}%"))

    return query.offset(skip).limit(limit).all()


def get_count(
    db: Session,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
) -> int:
    """Total count for pagination."""
    query = db.query(Destination).filter(Destination.is_active == True)

    if type:
        query = query.filter(Destination.type == type)
    if district:
        query = query.filter(Destination.district.ilike(f"%{district}%"))

    return query.count()


def get_by_id(db: Session, destination_id: str) -> Optional[Destination]:

    return db.query(Destination).filter(
        Destination.id == destination_id,
        Destination.is_active == True
    ).first()


def get_by_slug(db: Session, slug: str) -> Optional[Destination]:

    return db.query(Destination).filter(
        Destination.slug == slug,
        Destination.is_active == True
    ).first()


def get_by_id_or_slug(db: Session, value: str) -> Optional[Destination]:
    """
    Single lookup for GET /{id} endpoint.
    Accepts both UUID and slug.

    Examples:
        get_by_id_or_slug(db, "araku-valley")
        get_by_id_or_slug(db, "f3a1b2c4-9d8e-4f2a-b1c3-a2b3c4d5e6f7")
    """
    if _is_uuid(value):
        return get_by_id(db, value)
    return get_by_slug(db, value)


def get_featured(db: Session) -> List[Destination]:

    return db.query(Destination).filter(
        Destination.is_featured == True,
        Destination.is_active == True
    ).all()


def get_popular(db: Session) -> List[Destination]:

    return db.query(Destination).filter(
        Destination.is_active == True
    ).order_by(
        Destination.reviews_count.desc(),
        Destination.rating.desc()
    ).limit(9).all()


def get_types() -> List[str]:
    return [e.value for e in DestinationType]


def slug_exists(
    db: Session,
    slug: str,
    exclude_id: Optional[str] = None
) -> bool:
    """Check if slug is already taken. Used before create/update."""
    query = db.query(Destination).filter(Destination.slug == slug)
    if exclude_id:
        query = query.filter(Destination.id != exclude_id)
    return query.first() is not None


# ─────────────────────────────────────────
# WRITE
# ─────────────────────────────────────────

def create(db: Session, destination: Destination) -> Destination:

    db.add(destination)
    db.commit()
    db.refresh(destination)

    return destination


def update(db: Session, destination: Destination) -> Destination:

    db.commit()
    db.refresh(destination)

    return destination