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


# PUBLIC
@router.get("/")
def list_destinations(
    type: Optional[DestinationType] = Query(None),
    district: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_destinations(db, skip=skip, limit=limit, type=type, district=district)


@router.get("/featured")
def get_featured_destinations(db: Session = Depends(get_db)):
    return get_featured_destinations(db)


@router.get("/popular")
def get_popular_destinations(db: Session = Depends(get_db)):
    return get_popular_destinations(db)


@router.get("/types")
def get_destination_types():
    return get_destination_types()


@router.get("/{value}")
def get_destination(value: str, db: Session = Depends(get_db)):
    return get_destination(db, value)


# ADMIN
@router.post("/")
def create_destination(
    data: DestinationCreate,
    db: Session = Depends(get_db),
):
    return create_destination(db, data)


@router.put("/{destination_id}")
def update_destination(
    destination_id: str,
    data: DestinationUpdate,
    db: Session = Depends(get_db),
):
    return update_destination(db, destination_id, data)