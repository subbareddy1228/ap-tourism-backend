from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.services.darshan_service import DarshanService
from src.schemas.darshan import (
    DarshanCheckAvailabilityRequest,
    DarshanBookRequest,
    PoojaBookRequest,
    PrasadamOrderRequest,
)
from src.common.responses import ResponseSchema

router = APIRouter(prefix="/temples", tags=["Darshan, Pooja & Prasadam"])


async def get_service(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> DarshanService:
    return DarshanService(db=db, redis_client=redis)


# ═════════════════════════════════════════════
# DARSHAN TYPES
# ═════════════════════════════════════════════

@router.get("/{temple_id}/darshan-types", summary="List darshan types")
async def get_darshan_types(temple_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_darshan_types(temple_id))


@router.get("/{temple_id}/darshan-types/{type_id}", summary="Darshan type detail")
async def get_darshan_type_detail(temple_id: UUID, type_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_darshan_type_detail(temple_id, type_id))


# ═════════════════════════════════════════════
# DARSHAN SLOTS
# ═════════════════════════════════════════════

@router.get("/{temple_id}/darshan-slots", summary="All slots next 30 days (cached 2 min)")
async def get_darshan_slots(temple_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_darshan_slots(temple_id))


@router.get("/{temple_id}/darshan-slots/{slot_date}", summary="Slots for a specific date")
async def get_darshan_slots_by_date(temple_id: UUID, slot_date: date, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_darshan_slots_by_date(temple_id, slot_date))


# ═════════════════════════════════════════════
# DARSHAN BOOKING
# ═════════════════════════════════════════════

@router.post("/{temple_id}/darshan/check-availability", summary="Check darshan availability")
async def check_availability(temple_id: UUID, req: DarshanCheckAvailabilityRequest, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.check_availability(temple_id, req))


@router.post("/{temple_id}/darshan/book", status_code=status.HTTP_201_CREATED, summary="Book darshan slot")
async def book_darshan(
    temple_id: UUID,
    req: DarshanBookRequest,
    svc: DarshanService = Depends(get_service),
):
    # TODO: replace with current_user.id once Auth module ready
    data = await svc.book_darshan(
        temple_id=temple_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        req=req,
    )
    return ResponseSchema.ok(data=data, message="Darshan booked. Please complete payment.")


@router.get("/{temple_id}/darshan/booking/{booking_id}", summary="Get darshan booking detail")
async def get_darshan_booking(temple_id: UUID, booking_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_darshan_booking(temple_id, booking_id))


# ═════════════════════════════════════════════
# POOJA SERVICES
# ═════════════════════════════════════════════

@router.get("/{temple_id}/pooja-services", summary="List pooja services")
async def get_pooja_services(temple_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_pooja_services(temple_id))


@router.get("/{temple_id}/pooja-services/{service_id}", summary="Pooja service detail")
async def get_pooja_service_detail(temple_id: UUID, service_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_pooja_service_detail(temple_id, service_id))


@router.get("/{temple_id}/pooja-services/{service_id}/slots", summary="Available pooja slots")
async def get_pooja_slots(temple_id: UUID, service_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_pooja_slots(temple_id, service_id))


@router.post("/{temple_id}/pooja/book", status_code=status.HTTP_201_CREATED, summary="Book pooja")
async def book_pooja(
    temple_id: UUID,
    req: PoojaBookRequest,
    svc: DarshanService = Depends(get_service),
):
    # TODO: replace with current_user.id once Auth module ready
    data = await svc.book_pooja(
        temple_id=temple_id,
        service_id=req.pooja_service_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        req=req,
    )
    return ResponseSchema.ok(data=data, message="Pooja booked. Please complete payment.")


# ═════════════════════════════════════════════
# PRASADAM
# /prasadam/orders MUST be before /prasadam/{item_id}
# ═════════════════════════════════════════════

@router.get("/{temple_id}/prasadam/orders", summary="My prasadam orders")
async def get_my_prasadam_orders(temple_id: UUID, svc: DarshanService = Depends(get_service)):
    # TODO: replace with current_user.id once Auth module ready
    return ResponseSchema.ok(data=await svc.get_my_prasadam_orders(
        temple_id=temple_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
    ))


@router.get("/{temple_id}/prasadam", summary="List prasadam items")
async def get_prasadam_items(temple_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_prasadam_items(temple_id))


@router.get("/{temple_id}/prasadam/{item_id}", summary="Prasadam item detail")
async def get_prasadam_item(temple_id: UUID, item_id: UUID, svc: DarshanService = Depends(get_service)):
    return ResponseSchema.ok(data=await svc.get_prasadam_item(temple_id, item_id))


@router.post("/{temple_id}/prasadam/order", status_code=status.HTTP_201_CREATED, summary="Order prasadam")
async def order_prasadam(
    temple_id: UUID,
    req: PrasadamOrderRequest,
    svc: DarshanService = Depends(get_service),
):
    # TODO: replace with current_user.id once Auth module ready
    data = await svc.order_prasadam(
        temple_id=temple_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        req=req,
    )
    return ResponseSchema.ok(data=data, message="Prasadam order placed successfully.")