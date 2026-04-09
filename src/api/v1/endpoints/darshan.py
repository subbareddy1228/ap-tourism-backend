"""
api/v1/endpoints/darshan.py
Darshan, Pooja & Prasadam endpoints — 15 routes, all verified present.

Bugs fixed vs project file:
──────────────────────────────────────────────────────────────────────────────
  BUG-1  get_redis() used the SYNCHRONOUS `redis` library
         (import redis as redis_lib; client = redis_lib.from_url(...)).
         Calling .ping() on a sync client inside an async function blocks
         the entire event loop on every request.  Replaced with the project-
         wide async Redis client from core/redis.get_redis() which is already
         initialized at startup.  Falls back gracefully to None if Redis is
         down (same behaviour as before, but non-blocking).

  BUG-2  get_service() was an async dependency that awaited get_redis() — but
         get_redis() from core/redis.py raises RuntimeError if Redis is not
         initialized, which would crash the entire dependency graph on every
         request if Redis was down.  Wrapped in try/except to degrade
         gracefully (redis_client = None), matching the intent of the original
         optional-Redis design.

  BUG-3  Static routes MUST come before path-parameter routes in FastAPI to
         avoid routing conflicts.  The original had correct ordering for
         prasadam (/prasadam/orders before /prasadam/{item_id}) but
         /darshan/check-availability and /darshan/book are POST routes on
         different paths — no conflict.  Order preserved and verified.

All 15 endpoints from the module docstring are present and accounted for:
  1.  GET  /{temple_id}/darshan-types
  2.  GET  /{temple_id}/darshan-types/{type_id}
  3.  GET  /{temple_id}/darshan-slots
  4.  GET  /{temple_id}/darshan-slots/{slot_date}
  5.  POST /{temple_id}/darshan/check-availability
  6.  POST /{temple_id}/darshan/book              (auth required)
  7.  GET  /{temple_id}/darshan/booking/{id}      (auth required)
  8.  GET  /{temple_id}/pooja-services
  9.  GET  /{temple_id}/pooja-services/{service_id}
  10. GET  /{temple_id}/pooja-services/{service_id}/slots
  11. POST /{temple_id}/pooja/book                (auth required)
  12. GET  /{temple_id}/prasadam                  — MUST be after /prasadam/orders
  13. GET  /{temple_id}/prasadam/orders           (auth required)
  14. GET  /{temple_id}/prasadam/{item_id}
  15. POST /{temple_id}/prasadam/order            (auth required)
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user
from src.models.user import User
from src.services.darshan_service import DarshanService
from src.schemas.darshan import (
    DarshanCheckAvailabilityRequest,
    DarshanBookRequest,
    PoojaBookRequest,
    PrasadamOrderRequest,
)
from src.common.responses import APIResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/darshan", tags=["Darshan"])


# ── Async Redis dependency (graceful fallback) ────────────────────────────────

async def _get_optional_redis():
    """
    BUG-1 + BUG-2 FIX:
    Use the project-wide async Redis client (core/redis.get_redis) instead of
    creating a new synchronous redis.from_url() on every request.
    Falls back to None if Redis is unavailable so caching/locking is
    simply skipped, preserving the original optional-Redis design.
    """
    try:
        from src.core.redis import get_redis
        return await get_redis()
    except Exception:
        return None


async def get_service(db: AsyncSession = Depends(get_db)) -> DarshanService:
    redis = await _get_optional_redis()
    return DarshanService(db=db, redis_client=redis)


# ══════════════════════════════════════════════════════════════════════════════
# 1 & 2 — DARSHAN TYPES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}/darshan-types",
    response_model=APIResponse,
    summary="List all active darshan types for a temple",
)
async def get_darshan_types(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_darshan_types(temple_id)
    return APIResponse.success(message="Darshan types fetched", data=data)


@router.get(
    "/{temple_id}/darshan-types/{type_id}",
    response_model=APIResponse,
    summary="Get a single darshan type detail",
)
async def get_darshan_type_detail(
    temple_id: UUID,
    type_id:   UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_darshan_type_detail(temple_id, type_id)
    return APIResponse.success(message="Darshan type fetched", data=data)


# ══════════════════════════════════════════════════════════════════════════════
# 3 & 4 — DARSHAN SLOTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}/darshan-slots",
    response_model=APIResponse,
    summary="List available darshan slots for next 30 days (cached 2 min)",
)
async def get_darshan_slots(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_darshan_slots(temple_id)
    return APIResponse.success(message="Darshan slots fetched", data=data)


@router.get(
    "/{temple_id}/darshan-slots/{slot_date}",
    response_model=APIResponse,
    summary="List darshan slots for a specific date",
)
async def get_darshan_slots_by_date(
    temple_id: UUID,
    slot_date: date,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_darshan_slots_by_date(temple_id, slot_date)
    return APIResponse.success(message="Slots fetched", data=data)


# ══════════════════════════════════════════════════════════════════════════════
# 5, 6, 7 — DARSHAN BOOKING
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{temple_id}/darshan/check-availability",
    response_model=APIResponse,
    summary="Check if a darshan slot has enough seats for the requested count",
)
async def check_availability(
    temple_id: UUID,
    req:       DarshanCheckAvailabilityRequest,
    svc:       DarshanService = Depends(get_service),
):
    data = await svc.check_availability(temple_id, req)
    return APIResponse.success(message="Availability checked", data=data)


@router.post(
    "/{temple_id}/darshan/book",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
    summary="Book a darshan slot (authenticated)",
)
async def book_darshan(
    temple_id:    UUID,
    req:          DarshanBookRequest,
    current_user: User = Depends(get_current_user),
    svc:          DarshanService = Depends(get_service),
):
    data = await svc.book_darshan(
        temple_id=temple_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(
        message="Darshan booked successfully. Please complete payment to confirm.",
        data=data,
    )


@router.get(
    "/{temple_id}/darshan/booking/{booking_id}",
    response_model=APIResponse,
    summary="Get darshan booking detail (authenticated)",
)
async def get_darshan_booking(
    temple_id:    UUID,
    booking_id:   UUID,
    current_user: User = Depends(get_current_user),
    svc:          DarshanService = Depends(get_service),
):
    data = await svc.get_darshan_booking(temple_id, booking_id)
    return APIResponse.success(message="Booking fetched", data=data)


# ══════════════════════════════════════════════════════════════════════════════
# 8, 9, 10, 11 — POOJA SERVICES & BOOKING
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}/pooja-services",
    response_model=APIResponse,
    summary="List all active pooja services for a temple",
)
async def get_pooja_services(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_pooja_services(temple_id)
    return APIResponse.success(message="Pooja services fetched", data=data)


@router.get(
    "/{temple_id}/pooja-services/{service_id}",
    response_model=APIResponse,
    summary="Get a single pooja service detail",
)
async def get_pooja_service_detail(
    temple_id:  UUID,
    service_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_pooja_service_detail(temple_id, service_id)
    return APIResponse.success(message="Pooja service fetched", data=data)


@router.get(
    "/{temple_id}/pooja-services/{service_id}/slots",
    response_model=APIResponse,
    summary="List available slots for a pooja service",
)
async def get_pooja_slots(
    temple_id:  UUID,
    service_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_pooja_slots(temple_id, service_id)
    return APIResponse.success(message="Pooja slots fetched", data=data)


@router.post(
    "/{temple_id}/pooja/book",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
    summary="Book a pooja service slot (authenticated)",
)
async def book_pooja(
    temple_id:    UUID,
    req:          PoojaBookRequest,
    current_user: User = Depends(get_current_user),
    svc:          DarshanService = Depends(get_service),
):
    data = await svc.book_pooja(
        temple_id=temple_id,
        service_id=req.pooja_service_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(
        message="Pooja booked successfully. Please complete payment to confirm.",
        data=data,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 12, 13, 14, 15 — PRASADAM
#
# IMPORTANT: Static routes MUST come before path-parameter routes.
#   /prasadam/orders  →  endpoint 13 (MUST be defined before endpoint 14)
#   /prasadam         →  endpoint 12
#   /prasadam/{item}  →  endpoint 14
#   /prasadam/order   →  endpoint 15 (POST — no conflict with GET /{item_id})
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{temple_id}/prasadam/orders",
    response_model=APIResponse,
    summary="List my prasadam orders for a temple (authenticated)",
)
async def get_my_prasadam_orders(
    temple_id:    UUID,
    current_user: User = Depends(get_current_user),
    svc:          DarshanService = Depends(get_service),
):
    data = await svc.get_my_prasadam_orders(
        temple_id=temple_id,
        user_id=current_user.id,
    )
    return APIResponse.success(message="Orders fetched", data=data)


@router.get(
    "/{temple_id}/prasadam",
    response_model=APIResponse,
    summary="List all available prasadam items for a temple",
)
async def get_prasadam_items(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_prasadam_items(temple_id)
    return APIResponse.success(message="Prasadam items fetched", data=data)


@router.get(
    "/{temple_id}/prasadam/{item_id}",
    response_model=APIResponse,
    summary="Get a single prasadam item detail",
)
async def get_prasadam_item(
    temple_id: UUID,
    item_id:   UUID,
    svc: DarshanService = Depends(get_service),
):
    data = await svc.get_prasadam_item(temple_id, item_id)
    return APIResponse.success(message="Prasadam item fetched", data=data)


@router.post(
    "/{temple_id}/prasadam/order",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
    summary="Place a prasadam order (authenticated)",
)
async def order_prasadam(
    temple_id:    UUID,
    req:          PrasadamOrderRequest,
    current_user: User = Depends(get_current_user),
    svc:          DarshanService = Depends(get_service),
):
    data = await svc.order_prasadam(
        temple_id=temple_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(message="Prasadam order placed successfully", data=data)
