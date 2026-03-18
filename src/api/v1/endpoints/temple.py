from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.services.temple_service import TempleService
from src.schemas.temple import TempleCreate, TempleUpdate
from src.common.responses import ResponseSchema, PaginatedResponse

router = APIRouter(prefix="/temples", tags=["Temples"])


async def get_service(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TempleService:
    return TempleService(db=db, redis_client=redis)


# ═════════════════════════════════════════════
# PUBLIC LISTINGS
# Static routes MUST come before /{temple_id}
# ═════════════════════════════════════════════

@router.get("/featured", summary="Featured temples (cached 1hr)")
async def get_featured(svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_featured())


@router.get("/popular", summary="Popular temples by booking count")
async def get_popular(
    limit: int = Query(10, ge=1, le=50),
    svc: TempleService = Depends(get_service),
):
    return ResponseSchema.ok(data=await svc.get_popular(limit=limit))


@router.get("/nearby", summary="Temples near a location")
async def get_nearby(
    lat:       float = Query(...),
    lng:       float = Query(...),
    radius_km: float = Query(50.0, ge=1.0, le=500.0),
    svc: TempleService = Depends(get_service),
):
    return ResponseSchema.ok(data=await svc.get_nearby(lat=lat, lng=lng, radius_km=radius_km))


@router.get("/by-deity/{deity}", summary="Temples filtered by deity")
async def get_by_deity(
    deity: str,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    return ResponseSchema.ok(data=await svc.get_by_deity(deity=deity, page=page, page_size=page_size))


@router.get("/by-district/{district}", summary="Temples filtered by AP district")
async def get_by_district(
    district: str,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    return ResponseSchema.ok(data=await svc.get_by_district(district=district, page=page, page_size=page_size))


@router.get("/", summary="List all temples with filters")
async def list_temples(
    deity:        Optional[str] = Query(None),
    district:     Optional[str] = Query(None),
    darshan_type: Optional[str] = Query(None),
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    temples = await svc.list_temples(
        deity=deity, district=district,
        darshan_type=darshan_type,
        page=page, page_size=page_size,
    )
    total = await svc.repo.count_all(deity=deity, district=district, darshan_type=darshan_type)
    return PaginatedResponse.ok(data=temples, total=total, page=page, page_size=page_size)


# ═════════════════════════════════════════════
# TEMPLE DETAIL
# ═════════════════════════════════════════════

@router.get("/{temple_id}/images", summary="Temple images from S3")
async def get_images(temple_id: UUID, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_temple_images(temple_id))


@router.get("/{temple_id}/timings", summary="Day-wise opening/closing schedule")
async def get_timings(temple_id: UUID, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_temple_timings(temple_id))


@router.get("/{temple_id}/events", summary="Upcoming temple events and festivals")
async def get_events(temple_id: UUID, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_temple_events(temple_id))


@router.get("/{temple_id}/reviews", summary="Visitor reviews for temple")
async def get_reviews(
    temple_id: UUID,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    return ResponseSchema.ok(data=await svc.get_temple_reviews(temple_id, page=page, page_size=page_size))


@router.get("/{temple_id}", summary="Full temple detail")
async def get_detail(temple_id: UUID, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_temple_detail(temple_id))


# ═════════════════════════════════════════════
# ADMIN
# TODO: add Depends(require_admin) when Auth module ready
# ═════════════════════════════════════════════

@router.post("/", status_code=status.HTTP_201_CREATED, summary="[Admin] Add new temple")
async def create_temple(data: TempleCreate, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.create_temple(data), message="Temple created successfully")


@router.put("/{temple_id}", summary="[Admin] Update temple")
async def update_temple(temple_id: UUID, data: TempleUpdate, svc: TempleService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.update_temple(temple_id, data), message="Temple updated successfully")