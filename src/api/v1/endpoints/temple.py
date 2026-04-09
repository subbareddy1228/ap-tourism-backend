"""
api/v1/endpoints/temple.py  —  Temple Module Endpoints
Base URL : /temples
Tags     : Temples

All 28 endpoints across 6 groups:
  Public  listings   : GET /featured, /popular, /nearby, /by-deity/{deity},
                       /by-district/{district}, /
  Temple  detail     : GET /{id}, /{id}/images, /{id}/timings,
                       /{id}/events, /{id}/reviews
  Admin   temple     : POST /, PUT /{id}, DELETE /{id}
  Admin   images     : POST /{id}/images, DELETE /{id}/images/{image_id}
  Admin   darshan    : POST /{id}/darshan-types,
                       PUT  /{id}/darshan-types/{type_id},
                       DELETE /{id}/darshan-types/{type_id},
                       POST /{id}/darshan-slots/bulk-generate,
                       PUT  /{id}/darshan-slots/{slot_id}
  Admin   events     : POST /{id}/events, PUT /{id}/events/{event_id},
                       DELETE /{id}/events/{event_id}
  Admin   pooja      : POST /{id}/pooja-services,
                       PUT  /{id}/pooja-services/{service_id}
  User    reviews    : POST /{id}/reviews
  Admin   TTD sync   : POST /{id}/sync-ttd

Changes vs original:
  - Removed `from httpx import patch` — httpx is an HTTP client library;
    `patch` is a unittest.mock function. Both are wrong here. The sync_ttd
    endpoint now calls TempleService.sync_ttd() directly.
  - Removed broken mock/unittest.mock logic from sync_ttd endpoint.
  - Replaced raw `dict` body types with typed Pydantic schemas for
    darshan type, darshan slot, and event update endpoints — enables
    validation and correct OpenAPI docs.
  - Replaced inconsistent get_redis() implementation (was using sync redis
    library) with the project's standard async aioredis pattern from
    src.core.redis.
  - Standardised all admin endpoints to use TempleService via get_service()
    dependency instead of mixing two patterns (some used it, others didn't).
  - Route ordering: all static paths (/featured, /popular, /nearby,
    /by-deity/{deity}, /by-district/{district}, /{id}/sub-routes) are
    declared before the dynamic catch-all /{id} to prevent FastAPI
    matching literal path segments as temple_id values.
  - Added missing `status_code` on all 201 endpoints.
  - Removed duplicate import of TempleService and temple_service.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.redis import get_redis
from src.api.deps.auth import get_admin_user, get_current_user, get_verified_user
from src.models.user import User
from src.services.temple_service import TempleService
from src.schemas.temple import (
    TempleCreate,
    TempleUpdate,
    TempleReviewCreate,
    TempleEventCreate,
    TempleEventUpdate,
    PoojaServiceCreate,
    PoojaServiceUpdate,
    DarshanTypeCreate,
    DarshanTypeUpdate,
    DarshanSlotBulkGenerate,
    DarshanSlotUpdate,
)
from src.common.responses import APIResponse

router = APIRouter(prefix="/temples", tags=["Temples"])


# ─────────────────────────────────────────────────────────────────────────────
# Service factory dependency
# Uses the project-standard async Redis client from src.core.redis.
# ─────────────────────────────────────────────────────────────────────────────

async def get_service(db: AsyncSession = Depends(get_db)) -> TempleService:
    """Build TempleService with async Redis; gracefully degrades if Redis is down."""
    redis = None
    try:
        redis = await get_redis()
    except Exception:
        pass   # Redis unavailable — service falls through to DB queries
    return TempleService(db=db, redis_client=redis)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC LISTINGS
# Static routes MUST be declared before /{temple_id} so FastAPI does not
# interpret literal strings like "featured" or "popular" as UUID temple IDs.
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/featured",
    response_model=APIResponse,
    summary="Featured temples (cached 1 hr)",
)
async def get_featured(svc: TempleService = Depends(get_service)):
    data = await svc.get_featured()
    return APIResponse.success(
        message="Featured temples fetched",
        data=[d.model_dump() for d in data],
    )


@router.get(
    "/popular",
    response_model=APIResponse,
    summary="Popular temples by booking count",
)
async def get_popular(
    limit: int          = Query(10, ge=1, le=50),
    svc:   TempleService = Depends(get_service),
):
    data = await svc.get_popular(limit=limit)
    return APIResponse.success(
        message="Popular temples fetched",
        data=[d.model_dump() for d in data],
    )


@router.get(
    "/nearby",
    response_model=APIResponse,
    summary="Temples within a radius of a coordinate",
)
async def get_nearby(
    lat:       float        = Query(..., description="Latitude"),
    lng:       float        = Query(..., description="Longitude"),
    radius_km: float        = Query(50.0, ge=1.0, le=500.0),
    svc:       TempleService = Depends(get_service),
):
    data = await svc.get_nearby(lat=lat, lng=lng, radius_km=radius_km)
    return APIResponse.success(
        message="Nearby temples fetched",
        data=[d.model_dump() for d in data],
    )


@router.get(
    "/by-deity/{deity}",
    response_model=APIResponse,
    summary="Temples filtered by deity name",
)
async def get_by_deity(
    deity:     str,
    page:      int          = Query(1,  ge=1),
    page_size: int          = Query(20, ge=1, le=100),
    svc:       TempleService = Depends(get_service),
):
    data = await svc.get_by_deity(deity=deity, page=page, page_size=page_size)
    return APIResponse.success(
        message=f"Temples for deity '{deity}'",
        data=[d.model_dump() for d in data],
    )


@router.get(
    "/by-district/{district}",
    response_model=APIResponse,
    summary="Temples in an Andhra Pradesh district",
)
async def get_by_district(
    district:  str,
    page:      int          = Query(1,  ge=1),
    page_size: int          = Query(20, ge=1, le=100),
    svc:       TempleService = Depends(get_service),
):
    data = await svc.get_by_district(district=district, page=page, page_size=page_size)
    return APIResponse.success(
        message=f"Temples in '{district}'",
        data=[d.model_dump() for d in data],
    )


@router.get(
    "/",
    response_model=APIResponse,
    summary="List all active temples with optional filters",
)
async def list_temples(
    deity:        Optional[str] = Query(None),
    district:     Optional[str] = Query(None),
    darshan_type: Optional[str] = Query(None),
    page:         int           = Query(1,  ge=1),
    page_size:    int           = Query(20, ge=1, le=100),
    svc:          TempleService  = Depends(get_service),
):
    temples = await svc.list_temples(
        deity=deity, district=district,
        darshan_type=darshan_type,
        page=page, page_size=page_size,
    )
    total = await svc.repo.count_all(
        deity=deity, district=district, darshan_type=darshan_type
    )
    return APIResponse.success(
        message=f"{total} temples found",
        data={
            "temples":   [t.model_dump() for t in temples],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLE SUB-ROUTES  (must come before /{temple_id} catch-all)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}/images",
    response_model=APIResponse,
    summary="Temple image URLs stored in S3",
)
async def get_images(
    temple_id: UUID,
    svc:       TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_images(temple_id)
        return APIResponse.success(message="Images fetched", data=data)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{temple_id}/timings",
    response_model=APIResponse,
    summary="Day-wise opening schedule",
)
async def get_timings(
    temple_id: UUID,
    svc:       TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_timings(temple_id)
        return APIResponse.success(message="Timings fetched", data=data)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{temple_id}/events",
    response_model=APIResponse,
    summary="Upcoming temple events and festivals",
)
async def get_events(
    temple_id: UUID,
    svc:       TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_events(temple_id)
        return APIResponse.success(
            message="Events fetched",
            data=[d.model_dump() for d in data],
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{temple_id}/reviews",
    response_model=APIResponse,
    summary="Visitor reviews for a temple",
)
async def get_reviews(
    temple_id: UUID,
    page:      int          = Query(1,  ge=1),
    page_size: int          = Query(20, ge=1, le=100),
    svc:       TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_reviews(temple_id, page=page, page_size=page_size)
        return APIResponse.success(
            message="Reviews fetched",
            data=[d.model_dump() for d in data],
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLE DETAIL  (dynamic catch-all — MUST be last among GET /{temple_id}*)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}",
    response_model=APIResponse,
    summary="Full temple detail with events and reviews",
)
async def get_detail(
    temple_id: UUID,
    svc:       TempleService = Depends(get_service),
):
    try:
        data = await svc.get_temple_detail(temple_id)
        return APIResponse.success(message="Temple fetched", data=data.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# USER — REVIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/reviews",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a temple review (authenticated user)",
)
async def create_temple_review(
    temple_id:    UUID,
    data:         TempleReviewCreate,
    current_user: User         = Depends(get_verified_user),
    svc:          TempleService = Depends(get_service),
):
    """Submit a review for a temple. Requires phone/email verification."""
    result = await svc.create_review(str(temple_id), data, str(current_user.id))
    return APIResponse.success(message="Review submitted", data=result)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — TEMPLE CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Add a new temple",
)
async def create_temple(
    data:         TempleCreate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    temple = await svc.create_temple(data)
    return APIResponse.success(message="Temple created successfully", data=temple.model_dump())


@router.put(
    "/{temple_id}",
    response_model=APIResponse,
    summary="[Admin] Update temple details",
)
async def update_temple(
    temple_id:    UUID,
    data:         TempleUpdate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        temple = await svc.update_temple(temple_id, data)
        return APIResponse.success(message="Temple updated successfully", data=temple.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{temple_id}",
    response_model=APIResponse,
    summary="[Admin] Soft-delete a temple",
)
async def delete_temple(
    temple_id:    UUID,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.delete_temple(str(temple_id))
        return APIResponse.success(message=result["message"])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — IMAGES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/images",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Upload a temple image to S3",
)
async def upload_temple_image(
    temple_id:    UUID,
    file:         UploadFile   = File(...),
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.upload_temple_image(temple_id, file)
        return APIResponse.success(message="Image uploaded", data=result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete(
    "/{temple_id}/images/{image_id:path}",
    response_model=APIResponse,
    summary="[Admin] Delete a temple image from S3",
)
async def delete_temple_image(
    temple_id:    UUID,
    image_id:     str,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    """image_id is the full S3 URL of the image to remove."""
    try:
        result = await svc.delete_temple_image(str(temple_id), image_id)
        return APIResponse.success(message="Image deleted", data=result)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — DARSHAN TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/darshan-types",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Add a darshan type to a temple",
)
async def create_darshan_type(
    temple_id:    UUID,
    data:         DarshanTypeCreate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    result = await svc.create_darshan_type(temple_id, data)
    return APIResponse.success(message="Darshan type created", data=result.model_dump())


@router.put(
    "/{temple_id}/darshan-types/{type_id}",
    response_model=APIResponse,
    summary="[Admin] Update a darshan type",
)
async def update_darshan_type(
    temple_id:    UUID,
    type_id:      UUID,
    data:         DarshanTypeUpdate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.update_darshan_type(str(temple_id), str(type_id), data)
        return APIResponse.success(message="Darshan type updated", data=result.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{temple_id}/darshan-types/{type_id}",
    response_model=APIResponse,
    summary="[Admin] Soft-delete a darshan type",
)
async def delete_darshan_type(
    temple_id:    UUID,
    type_id:      UUID,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.delete_darshan_type(str(temple_id), str(type_id))
        return APIResponse.success(message=result["message"])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — DARSHAN SLOTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/darshan-slots/bulk-generate",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Bulk-generate darshan slots for a date range",
)
async def bulk_generate_darshan_slots(
    temple_id:    UUID,
    data:         DarshanSlotBulkGenerate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.bulk_generate_darshan_slots(str(temple_id), data)
        return APIResponse.success(message="Slots generated", data=result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/{temple_id}/darshan-slots/{slot_id}",
    response_model=APIResponse,
    summary="[Admin] Update a darshan slot",
)
async def update_darshan_slot(
    temple_id:    UUID,
    slot_id:      UUID,
    data:         DarshanSlotUpdate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.update_darshan_slot(str(temple_id), str(slot_id), data)
        return APIResponse.success(message="Slot updated", data=result.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/events",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a temple event",
)
async def create_temple_event(
    temple_id:    UUID,
    data:         TempleEventCreate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    result = await svc.create_event(temple_id, data)
    return APIResponse.success(message="Temple event created", data=result.model_dump())


@router.put(
    "/{temple_id}/events/{event_id}",
    response_model=APIResponse,
    summary="[Admin] Update a temple event",
)
async def update_temple_event(
    temple_id:    UUID,
    event_id:     UUID,
    data:         TempleEventUpdate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.update_event(str(temple_id), str(event_id), data)
        return APIResponse.success(message="Event updated", data=result.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{temple_id}/events/{event_id}",
    response_model=APIResponse,
    summary="[Admin] Soft-delete a temple event",
)
async def delete_temple_event(
    temple_id:    UUID,
    event_id:     UUID,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.delete_event(str(temple_id), str(event_id))
        return APIResponse.success(message=result["message"])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — POOJA SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/pooja-services",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Add a pooja service to a temple",
)
async def add_pooja_service(
    temple_id:    UUID,
    data:         PoojaServiceCreate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    result = await svc.create_pooja_service(str(temple_id), data)
    return APIResponse.success(message="Pooja service added", data=result)


@router.put(
    "/{temple_id}/pooja-services/{service_id}",
    response_model=APIResponse,
    summary="[Admin] Update a pooja service",
)
async def update_pooja_service(
    temple_id:    UUID,
    service_id:   UUID,
    data:         PoojaServiceUpdate,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    try:
        result = await svc.update_pooja_service(str(temple_id), str(service_id), data)
        return APIResponse.success(message="Pooja service updated", data=result)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — TTD SYNC
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/sync-ttd",
    response_model=APIResponse,
    summary="[Admin] Sync darshan slots from the TTD API",
)
async def sync_ttd(
    temple_id:    UUID,
    current_user: User         = Depends(get_admin_user),
    svc:          TempleService = Depends(get_service),
):
    """
    Pull today's darshan availability from the TTD (Tirumala Tirupati
    Devasthanams) API and upsert into darshan_slots.
    Falls back to mock data when TTD credentials are not configured.
    """
    try:
        result = await svc.sync_ttd(str(temple_id))
        return APIResponse.success(message="TTD sync complete", data=result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
