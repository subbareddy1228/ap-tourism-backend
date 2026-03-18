"""
api/v1/endpoints/temples.py
Temple module endpoints — fixed to use LEV146 patterns.

Routes:
  GET  /temples/featured           → Featured temples (cached 1hr)
  GET  /temples/popular            → Popular by booking count
  GET  /temples/nearby             → Near lat/lng within radius_km
  GET  /temples/by-deity/{deity}   → Filter by deity
  GET  /temples/by-district/{district} → Filter by AP district
  GET  /temples/                   → List all with filters
  GET  /temples/{temple_id}        → Full temple detail
  GET  /temples/{temple_id}/images → S3 images
  GET  /temples/{temple_id}/timings → Day-wise schedule
  GET  /temples/{temple_id}/events → Upcoming events
  GET  /temples/{temple_id}/reviews → Visitor reviews
  POST /temples/                   → [Admin] Add temple
  PUT  /temples/{temple_id}        → [Admin] Update temple
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.temple_service import TempleService
from src.schemas.temple import TempleCreate, TempleUpdate
from src.common.responses import APIResponse

router = APIRouter(prefix="/temples", tags=["Temples"])


# ── Redis dependency (optional — gracefully degrades if Redis down) ──
def get_redis():
    import redis as redis_lib
    from src.core.config import settings
    client = None
    try:
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception:
        client = None
    return client


async def get_service(
    db: AsyncSession = Depends(get_db),
) -> TempleService:
    redis = get_redis()
    return TempleService(db=db, redis_client=redis)


# ═══════════════════════════════════════════════════════════════
# PUBLIC LISTINGS
# Static routes MUST come before /{temple_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/featured", response_model=APIResponse, summary="Featured temples (cached 1hr)")
async def get_featured(svc: TempleService = Depends(get_service)):
    data = await svc.get_featured()
    return APIResponse.success(message="Featured temples fetched", data=[d.model_dump() for d in data])


@router.get("/popular", response_model=APIResponse, summary="Popular temples by booking count")
async def get_popular(
    limit: int = Query(10, ge=1, le=50),
    svc: TempleService = Depends(get_service),
):
    data = await svc.get_popular(limit=limit)
    return APIResponse.success(message="Popular temples fetched", data=[d.model_dump() for d in data])


@router.get("/nearby", response_model=APIResponse, summary="Temples near a location")
async def get_nearby(
    lat:       float = Query(..., description="Latitude"),
    lng:       float = Query(..., description="Longitude"),
    radius_km: float = Query(50.0, ge=1.0, le=500.0),
    svc: TempleService = Depends(get_service),
):
    data = await svc.get_nearby(lat=lat, lng=lng, radius_km=radius_km)
    return APIResponse.success(message="Nearby temples fetched", data=[d.model_dump() for d in data])


@router.get("/by-deity/{deity}", response_model=APIResponse, summary="Temples by deity")
async def get_by_deity(
    deity: str,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    data = await svc.get_by_deity(deity=deity, page=page, page_size=page_size)
    return APIResponse.success(message=f"Temples for deity {deity}", data=[d.model_dump() for d in data])


@router.get("/by-district/{district}", response_model=APIResponse, summary="Temples by AP district")
async def get_by_district(
    district: str,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    data = await svc.get_by_district(district=district, page=page, page_size=page_size)
    return APIResponse.success(message=f"Temples in {district}", data=[d.model_dump() for d in data])


@router.get("/", response_model=APIResponse, summary="List all temples with filters")
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
    return APIResponse.success(
        message=f"{total} temples found",
        data={
            "temples":   [t.model_dump() for t in temples],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }
    )


# ═══════════════════════════════════════════════════════════════
# TEMPLE DETAIL
# ═══════════════════════════════════════════════════════════════

@router.get("/{temple_id}/images", response_model=APIResponse, summary="Temple images from S3")
async def get_images(
    temple_id: UUID,
    svc: TempleService = Depends(get_service)
):
    try:
        data = await svc.get_temple_images(temple_id)
        return APIResponse.success(message="Images fetched", data=data)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{temple_id}/timings", response_model=APIResponse, summary="Day-wise opening schedule")
async def get_timings(
    temple_id: UUID,
    svc: TempleService = Depends(get_service)
):
    try:
        data = await svc.get_temple_timings(temple_id)
        return APIResponse.success(message="Timings fetched", data=data)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{temple_id}/events", response_model=APIResponse, summary="Upcoming temple events")
async def get_events(
    temple_id: UUID,
    svc: TempleService = Depends(get_service)
):
    try:
        data = await svc.get_temple_events(temple_id)
        return APIResponse.success(message="Events fetched", data=[d.model_dump() for d in data])
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{temple_id}/reviews", response_model=APIResponse, summary="Visitor reviews")
async def get_reviews(
    temple_id: UUID,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_reviews(temple_id, page=page, page_size=page_size)
        return APIResponse.success(message="Reviews fetched", data=[d.model_dump() for d in data])
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{temple_id}", response_model=APIResponse, summary="Full temple detail")
async def get_detail(
    temple_id: UUID,
    svc: TempleService = Depends(get_service)
):
    try:
        data = await svc.get_temple_detail(temple_id)
        return APIResponse.success(message="Temple fetched", data=data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=APIResponse, summary="[Admin] Add new temple")
async def create_temple(
    data: TempleCreate,
    svc: TempleService = Depends(get_service)
):
    temple = await svc.create_temple(data)
    return APIResponse.success(message="Temple created successfully", data=temple.model_dump())


@router.put("/{temple_id}", response_model=APIResponse, summary="[Admin] Update temple")
async def update_temple(
    temple_id: UUID,
    data: TempleUpdate,
    svc: TempleService = Depends(get_service)
):
    try:
        temple = await svc.update_temple(temple_id, data)
        return APIResponse.success(message="Temple updated successfully", data=temple.model_dump())
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))