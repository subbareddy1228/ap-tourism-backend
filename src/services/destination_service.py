from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from src.models.destination import Destination, DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate, DestinationListResponse   
from src.repositories import destination_repo as repo


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

    return await repo.create(db, db_destination)


# ---------------------------------------
# GET ALL DESTINATIONS
# ---------------------------------------
async def get_destinations(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    type: Optional[DestinationType] = None,
    district: Optional[str] = None,
):
    items = await repo.get_all(db, skip=skip, limit=limit, type=type, district=district)
    total = await repo.get_count(db, type=type, district=district)

    return {
        "total": total,
        "items": [DestinationListResponse.model_validate(i) for i in items],
    }
          

# ---------------------------------------
# GET FEATURED DESTINATIONS
# ---------------------------------------
async def get_featured_destinations(db: Session):
    return await repo.get_featured(db)


# ---------------------------------------
# GET POPULAR DESTINATIONS
# ---------------------------------------
async def get_popular_destinations(db: Session):
    return await repo.get_popular(db)


# ---------------------------------------
# GET DESTINATION TYPES
# ---------------------------------------
async def get_destination_types():
    return await repo.get_types()


# ---------------------------------------
# GET DESTINATION BY ID
# ---------------------------------------
async def get_destination(db: Session, value: str):

    destination = await repo.get_by_id_or_slug(db, value)

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{value}' not found"
        )

    return destination


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

    return await repo.update(db, destination)