from sqlalchemy.orm import Session
from typing import List, Optional
from src.models.destination import DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate
from src.repositories import destination_repo as repo
from fastapi import HTTPException, status



# ---------------------------------------
# CREATE DESTINATION (Admin)
# ---------------------------------------
def create_destination(db: Session, data: DestinationCreate):

    # Check slug already taken
    if repo.slug_exists(db, slug=data.slug):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slug '{data.slug}' is already taken")

    destination = repo.create_destination(db, data)

    return destination


# ---------------------------------------
# GET ALL DESTINATIONS
# ---------------------------------------
def get_destinations(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
):

    items = repo.get_destinations(
        db,
        skip=skip,
        limit=limit,
        type=type,
        district=district,
    )

    total = repo.get_destinations_count(db, type=type, district=district)

    return {
        "total": total,
        "items": items,
    }


# ---------------------------------------
# GET FEATURED DESTINATIONS
# ---------------------------------------
def get_featured_destinations(db: Session):

    return repo.get_featured_destinations(db)


# ---------------------------------------
# GET POPULAR DESTINATIONS
# ---------------------------------------
def get_popular_destinations(db: Session):

    return repo.get_popular_destinations(db)


# ---------------------------------------
# GET DESTINATION TYPES
# ---------------------------------------
def get_destination_types():

    return repo.get_destination_types()


# ---------------------------------------
# GET DESTINATION BY ID OR SLUG
# ---------------------------------------
def get_destination(db: Session, value: str):

    destination = repo.get_destination_by_id_or_slug(db, value)

    if not destination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination '{value}' not found")

    return destination


# ---------------------------------------
# UPDATE DESTINATION (Admin)
# ---------------------------------------
def update_destination(
    db: Session,
    destination_id: str,
    data: DestinationUpdate,
):

    # Check destination exists
    destination = repo.get_destination_by_id(db, destination_id)
    if not destination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination '{destination_id}' not found")

    # If slug is being updated, check it's not taken by another destination
    if data.slug and data.slug != destination.slug:
        if repo.slug_exists(db, slug=data.slug, exclude_id=destination_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slug '{data.slug}' is already taken")

    updated = repo.update_destination(db, destination_id, data)

    return updated