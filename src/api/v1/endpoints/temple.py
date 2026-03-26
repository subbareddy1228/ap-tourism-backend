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
from src.api.deps.auth import get_admin_user, get_current_user, get_current_user
from src.models.user import User
from src.services import temple_service
from src.services import temple_service
from src.services.temple_service import TempleService
from src.schemas.temple import TempleCreate, TempleUpdate
from src.common.responses import APIResponse

router = APIRouter(prefix="/temples", tags=["Temples"])


# ── Redis dependency (optional — gracefully degrades if Redis down) ──
async def get_redis():
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
    redis = await get_redis()
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
    current_user: User = Depends(get_admin_user),
    svc: TempleService = Depends(get_service)
):
    temple = await svc.create_temple(data)
    return APIResponse.success(message="Temple created successfully", data=temple.model_dump())


@router.put("/{temple_id}", response_model=APIResponse, summary="[Admin] Update temple")
async def update_temple(
    temple_id: UUID,
    data: TempleUpdate,
    current_user: User = Depends(get_admin_user),
    svc: TempleService = Depends(get_service)
):
    try:
        temple = await svc.update_temple(temple_id, data)
        return APIResponse.success(message="Temple updated successfully", data=temple.model_dump())
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
 
# ══════════════════ ADMIN ENDPOINTS ══════════════════
 
@router.delete(

    "/{temple_id}",

    response_model=APIResponse,

    summary="[Admin] Delete temple"

)

async def delete_temple(

    temple_id: str,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.delete_temple(temple_id, db)

    return APIResponse.success(message=result["message"])
 
 
@router.post(

    "/{temple_id}/darshan-types",

    response_model=APIResponse,

    status_code=201,

    summary="[Admin] Add darshan type"

)

async def create_darshan_type(

    temple_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.create_darshan_type(temple_id, data, db)

    return APIResponse.success(message="Darshan type created", data=result)
 
 
@router.put(

    "/{temple_id}/darshan-types/{type_id}",

    response_model=APIResponse,

    summary="[Admin] Update darshan type"

)

async def update_darshan_type(

    temple_id: str,

    type_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.update_darshan_type(temple_id, type_id, data, db)

    return APIResponse.success(message="Darshan type updated", data=result)
 
 
@router.delete(

    "/{temple_id}/darshan-types/{type_id}",

    response_model=APIResponse,

    summary="[Admin] Delete darshan type"

)

async def delete_darshan_type(

    temple_id: str,

    type_id: str,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.delete_darshan_type(temple_id, type_id, db)

    return APIResponse.success(message=result["message"])
 
 
@router.post(

    "/{temple_id}/darshan-slots/bulk-generate",

    response_model=APIResponse,

    status_code=201,

    summary="[Admin] Bulk generate darshan slots"

)

async def bulk_generate_darshan_slots(

    temple_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.bulk_generate_darshan_slots(temple_id, data, db)

    return APIResponse.success(message="Slots generated", data=result)
 
 
@router.put(

    "/{temple_id}/darshan-slots/{slot_id}",

    response_model=APIResponse,

    summary="[Admin] Update darshan slot"

)

async def update_darshan_slot(

    temple_id: str,

    slot_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.update_darshan_slot(temple_id, slot_id, data, db)

    return APIResponse.success(message="Slot updated", data=result)
 
 
@router.post(

    "/{temple_id}/events",

    response_model=APIResponse,

    status_code=201,

    summary="[Admin] Create temple event"

)

async def create_temple_event(

    temple_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.create_event(temple_id, data, db)

    return APIResponse.success(message="Event created", data=result)
 
 
@router.put(

    "/{temple_id}/events/{event_id}",

    response_model=APIResponse,

    summary="[Admin] Update temple event"

)

async def update_temple_event(

    temple_id: str,

    event_id: str,

    data: dict,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.update_event(temple_id, event_id, data, db)

    return APIResponse.success(message="Event updated", data=result)
 
 
@router.delete(

    "/{temple_id}/events/{event_id}",

    response_model=APIResponse,

    summary="[Admin] Delete temple event"

)

async def delete_temple_event(

    temple_id: str,

    event_id: str,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    result = await temple_service.delete_event(temple_id, event_id, db)

    return APIResponse.success(message=result["message"])
 
 
@router.post(

    "/{temple_id}/sync-ttd",

    response_model=APIResponse,

    summary="[Admin] Sync darshan slots from TTD API"

)

async def sync_ttd(

    temple_id: str,

    current_user: User = Depends(get_admin_user),

    db: AsyncSession = Depends(get_db)

):

    from src.integrations.ttd_api import sync_temple_slots

    result = await sync_temple_slots(temple_id, db)

    return APIResponse.success(message="TTD sync complete", data=result)
 