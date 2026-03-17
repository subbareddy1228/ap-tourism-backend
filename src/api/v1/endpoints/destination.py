from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.models.destination import DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate
from src.services.destination_service import (
    get_destinations,
    get_featured_destinations,
    get_popular_destinations,
    get_destination_types,
    get_destination,
    create_destination,
    update_destination,
)

router = APIRouter(prefix="/destinations", tags=["Destinations"])


# ---------------------------------------
# GET ALL DESTINATIONS
# GET /api/v1/destinations/
# ---------------------------------------
@router.get("/")
async def list_destinations(
    type: Optional[DestinationType] = Query(None, description="NATURE | HERITAGE | ADVENTURE | COASTAL | RELIGIOUS"),
    district: Optional[str] = Query(None, description="Filter by district"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    return await get_destinations(db, page=page, limit=limit, type=type, district=district)


# ---------------------------------------
# GET FEATURED DESTINATIONS
# GET /api/v1/destinations/featured
# ---------------------------------------
@router.get("/featured")
async def list_featured_destinations(db: Session = Depends(get_db)):
    return await get_featured_destinations(db)


# ---------------------------------------
# GET POPULAR DESTINATIONS
# GET /api/v1/destinations/popular
# ---------------------------------------
@router.get("/popular")
async def list_popular_destinations(db: Session = Depends(get_db)):
    return await get_popular_destinations(db)


# ---------------------------------------
# GET DESTINATION TYPES
# GET /api/v1/destinations/types
# ---------------------------------------
@router.get("/types")
async def list_destination_types():
    return await get_destination_types()


# ---------------------------------------
# GET DESTINATION BY ID OR SLUG
# GET /api/v1/destinations/{value}
# NOTE: always last
# ---------------------------------------
@router.get("/{destination_id}")
async def retrieve_destination(destination_id: str, db: Session = Depends(get_db)):
    return await get_destination(db, destination_id)


# ---------------------------------------
# CREATE DESTINATION (Admin)
# POST /api/v1/destinations/
# ---------------------------------------
@router.post("/")
async def create_new_destination(
    data: DestinationCreate,
    db: Session = Depends(get_db),
):
    return await create_destination(db, data)


# ---------------------------------------
# UPDATE DESTINATION (Admin)
# PUT /api/v1/destinations/{destination_id}
# ---------------------------------------
@router.put("/{destination_id}")
async def update_existing_destination(
    destination_id: str,
    data: DestinationUpdate,
    db: Session = Depends(get_db),
):
    return await update_destination(db, destination_id, data)