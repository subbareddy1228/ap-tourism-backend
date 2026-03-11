from datetime import date
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.deps.database import get_db
from src.services.darshan_service import DarshanService
from src.schemas.darshan import (
    DarshanTypeResponse, DarshanSlotResponse,
    DarshanCheckAvailabilityRequest, DarshanCheckAvailabilityResponse,
    DarshanBookRequest, DarshanBookingResponse,
    PoojaServiceResponse, PoojaSlotResponse,
    PoojaBookRequest, PoojaBookingResponse,
    PrasadamItemResponse, PrasadamOrderRequest, PrasadamOrderResponse,
)
from src.core.redis import get_redis

router = APIRouter(prefix="/temples", tags=["Darshan & Bookings"])

# Temporary dummy user_id until auth module is integrated
DUMMY_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_darshan_service(
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> DarshanService:
    return DarshanService(db=db, redis_client=redis)


# ═════════════════════════════════════════════
# DARSHAN TYPES
# ═════════════════════════════════════════════

@router.get("/{temple_id}/darshan-types", response_model=List[DarshanTypeResponse], summary="Get Darshan Types")
def get_darshan_types(
    temple_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_darshan_types(temple_id)


@router.get("/{temple_id}/darshan-types/{type_id}", response_model=DarshanTypeResponse, summary="Get Darshan Type Detail")
def get_darshan_type_detail(
    temple_id: UUID,
    type_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_darshan_type_detail(temple_id, type_id)


# ═════════════════════════════════════════════
# DARSHAN SLOTS
# ═════════════════════════════════════════════

@router.get("/{temple_id}/darshan-slots", response_model=List[DarshanSlotResponse], summary="Get Darshan Slots (next 30 days)")
def get_darshan_slots(
    temple_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_darshan_slots(temple_id)


@router.get("/{temple_id}/darshan-slots/{slot_date}", response_model=List[DarshanSlotResponse], summary="Get Darshan Slots by Date")
def get_darshan_slots_by_date(
    temple_id: UUID,
    slot_date: date,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_darshan_slots_by_date(temple_id, slot_date)


# ═════════════════════════════════════════════
# DARSHAN BOOKING
# ═════════════════════════════════════════════

@router.post("/{temple_id}/darshan/check-availability", response_model=DarshanCheckAvailabilityResponse, summary="Check Darshan Availability")
def check_darshan_availability(
    temple_id: UUID,
    req: DarshanCheckAvailabilityRequest,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.check_availability(temple_id, req)


@router.post("/{temple_id}/darshan/book", response_model=DarshanBookingResponse, status_code=status.HTTP_201_CREATED, summary="Book Darshan")
def book_darshan(
    temple_id: UUID,
    req: DarshanBookRequest,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.book_darshan(temple_id=temple_id, user_id=DUMMY_USER_ID, req=req)


@router.get("/{temple_id}/darshan/booking/{booking_id}", response_model=DarshanBookingResponse, summary="Get Darshan Booking")
def get_darshan_booking(
    temple_id: UUID,
    booking_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_darshan_booking(temple_id, booking_id)


# ═════════════════════════════════════════════
# POOJA SERVICES
# ═════════════════════════════════════════════

@router.get("/{temple_id}/pooja-services", response_model=List[PoojaServiceResponse], summary="Get Pooja Services")
def get_pooja_services(
    temple_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_pooja_services(temple_id)


@router.get("/{temple_id}/pooja-services/{service_id}", response_model=PoojaServiceResponse, summary="Get Pooja Service Detail")
def get_pooja_service_detail(
    temple_id: UUID,
    service_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_pooja_service_detail(temple_id, service_id)


@router.get("/{temple_id}/pooja-services/{service_id}/slots", response_model=List[PoojaSlotResponse], summary="Get Pooja Slots")
def get_pooja_slots(
    temple_id: UUID,
    service_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_pooja_slots(temple_id, service_id)


@router.post("/{temple_id}/pooja/book", response_model=PoojaBookingResponse, status_code=status.HTTP_201_CREATED, summary="Book Pooja")
def book_pooja(
    temple_id: UUID,
    req: PoojaBookRequest,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.book_pooja(
        temple_id=temple_id,
        service_id=req.pooja_service_id,
        user_id=DUMMY_USER_ID,
        req=req,
    )


# ═════════════════════════════════════════════
# PRASADAM
# ═════════════════════════════════════════════

@router.get("/{temple_id}/prasadam", response_model=List[PrasadamItemResponse], summary="Get Prasadam Items")
def get_prasadam_items(
    temple_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_prasadam_items(temple_id)


@router.get("/{temple_id}/prasadam/{item_id}", response_model=PrasadamItemResponse, summary="Get Prasadam Item Detail")
def get_prasadam_item(
    temple_id: UUID,
    item_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_prasadam_item(temple_id, item_id)


@router.post("/{temple_id}/prasadam/order", response_model=PrasadamOrderResponse, status_code=status.HTTP_201_CREATED, summary="Order Prasadam")
def order_prasadam(
    temple_id: UUID,
    req: PrasadamOrderRequest,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.order_prasadam(temple_id=temple_id, user_id=DUMMY_USER_ID, req=req)


@router.get("/{temple_id}/prasadam/orders", response_model=List[PrasadamOrderResponse], summary="Get My Prasadam Orders")
def get_my_prasadam_orders(
    temple_id: UUID,
    service: DarshanService = Depends(get_darshan_service),
):
    return service.get_my_prasadam_orders(temple_id, DUMMY_USER_ID)