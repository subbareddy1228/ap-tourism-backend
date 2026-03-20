"""
api/v1/endpoints/darshan.py
Darshan, Pooja & Prasadam endpoints — fixed to use LEV146 patterns.

Routes:
  GET  /darshan/{temple_id}/darshan-types           → List darshan types
  GET  /darshan/{temple_id}/darshan-types/{type_id} → Type detail
  GET  /darshan/{temple_id}/darshan-slots           → Slots next 30 days
  GET  /darshan/{temple_id}/darshan-slots/{date}    → Slots for date
  POST /darshan/{temple_id}/darshan/check-availability → Check availability
  POST /darshan/{temple_id}/darshan/book            → Book darshan slot
  GET  /darshan/{temple_id}/darshan/booking/{id}    → Booking detail
  GET  /darshan/{temple_id}/pooja-services          → List pooja services
  GET  /darshan/{temple_id}/pooja-services/{id}     → Service detail
  GET  /darshan/{temple_id}/pooja-services/{id}/slots → Available slots
  POST /darshan/{temple_id}/pooja/book              → Book pooja
  GET  /darshan/{temple_id}/prasadam                → List prasadam items
  GET  /darshan/{temple_id}/prasadam/orders         → My orders
  GET  /darshan/{temple_id}/prasadam/{item_id}      → Item detail
  POST /darshan/{temple_id}/prasadam/order          → Order prasadam
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user
from src.services.darshan_service import DarshanService
from src.schemas.darshan import (
    DarshanCheckAvailabilityRequest,
    DarshanBookRequest,
    PoojaBookRequest,
    PrasadamOrderRequest,
)
from src.common.responses import APIResponse

router = APIRouter(prefix="/darshan", tags=["Darshan"])


# ── Redis dependency (optional) ───────────────────────────────
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


async def get_service(db: AsyncSession = Depends(get_db)) -> DarshanService:
    redis = get_redis()
    return DarshanService(db=db, redis_client=redis)


# ═══════════════════════════════════════════════════════════════
# DARSHAN TYPES
# ═══════════════════════════════════════════════════════════════

@router.get("/{temple_id}/darshan-types", response_model=APIResponse, summary="List darshan types")
async def get_darshan_types(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_darshan_types(temple_id)
    return APIResponse.success(message="Darshan types fetched", data=data)


@router.get("/{temple_id}/darshan-types/{type_id}", response_model=APIResponse, summary="Darshan type detail")
async def get_darshan_type_detail(
    temple_id: UUID,
    type_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_darshan_type_detail(temple_id, type_id)
    return APIResponse.success(message="Darshan type fetched", data=data)


# ═══════════════════════════════════════════════════════════════
# DARSHAN SLOTS
# ═══════════════════════════════════════════════════════════════

@router.get("/{temple_id}/darshan-slots", response_model=APIResponse, summary="All slots next 30 days")
async def get_darshan_slots(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_darshan_slots(temple_id)
    return APIResponse.success(message="Darshan slots fetched", data=data)


@router.get("/{temple_id}/darshan-slots/{slot_date}", response_model=APIResponse, summary="Slots for a specific date")
async def get_darshan_slots_by_date(
    temple_id: UUID,
    slot_date: date,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_darshan_slots_by_date(temple_id, slot_date)
    return APIResponse.success(message="Slots fetched", data=data)


# ═══════════════════════════════════════════════════════════════
# DARSHAN BOOKING
# ═══════════════════════════════════════════════════════════════

@router.post("/{temple_id}/darshan/check-availability", response_model=APIResponse, summary="Check darshan availability")
async def check_availability(
    temple_id: UUID,
    req: DarshanCheckAvailabilityRequest,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.check_availability(temple_id, req)
    return APIResponse.success(message="Availability checked", data=data)


@router.post("/{temple_id}/darshan/book", status_code=status.HTTP_201_CREATED, response_model=APIResponse, summary="Book darshan slot")
async def book_darshan(
    temple_id: UUID,
    req: DarshanBookRequest,
    current_user = Depends(get_current_user),
    svc: DarshanService = Depends(get_service),
):
    data = await svc.book_darshan(
        temple_id=temple_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(message="Darshan booked. Please complete payment.", data=data)


@router.get("/{temple_id}/darshan/booking/{booking_id}", response_model=APIResponse, summary="Darshan booking detail")
async def get_darshan_booking(
    temple_id: UUID,
    booking_id: UUID,
    current_user = Depends(get_current_user),
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_darshan_booking(temple_id, booking_id)
    return APIResponse.success(message="Booking fetched", data=data)


# ═══════════════════════════════════════════════════════════════
# POOJA SERVICES
# ═══════════════════════════════════════════════════════════════

@router.get("/{temple_id}/pooja-services", response_model=APIResponse, summary="List pooja services")
async def get_pooja_services(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_pooja_services(temple_id)
    return APIResponse.success(message="Pooja services fetched", data=data)


@router.get("/{temple_id}/pooja-services/{service_id}", response_model=APIResponse, summary="Pooja service detail")
async def get_pooja_service_detail(
    temple_id: UUID,
    service_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_pooja_service_detail(temple_id, service_id)
    return APIResponse.success(message="Pooja service fetched", data=data)


@router.get("/{temple_id}/pooja-services/{service_id}/slots", response_model=APIResponse, summary="Available pooja slots")
async def get_pooja_slots(
    temple_id: UUID,
    service_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_pooja_slots(temple_id, service_id)
    return APIResponse.success(message="Pooja slots fetched", data=data)


@router.post("/{temple_id}/pooja/book", status_code=status.HTTP_201_CREATED, response_model=APIResponse, summary="Book pooja")
async def book_pooja(
    temple_id: UUID,
    req: PoojaBookRequest,
    current_user = Depends(get_current_user),
    svc: DarshanService = Depends(get_service),
):
    data = await svc.book_pooja(
        temple_id=temple_id,
        service_id=req.pooja_service_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(message="Pooja booked. Please complete payment.", data=data)


# ═══════════════════════════════════════════════════════════════
# PRASADAM
# /prasadam/orders MUST be before /prasadam/{item_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/{temple_id}/prasadam/orders", response_model=APIResponse, summary="My prasadam orders")
async def get_my_prasadam_orders(
    temple_id: UUID,
    current_user = Depends(get_current_user),
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_my_prasadam_orders(
        temple_id=temple_id,
        user_id=current_user.id,
    )
    return APIResponse.success(message="Orders fetched", data=data)


@router.get("/{temple_id}/prasadam", response_model=APIResponse, summary="List prasadam items")
async def get_prasadam_items(
    temple_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_prasadam_items(temple_id)
    return APIResponse.success(message="Prasadam items fetched", data=data)


@router.get("/{temple_id}/prasadam/{item_id}", response_model=APIResponse, summary="Prasadam item detail")
async def get_prasadam_item(
    temple_id: UUID,
    item_id: UUID,
    svc: DarshanService = Depends(get_service)
):
    data = await svc.get_prasadam_item(temple_id, item_id)
    return APIResponse.success(message="Item fetched", data=data)


@router.post("/{temple_id}/prasadam/order", status_code=status.HTTP_201_CREATED, response_model=APIResponse, summary="Order prasadam")
async def order_prasadam(
    temple_id: UUID,
    req: PrasadamOrderRequest,
    current_user = Depends(get_current_user),
    svc: DarshanService = Depends(get_service),
):
    data = await svc.order_prasadam(
        temple_id=temple_id,
        user_id=current_user.id,
        req=req,
    )
    return APIResponse.success(message="Prasadam order placed successfully.", data=data)