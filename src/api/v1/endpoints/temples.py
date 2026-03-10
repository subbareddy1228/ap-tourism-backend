from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.deps.database import get_db
from src.services.temple_service import TempleService
from src.schemas.temple import (
    TempleCreate, TempleUpdate, TempleDetail,
    TempleListItem, TempleEventResponse, TempleReviewResponse,
)
from src.core.redis import get_redis

router = APIRouter(prefix="/temples", tags=["Temple"])


def get_temple_service(
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> TempleService:
    return TempleService(db=db, redis_client=redis)


# ═════════════════════════════════════════════
# PUBLIC — Temple Listings
# ═════════════════════════════════════════════

@router.get("/", response_model=List[TempleListItem], summary="List all temples")
def list_temples(
    deity: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TempleService = Depends(get_temple_service),
):
    return service.list_temples(deity=deity, district=district, page=page, page_size=page_size)


@router.get("/featured", response_model=List[TempleListItem], summary="Featured temples")
def get_featured_temples(service: TempleService = Depends(get_temple_service)):
    return service.get_featured()


@router.get("/popular", response_model=List[TempleListItem], summary="Popular temples")
def get_popular_temples(
    limit: int = Query(10, ge=1, le=50),
    service: TempleService = Depends(get_temple_service),
):
    return service.get_popular(limit=limit)


@router.get("/nearby", response_model=List[TempleListItem], summary="Nearby temples")
def get_nearby_temples(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(50.0, ge=1.0, le=500.0),
    service: TempleService = Depends(get_temple_service),
):
    return service.get_nearby(lat=lat, lng=lng, radius_km=radius_km)


@router.get("/by-deity/{deity}", response_model=List[TempleListItem], summary="Temples by deity")
def get_temples_by_deity(
    deity: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TempleService = Depends(get_temple_service),
):
    return service.get_by_deity(deity=deity, page=page, page_size=page_size)


@router.get("/by-district/{district}", response_model=List[TempleListItem], summary="Temples by district")
def get_temples_by_district(
    district: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TempleService = Depends(get_temple_service),
):
    return service.get_by_district(district=district, page=page, page_size=page_size)


# ═════════════════════════════════════════════
# PUBLIC — Temple Detail
# ═════════════════════════════════════════════

@router.get("/{temple_id}", response_model=TempleDetail, summary="Full temple detail")
def get_temple_detail(
    temple_id: UUID,
    service: TempleService = Depends(get_temple_service),
):
    return service.get_temple_detail(temple_id)


@router.get("/{temple_id}/images", response_model=List[str], summary="Temple images")
def get_temple_images(
    temple_id: UUID,
    service: TempleService = Depends(get_temple_service),
):
    return service.get_temple_images(temple_id)


@router.get("/{temple_id}/timings", summary="Temple timings")
def get_temple_timings(
    temple_id: UUID,
    service: TempleService = Depends(get_temple_service),
):
    return service.get_temple_timings(temple_id)


@router.get("/{temple_id}/events", response_model=List[TempleEventResponse], summary="Temple events")
def get_temple_events(
    temple_id: UUID,
    service: TempleService = Depends(get_temple_service),
):
    return service.get_temple_events(temple_id)


@router.get("/{temple_id}/reviews", response_model=List[TempleReviewResponse], summary="Temple reviews")
def get_temple_reviews(
    temple_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TempleService = Depends(get_temple_service),
):
    return service.get_temple_reviews(temple_id, page=page, page_size=page_size)


# ═════════════════════════════════════════════
# ADMIN — Temple Management
# ═════════════════════════════════════════════

@router.post("/", response_model=TempleDetail, status_code=status.HTTP_201_CREATED, summary="[Admin] Add new temple")
def create_temple(
    data: TempleCreate,
    service: TempleService = Depends(get_temple_service),
):
    return service.create_temple(data)


@router.put("/{temple_id}", response_model=TempleDetail, summary="[Admin] Update temple")
def update_temple(
    temple_id: UUID,
    data: TempleUpdate,
    service: TempleService = Depends(get_temple_service),
):
    return service.update_temple(temple_id, data)