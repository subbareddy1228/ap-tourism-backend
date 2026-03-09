
"""
Booking Endpoints — M11
Base URL: /api/v1/bookings
25 endpoints: Cart (6), Create Bookings (9), My Bookings (10)

Team rules applied:
  - Auth:     user = Depends(get_current_user) on every endpoint
  - Response: {success: true, data: {...}, message: ''}
  - Errors:   HTTPException 400/401/403/404/409/422/500
  - Pagination: page + limit query params, response has data/total/page/pages
  - DB:       db: AsyncSession = Depends(get_db)
  - Logging:  request_id, user_id, endpoint, status_code, duration_ms
"""
import logging
import time
import uuid
from typing import Optional
from uuid import UUID

import json as json_mod
from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user, get_redis
from src.models.user import User
from src.schemas.booking import (
    # Cart
    CartItemAddRequest, CartItemUpdateRequest, CartResponse,
    # Create
    BookHotelRequest, BookVehicleRequest, BookDarshanRequest,
    BookPoojaRequest, BookPrasadamRequest, BookPackageRequest,
    BookGuideRequest, BookComboRequest, BookCustomRequest,
    # Responses
    BookingCreatedResponse, BookingDetailResponse, BookingListResponse,
    BookingListFilter, CancelBookingRequest, CancelBookingResponse,
    ModifyBookingRequest, ModifyBookingResponse,
    InvoiceResponse, TicketResponse,
    BookingTrackingResponse,                # [FIX-3] added — used by GET /{id}/tracking
)
from src.common.enums import BookingStatus, BookingType   # [FIX-1] from common not from model
from src.repositories import booking_repo
from src.services import booking_service



# ─────────────────────────────────────────────────────────────────────────────
# TYPED API RESPONSE WRAPPER
# Ensures OpenAPI/Swagger docs show correct response shape.
# Team rule: All APIs return {success, data, message}
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel
from typing import Any

class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = "Success"

router = APIRouter(prefix="/bookings", tags=["Bookings"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def success(data, message: str = "Success") -> dict:
    """
    Standard success response per team rule:
    All APIs return JSON: {success: true, data: {...}, message: ''}
    """
    return {"success": True, "data": data, "message": message}


def _log(request: Request, user_id, endpoint: str, status_code: int, start: float):
    """Log request_id, user_id, endpoint, status_code, duration_ms per team rule."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        f"request_id={request_id} user_id={user_id} "
        f"endpoint={endpoint} status_code={status_code} duration_ms={duration_ms}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CART ENDPOINTS  (6)
# Redis only — no DB writes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/cart", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_cart(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    GET /cart
    Get current cart items stored in Redis per user (cart:{user_id}) with TTL 1hr.
    """
    start = time.time()
    cart = await booking_service.get_cart(redis, current_user.id)
    _log(request, current_user.id, "GET /cart", 200, start)
    return success(cart.model_dump(), "Cart retrieved")


@router.post("/cart/add", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    request: Request,
    body: CartItemAddRequest,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    POST /cart/add
    Add item to cart: {entity_type, entity_id, date, guests, options}.
    Validate availability first.
    """
    start = time.time()
    cart = await booking_service.add_to_cart(redis, current_user.id, body)
    _log(request, current_user.id, "POST /cart/add", 201, start)
    return success(cart.model_dump(), "Item added to cart")


@router.put("/cart/{item_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def update_cart_item(
    request: Request,
    item_id: str,
    body: CartItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    PUT /cart/{item_id}
    Update cart item such as dates or guests count.
    """
    start = time.time()
    cart = await booking_service.update_cart_item(redis, current_user.id, item_id, body)
    _log(request, current_user.id, f"PUT /cart/{item_id}", 200, start)
    return success(cart.model_dump(), "Cart item updated")


@router.delete("/cart/clear", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def clear_cart(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    DELETE /cart/clear
    Clear entire cart.
    NOTE: This route must be defined BEFORE /cart/{item_id} to avoid
    FastAPI treating 'clear' as an item_id.
    """
    start = time.time()
    await booking_service.clear_cart(redis, current_user.id)
    _log(request, current_user.id, "DELETE /cart/clear", 200, start)
    return success(None, "Cart cleared")


@router.delete("/cart/{item_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def remove_cart_item(
    request: Request,
    item_id: str,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    DELETE /cart/{item_id}
    Remove item from cart.
    """
    start = time.time()
    cart = await booking_service.remove_cart_item(redis, current_user.id, item_id)
    _log(request, current_user.id, f"DELETE /cart/{item_id}", 200, start)
    return success(cart.model_dump(), "Item removed from cart")


@router.post("/cart/checkout", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /cart/checkout
    Convert cart to booking, lock slots, create booking with status PENDING
    and trigger payment.
    """
    start = time.time()
    result = await booking_service.checkout_cart(db, redis, current_user.id)
    _log(request, current_user.id, "POST /cart/checkout", 201, start)
    return success(result.model_dump(), "Booking created. Please complete payment.")


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKING ENDPOINTS  (9)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/hotel", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_hotel(
    request: Request,
    body: BookHotelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /hotel
    Book hotel room: {hotel_id, room_id, check_in, check_out, guests,
    special_requests}. Lock room 15 minutes in Redis.
    """
    start = time.time()
    result = await booking_service.book_hotel(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /hotel", 201, start)
    return success(result.model_dump(), "Hotel booked. Complete payment to confirm.")


@router.post("/vehicle", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_vehicle(
    request: Request,
    body: BookVehicleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /vehicle
    Book vehicle: {vehicle_id, pickup_date, pickup_address, drop_address,
    trip_type}.
    """
    start = time.time()
    result = await booking_service.book_vehicle(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /vehicle", 201, start)
    return success(result.model_dump(), "Vehicle booked. Complete payment to confirm.")


@router.post("/darshan", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_darshan(
    request: Request,
    body: BookDarshanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /darshan
    Book darshan slot with devotees list (name, age, id_proof).
    """
    start = time.time()
    result = await booking_service.book_darshan(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /darshan", 201, start)
    return success(result.model_dump(), "Darshan slot reserved. Complete payment to confirm.")


@router.post("/pooja", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_pooja(
    request: Request,
    body: BookPoojaRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /pooja
    Book pooja service with devotees list.
    """
    start = time.time()
    result = await booking_service.book_pooja(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /pooja", 201, start)
    return success(result.model_dump(), "Pooja slot reserved. Complete payment to confirm.")


@router.post("/prasadam", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_prasadam(
    request: Request,
    body: BookPrasadamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /prasadam
    Order prasadam for pickup: {temple_id, items[], pickup_date}.
    """
    start = time.time()
    result = await booking_service.book_prasadam(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /prasadam", 201, start)
    return success(result.model_dump(), "Prasadam order placed. Complete payment to confirm.")


@router.post("/package", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_package(
    request: Request,
    body: BookPackageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /package
    Book tour package with start_date, group_size, traveler_details.
    """
    start = time.time()
    result = await booking_service.book_package(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /package", 201, start)
    return success(result.model_dump(), "Package booked. Complete payment to confirm.")


@router.post("/guide", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_guide(
    request: Request,
    body: BookGuideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /guide
    Book guide with start_date, end_date, destination_id.
    """
    start = time.time()
    result = await booking_service.book_guide(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /guide", 201, start)
    return success(result.model_dump(), "Guide booked. Complete payment to confirm.")


@router.post("/combo", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_combo(
    request: Request,
    body: BookComboRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    POST /combo
    Combo booking for package + hotel + vehicle in one transaction.
    """
    start = time.time()
    result = await booking_service.book_combo(db, redis, current_user.id, body)
    _log(request, current_user.id, "POST /combo", 201, start)
    return success(result.model_dump(), "Combo booking created. Complete payment to confirm.")


@router.post("/custom", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def book_custom(
    request: Request,
    body: BookCustomRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /custom
    Custom trip request with destinations, dates, services_needed,
    group_size, budget.
    """
    start = time.time()
    result = await booking_service.book_custom(db, current_user.id, body)
    _log(request, current_user.id, "POST /custom", 201, start)
    return success(result.model_dump(), "Custom trip request submitted. We will contact you within 24 hours.")


# ─────────────────────────────────────────────────────────────────────────────
# MY BOOKINGS ENDPOINTS  (10)
# NOTE: All static paths (/upcoming, /past, /cancelled) must be defined
#       BEFORE the dynamic path (/{booking_id}) to avoid routing conflicts.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_my_bookings(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    booking_type: Optional[str]  = Query(None, alias="type"),
    date_from: Optional[str]     = Query(None),
    date_to: Optional[str]       = Query(None),
    page: int                    = Query(1, ge=1),
    limit: int                   = Query(20, ge=1, le=100),
    current_user: User           = Depends(get_current_user),
    db: AsyncSession             = Depends(get_db),
):
    """
    GET /
    All bookings for user with filters: status, type, date_range.
    Pagination: page + limit query params.
    """
    start = time.time()

    # Parse optional filters — validate inputs return HTTP 400 on bad values
    try:
        parsed_status = BookingStatus(status_filter) if status_filter else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status value: {status_filter}")
    try:
        parsed_type = BookingType(booking_type) if booking_type else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid booking type: {booking_type}")
    try:
        parsed_from = date_type.fromisoformat(date_from) if date_from else None
        parsed_to   = date_type.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    filters = BookingListFilter(
        status=parsed_status,
        booking_type=parsed_type,   # [FIX-2] was type= — field renamed to booking_type in schema
        date_from=parsed_from,
        date_to=parsed_to,
        page=page,
        per_page=limit,
    )

    result = await booking_service.get_my_bookings(db, current_user.id, filters)
    _log(request, current_user.id, "GET /bookings/", 200, start)
    return success(result.model_dump(), "Bookings retrieved")


@router.get("/upcoming", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_upcoming_bookings(
    request: Request,
    page: int  = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /upcoming
    Bookings with travel_date >= today and status CONFIRMED.
    """
    start = time.time()
    result = await booking_service.get_upcoming_bookings(db, current_user.id, page, limit)
    _log(request, current_user.id, "GET /bookings/upcoming", 200, start)
    return success(result.model_dump(), "Upcoming bookings retrieved")


@router.get("/past", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_past_bookings(
    request: Request,
    page: int  = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /past
    Completed bookings.
    """
    start = time.time()
    result = await booking_service.get_past_bookings(db, current_user.id, page, limit)
    _log(request, current_user.id, "GET /bookings/past", 200, start)
    return success(result.model_dump(), "Past bookings retrieved")


@router.get("/cancelled", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_cancelled_bookings(
    request: Request,
    page: int  = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /cancelled
    Cancelled bookings with refund status.
    """
    start = time.time()
    result = await booking_service.get_cancelled_bookings(db, current_user.id, page, limit)
    _log(request, current_user.id, "GET /bookings/cancelled", 200, start)
    return success(result.model_dump(), "Cancelled bookings retrieved")


@router.get("/{booking_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_booking_detail(
    request: Request,
    booking_id: UUID,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /{id}
    Full booking detail including items, payment, guide, driver, itinerary.
    """
    start = time.time()
    result = await booking_service.get_booking_detail(db, booking_id, current_user.id)
    _log(request, current_user.id, f"GET /bookings/{booking_id}", 200, start)
    return success(result.model_dump(), "Booking detail retrieved")


@router.get("/{booking_id}/invoice", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_invoice(
    request: Request,
    booking_id: UUID,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /{id}/invoice
    Download invoice PDF with GST breakdown and payment proof.
    """
    start = time.time()
    result = await booking_service.get_invoice(db, booking_id, current_user.id)
    _log(request, current_user.id, f"GET /bookings/{booking_id}/invoice", 200, start)
    return success(result.model_dump(), "Invoice retrieved")


@router.get("/{booking_id}/ticket", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_ticket(
    request: Request,
    booking_id: UUID,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    GET /{id}/ticket
    Download e-ticket with QR code for darshan or pooja.
    """
    start = time.time()
    result = await booking_service.get_ticket(db, booking_id, current_user.id)
    _log(request, current_user.id, f"GET /bookings/{booking_id}/ticket", 200, start)
    return success(result.model_dump(), "Ticket retrieved")


@router.get("/{booking_id}/tracking", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def get_tracking(
    request: Request,
    booking_id: UUID,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    GET /{id}/tracking
    Get live tracking data for active trip.
    Tracking data is stored in Redis by M18 (Tracking APIs):
    key: driver_loc:{booking_id}  TTL: 30s
    This endpoint reads that Redis key and returns current location.
    """
    start = time.time()

    # Verify booking ownership
    booking = await booking_repo.get_booking_for_modify(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Read tracking data from Redis (written by M18 Tracking APIs)
    tracking_key = f"driver_loc:{booking_id}"
    raw = await redis.get(tracking_key)

    if not raw:
        _log(request, current_user.id, f"GET /bookings/{booking_id}/tracking", 200, start)
        # [FIX-3] return typed schema object instead of raw dict — consistent with all other endpoints
        return success(
            BookingTrackingResponse(
                booking_id=booking_id,
                booking_number=booking.booking_number,
                status=booking.status,
                driver_name=None,
                driver_phone=None,
                vehicle_number=None,
                current_lat=None,
                current_lng=None,
                current_location=None,
                eta_minutes=None,
                last_updated=None,
            ).model_dump(),
            "No active tracking data available"
        )

    tracking_data = json_mod.loads(raw)
    _log(request, current_user.id, f"GET /bookings/{booking_id}/tracking", 200, start)
    # [FIX-3] parse Redis data into typed response
    return success(
        BookingTrackingResponse(
            booking_id=booking_id,
            booking_number=booking.booking_number,
            status=booking.status,
            driver_name=tracking_data.get("driver_name"),
            driver_phone=tracking_data.get("driver_phone"),
            vehicle_number=tracking_data.get("vehicle_number"),
            current_lat=tracking_data.get("lat"),
            current_lng=tracking_data.get("lng"),
            current_location=tracking_data.get("current_location"),
            eta_minutes=tracking_data.get("eta_minutes"),
            last_updated=tracking_data.get("recorded_at"),
        ).model_dump(),
        "Tracking data retrieved"
    )


@router.put("/{booking_id}/cancel", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def cancel_booking(
    request: Request,
    booking_id: UUID,
    body: CancelBookingRequest,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    PUT /{id}/cancel
    Cancel booking and apply refund policy:
    >48hrs = full refund, 24-48hrs = 50%, <24hrs = no refund.
    """
    start = time.time()
    result = await booking_service.cancel_booking(db, redis, booking_id, current_user.id, body)
    _log(request, current_user.id, f"PUT /bookings/{booking_id}/cancel", 200, start)
    return success(result.model_dump(), result.message)


@router.post("/{booking_id}/modify", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def modify_booking(
    request: Request,
    booking_id: UUID,
    body: ModifyBookingRequest,
    current_user: User       = Depends(get_current_user),
    db: AsyncSession         = Depends(get_db),
):
    """
    POST /{id}/modify
    Request modification such as date or guest change requiring admin approval.
    """
    start = time.time()
    result = await booking_service.modify_booking(db, booking_id, current_user.id, body)
    _log(request, current_user.id, f"POST /bookings/{booking_id}/modify", 200, start)
    return success(result.model_dump(), result.message)
