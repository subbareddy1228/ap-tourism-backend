"""
Booking Service — M11
Business logic for all 25 booking endpoints.
Depends on: Auth (M1), Hotels (M5), Vehicles (M6), Temples/Darshan (M7),
            Packages (M9), Guides (M10), Payments (M12)
"""
import json
import math
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import BookingStatus, BookingType, PaymentStatus
from src.repositories import booking_repo
from src.core.exceptions import (
    BadRequestException, ConflictException, ForbiddenException,
    InternalServerException, NotFoundException,
)
from src.schemas.booking import (
    CartItemAddRequest, CartItemUpdateRequest, CartResponse, CartItemResponse,
    BookHotelRequest, BookVehicleRequest, BookDarshanRequest, BookPoojaRequest,
    BookPrasadamRequest, BookPackageRequest, BookGuideRequest,
    BookComboRequest, BookCustomRequest,
    BookingCreatedResponse, BookingDetailResponse, BookingListResponse,
    BookingListItem, BookingListFilter,
    CancelBookingRequest, CancelBookingResponse,
    ModifyBookingRequest, ModifyBookingResponse,
    InvoiceResponse, InvoiceLineItem, TicketResponse,
    PaymentInfoSchema,
)

logger = logging.getLogger(__name__)

# ── Tax & Fee Constants ──────────────────────────────────────────────────────
CGST_RATE       = Decimal("0.09")
SGST_RATE       = Decimal("0.09")
CONVENIENCE_FEE = Decimal("29.00")
CART_TTL        = 3600   # 1 hour

# ── Stub Prices (replaced when upstream modules are ready) ───────────────────
_STUB = {
    "hotel_room_rate": Decimal("2000.00"),
    "vehicle_rate_km": Decimal("16.00"),
    "vehicle_est_km":  Decimal("100.00"),
    "darshan_pp":      Decimal("300.00"),
    "pooja":           Decimal("500.00"),
    "prasadam_item":   Decimal("150.00"),
    "package":         Decimal("15000.00"),
    "guide_day":       Decimal("1500.00"),
    "combo_vehicle":   Decimal("1600.00"),
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_totals(
    subtotal: Decimal,
    discount_amount: Decimal = Decimal("0"),
    apply_convenience_fee: bool = True,
) -> dict:
    """GST = CGST 9% + SGST 9% = 18% on (subtotal − discount). Called before every booking create."""
    taxable  = subtotal - discount_amount
    cgst     = (taxable * CGST_RATE).quantize(Decimal("0.01"))
    sgst     = (taxable * SGST_RATE).quantize(Decimal("0.01"))
    conv_fee = CONVENIENCE_FEE if apply_convenience_fee else Decimal("0")
    return {
        "subtotal":         subtotal,
        "discount_amount":  discount_amount,
        "tax_amount":       cgst + sgst,
        "convenience_fee":  conv_fee,
        "total_amount":     taxable + cgst + sgst + conv_fee,
    }


def _calculate_refund(booking) -> tuple[Decimal, int]:
    """SOW refund policy: >48 h → 100%, 24–48 h → 50%, <24 h → 0%."""
    if not booking.start_date:
        return Decimal("0"), 0
    hours = (booking.start_date - datetime.now(timezone.utc).date()).total_seconds() / 3600
    pct   = 100 if hours > 48 else (50 if hours >= 24 else 0)
    return (booking.total_amount * Decimal(pct) / 100).quantize(Decimal("0.01")), pct


async def _apply_coupon(coupon_code: Optional[str], subtotal: Decimal) -> Decimal:
    """Stub — returns 0 discount until M16 (Coupon APIs) is integrated."""
    # TODO: call coupon_service.validate_coupon(coupon_code, subtotal) when M16 ready
    return Decimal("0")


def _booking_response(booking, btype: BookingType, totals: dict, message: str) -> BookingCreatedResponse:
    """Single factory for BookingCreatedResponse — eliminates repeated construction."""
    return BookingCreatedResponse(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        booking_type=btype,
        status=BookingStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        total_amount=totals["total_amount"],
        payment_required=True,
        message=message,
    )


@asynccontextmanager
async def _locked_booking(redis, db: AsyncSession, slots: list[tuple[str, str]], user_id: UUID):
    """
    Async context manager: acquires Redis slot locks, yields, releases on exception.
    Rolls back DB on failure. Keeps try/except/release logic DRY across all book_* methods.

    Usage:
        async with _locked_booking(redis, db, [("hotel_room", room_id)], user_id):
            ...booking logic...
    """
    acquired = []
    try:
        for entity_type, entity_id in slots:
            locked = await booking_repo.lock_booking_slot(redis, entity_type, entity_id, str(user_id))
            if not locked:
                raise ConflictException(f"{entity_type.replace('_', ' ').title()} is no longer available.")
            acquired.append((entity_type, entity_id))
        yield
    except HTTPException:
        for t, i in acquired:
            await booking_repo.release_booking_slot(redis, t, i)
        raise
    except Exception as e:
        for t, i in acquired:
            await booking_repo.release_booking_slot(redis, t, i)
        await db.rollback()
        logger.error("Booking failed user=%s error=%s", user_id, e)
        raise InternalServerException("Booking failed. Please try again.")


# ─────────────────────────────────────────────────────────────────────────────
# CART  (Redis only — no DB writes)
# Key: cart:{user_id}   TTL: 1 hr
# ─────────────────────────────────────────────────────────────────────────────

async def _load_cart(redis, user_id: UUID) -> tuple[str, dict]:
    cart_key  = f"cart:{user_id}"
    raw       = await redis.get(cart_key)
    cart_data = json.loads(raw) if raw else {"items": []}
    return cart_key, cart_data


async def _save_cart(redis, cart_key: str, cart_data: dict) -> None:
    await redis.set(cart_key, json.dumps(cart_data), ex=CART_TTL)


async def _build_cart_response(redis, user_id: UUID) -> CartResponse:
    cart_key, cart_data = await _load_cart(redis, user_id)
    ttl   = await redis.ttl(cart_key)
    items = [
        CartItemResponse(
            item_id=i["item_id"],
            entity_type=i["entity_type"],
            entity_id=UUID(i["entity_id"]),
            travel_date=date.fromisoformat(i["date"]),
            guests=i["guests"],
            options=i.get("options"),
            added_at=datetime.fromisoformat(i["added_at"]),
        )
        for i in cart_data.get("items", [])
    ]
    return CartResponse(
        user_id=user_id,
        items=items,
        item_count=len(items),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 0)),
    )


async def get_cart(redis, user_id: UUID) -> CartResponse:
    """GET /cart — Current cart from Redis."""
    return await _build_cart_response(redis, user_id)


async def add_to_cart(redis, user_id: UUID, req: CartItemAddRequest) -> CartResponse:
    """POST /cart/add — Add item. TODO: validate availability per entity type when modules ready."""
    cart_key, cart_data = await _load_cart(redis, user_id)
    cart_data["items"].append({
        "item_id":     str(uuid.uuid4()),
        "entity_type": req.entity_type.value,
        "entity_id":   str(req.entity_id),
        "date":        req.travel_date.isoformat(),
        "guests":      req.guests,
        "options":     req.options,
        "added_at":    datetime.now(timezone.utc).isoformat(),
    })
    await _save_cart(redis, cart_key, cart_data)
    logger.info("endpoint=POST /cart/add user=%s entity=%s id=%s", user_id, req.entity_type, req.entity_id)
    return await _build_cart_response(redis, user_id)


async def update_cart_item(redis, user_id: UUID, item_id: str, req: CartItemUpdateRequest) -> CartResponse:
    """PUT /cart/{item_id} — Update dates or guest count."""
    cart_key, cart_data = await _load_cart(redis, user_id)
    if not cart_data["items"]:
        raise NotFoundException("Cart is empty")

    for item in cart_data["items"]:
        if item["item_id"] == item_id:
            if req.date:    item["date"]    = req.date.isoformat()
            if req.guests:  item["guests"]  = req.guests
            if req.options: item["options"] = req.options
            break
    else:
        raise NotFoundException("Cart item not found")

    await _save_cart(redis, cart_key, cart_data)
    return await _build_cart_response(redis, user_id)


async def remove_cart_item(redis, user_id: UUID, item_id: str) -> CartResponse:
    """DELETE /cart/{item_id} — Remove one item."""
    cart_key, cart_data = await _load_cart(redis, user_id)
    before = len(cart_data["items"])
    cart_data["items"] = [i for i in cart_data["items"] if i["item_id"] != item_id]
    if len(cart_data["items"]) == before:
        raise NotFoundException("Cart item not found")
    await _save_cart(redis, cart_key, cart_data)
    return await _build_cart_response(redis, user_id)


async def clear_cart(redis, user_id: UUID) -> None:
    """DELETE /cart/clear — Wipe entire cart."""
    await redis.delete(f"cart:{user_id}")
    logger.info("endpoint=DELETE /cart/clear user=%s", user_id)


async def checkout_cart(db: AsyncSession, redis, user_id: UUID) -> BookingCreatedResponse:
    """
    POST /cart/checkout — Convert cart → booking (status PENDING), trigger payment.
    Locks all slots, creates master booking, clears cart.
    TODO: real per-item pricing when entity modules (M5,M6,M7,M9,M10) are ready.
    """
    cart_key, cart_data = await _load_cart(redis, user_id)
    items = cart_data.get("items", [])
    if not items:
        raise BadRequestException("Cart is empty")

    for item in items:
        if not await booking_repo.lock_booking_slot(redis, item["entity_type"], item["entity_id"], str(user_id)):
            raise ConflictException(f"{item['entity_type']} {item['entity_id']} is no longer available")

    entity_types = {i["entity_type"] for i in items}
    btype        = BookingType.COMBO if len(entity_types) > 1 else BookingType(items[0]["entity_type"])
    # TODO: real per-item subtotal when M5/M6/M7/M9/M10 pricing is ready
    subtotal = Decimal("1000.00") * len(items)
    totals   = _calculate_totals(subtotal)

    booking = await booking_repo.create_booking(db, {"user_id": user_id, "booking_type": btype, **totals})
    await db.commit()
    await clear_cart(redis, user_id)

    logger.info("endpoint=POST /cart/checkout user=%s booking=%s", user_id, booking.booking_number)
    return BookingCreatedResponse(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        booking_type=btype,
        status=BookingStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        total_amount=booking.total_amount,
        payment_required=True,
        message="Booking created. Please complete payment to confirm.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

async def book_hotel(db: AsyncSession, redis, user_id: UUID, req: BookHotelRequest) -> BookingCreatedResponse:
    """POST /hotel — Lock room → create master + hotel sub-booking → commit."""
    async with _locked_booking(redis, db, [("hotel_room", str(req.room_id))], user_id):
        nights = (req.check_out - req.check_in).days
        if nights <= 0:
            raise BadRequestException("check_out must be after check_in")

        # TODO: fetch room_rate from hotel_service when M5 ready
        rate     = _STUB["hotel_room_rate"]
        subtotal = rate * nights * req.rooms_count
        totals   = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.HOTEL,
            "start_date": req.check_in, "end_date": req.check_out,
            "coupon_code": req.coupon_code, "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_hotel_booking(db, booking.id, {
            "hotel_id": req.hotel_id, "room_id": req.room_id,
            "check_in": req.check_in, "check_out": req.check_out,
            "rooms_count": req.rooms_count, "adults": req.adults, "children": req.children,
            "room_rate_per_night": rate,
            "total_room_charge": rate * nights * req.rooms_count,
        })
        if req.travelers:
            await booking_repo.create_booking_travelers(db, booking.id, [t.model_dump() for t in req.travelers])
        if req.addons:
            await booking_repo.create_booking_addons(db, booking.id, [a.model_dump() for a in req.addons])

        await db.commit()
        logger.info("endpoint=POST /hotel user=%s booking=%s hotel=%s", user_id, booking.booking_number, req.hotel_id)
        return _booking_response(booking, BookingType.HOTEL, totals, "Hotel booked. Complete payment to confirm.")


async def book_vehicle(db: AsyncSession, redis, user_id: UUID, req: BookVehicleRequest) -> BookingCreatedResponse:
    """POST /vehicle — Lock vehicle → create master + vehicle sub-booking → commit."""
    async with _locked_booking(redis, db, [("vehicle", str(req.vehicle_id))], user_id):
        # TODO: fetch rate_per_km from vehicle_service when M6 ready
        subtotal = _STUB["vehicle_rate_km"] * _STUB["vehicle_est_km"]
        totals   = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.VEHICLE,
            "start_date": req.pickup_date, "coupon_code": req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_vehicle_booking(db, booking.id, {
            "vehicle_id": req.vehicle_id, "trip_type": req.trip_type,
            "pickup_address": req.pickup_address, "pickup_lat": req.pickup_lat, "pickup_lng": req.pickup_lng,
            "drop_address": req.drop_address, "drop_lat": req.drop_lat, "drop_lng": req.drop_lng,
            "pickup_datetime": req.pickup_datetime, "return_datetime": req.return_datetime,
            "estimated_km": _STUB["vehicle_est_km"], "rate_per_km": _STUB["vehicle_rate_km"],
            "total_charge": subtotal,
        })
        if req.travelers:
            await booking_repo.create_booking_travelers(db, booking.id, [t.model_dump() for t in req.travelers])
        if req.addons:
            await booking_repo.create_booking_addons(db, booking.id, [a.model_dump() for a in req.addons])

        await db.commit()
        logger.info("endpoint=POST /vehicle user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.VEHICLE, totals, "Vehicle booked. Complete payment to confirm.")


async def book_darshan(db: AsyncSession, redis, user_id: UUID, req: BookDarshanRequest) -> BookingCreatedResponse:
    """POST /darshan — Verify slot not locked → lock → create → commit."""
    if await booking_repo.check_slot_locked(redis, "darshan_slot", str(req.darshan_slot_id)):
        raise ConflictException("Darshan slot is no longer available.")

    async with _locked_booking(redis, db, [("darshan_slot", str(req.darshan_slot_id))], user_id):
        # TODO: fetch price_per_person from temple_service when M7 ready
        ppp      = _STUB["darshan_pp"]
        subtotal = ppp * len(req.devotees)
        totals   = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.DARSHAN,
            "start_date": req.darshan_date, "coupon_code": req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_darshan_booking(db, booking.id, {
            "temple_id": req.temple_id, "darshan_slot_id": req.darshan_slot_id,
            "darshan_type_id": req.darshan_type_id, "darshan_date": req.darshan_date,
            "darshan_time": req.darshan_time, "num_persons": len(req.devotees),
            "price_per_person": ppp, "total_price": subtotal,
            "devotee_details": [d.model_dump() for d in req.devotees],
        })
        await booking_repo.create_booking_travelers(db, booking.id, [
            {"name": d.name, "age": d.age, "id_proof_type": d.id_proof_type,
             "id_proof_number": d.id_proof_number, "is_primary": i == 0}
            for i, d in enumerate(req.devotees)
        ])
        await db.commit()
        logger.info("endpoint=POST /darshan user=%s booking=%s temple=%s", user_id, booking.booking_number, req.temple_id)
        return _booking_response(booking, BookingType.DARSHAN, totals,
                                 "Darshan slot reserved for 15 minutes. Complete payment to confirm.")


async def book_pooja(db: AsyncSession, redis, user_id: UUID, req: BookPoojaRequest) -> BookingCreatedResponse:
    """POST /pooja — Lock pooja slot → create → commit."""
    async with _locked_booking(redis, db, [("pooja_service", str(req.pooja_service_id))], user_id):
        # TODO: fetch price from pooja_service when M7 ready
        totals = _calculate_totals(_STUB["pooja"], await _apply_coupon(req.coupon_code, _STUB["pooja"]))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.POOJA,
            "start_date": req.pooja_date, "coupon_code": req.coupon_code,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_pooja_booking(db, booking.id, {
            "pooja_service_id": req.pooja_service_id, "pooja_date": req.pooja_date,
            "pooja_time": req.pooja_time, "devotee_names": req.devotee_names,
            "gothram": req.gothram, "nakshatra": req.nakshatra,
            "special_instructions": req.special_instructions, "price": _STUB["pooja"],
        })
        await db.commit()
        logger.info("endpoint=POST /pooja user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.POOJA, totals, "Pooja slot reserved. Complete payment to confirm.")


async def book_prasadam(db: AsyncSession, redis, user_id: UUID, req: BookPrasadamRequest) -> BookingCreatedResponse:
    """POST /prasadam — No slot lock needed. Create one prasadam_order row per item."""
    try:
        # TODO: fetch unit prices from M7 when ready
        unit = _STUB["prasadam_item"]
        subtotal = sum(unit * item.quantity for item in req.items)
        totals   = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal),
                                     apply_convenience_fee=False)

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.PRASADAM,
            "start_date": req.pickup_date, "coupon_code": req.coupon_code,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        for item in req.items:
            await booking_repo.create_prasadam_order(db, booking.id, {
                "prasadam_item_id": item.prasadam_item_id, "quantity": item.quantity,
                "unit_price": unit, "total_price": unit * item.quantity,
                "delivery_address_id": req.delivery_address_id,
            })
        await db.commit()
        logger.info("endpoint=POST /prasadam user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.PRASADAM, totals, "Prasadam order placed. Complete payment to confirm.")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Prasadam order failed user=%s error=%s", user_id, e)
        raise InternalServerException("Order failed. Please try again.")


async def book_package(db: AsyncSession, redis, user_id: UUID, req: BookPackageRequest) -> BookingCreatedResponse:
    """POST /package — Lock package slot → create master + package sub-booking → commit."""
    async with _locked_booking(redis, db, [("package", str(req.package_id))], user_id):
        # TODO: fetch package_price from package_service when M9 ready
        addon_charges = sum(a.total_price for a in req.addons) if req.addons else Decimal("0")
        subtotal      = _STUB["package"] * (req.num_adults + req.num_children) + addon_charges
        totals        = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.PACKAGE,
            "start_date": req.start_date, "end_date": req.end_date,
            "coupon_code": req.coupon_code, "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_package_booking(db, booking.id, {
            "package_id": req.package_id, "start_date": req.start_date, "end_date": req.end_date,
            "num_adults": req.num_adults, "num_children": req.num_children,
            "package_price": _STUB["package"], "addon_charges": addon_charges,
            "total_price": subtotal, "customizations": req.customizations,
        })
        if req.traveler_details:
            await booking_repo.create_booking_travelers(db, booking.id, [t.model_dump() for t in req.traveler_details])
        if req.addons:
            await booking_repo.create_booking_addons(db, booking.id, [a.model_dump() for a in req.addons])

        await db.commit()
        logger.info("endpoint=POST /package user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.PACKAGE, totals, "Package booked. Complete payment to confirm.")


async def book_guide(db: AsyncSession, redis, user_id: UUID, req: BookGuideRequest) -> BookingCreatedResponse:
    """POST /guide — Lock guide → create master + guide sub-booking → commit."""
    async with _locked_booking(redis, db, [("guide", str(req.guide_id))], user_id):
        num_days = (req.end_date - req.start_date).days + 1
        # TODO: fetch rate from guide_service when M10 ready
        charge   = _STUB["guide_day"] * num_days
        totals   = _calculate_totals(charge, await _apply_coupon(req.coupon_code, charge))

        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.GUIDE,
            "start_date": req.start_date, "end_date": req.end_date,
            "coupon_code": req.coupon_code, "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })
        await booking_repo.create_guide_booking(db, booking.id, {
            "guide_id": req.guide_id, "start_date": req.start_date, "end_date": req.end_date,
            "num_days": num_days, "rate": _STUB["guide_day"], "total_charge": charge,
            "meeting_point": req.meeting_point,
            "locations_to_cover": [str(lid) for lid in req.locations_to_cover] if req.locations_to_cover else None,
        })
        await db.commit()
        logger.info("endpoint=POST /guide user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.GUIDE, totals, "Guide booked. Complete payment to confirm.")


async def book_combo(db: AsyncSession, redis, user_id: UUID, req: BookComboRequest) -> BookingCreatedResponse:
    """
    POST /combo — Package + hotel + vehicle in one atomic transaction.
    Locks all slots first, then creates master + each sub-booking.
    """
    if not any([req.package, req.hotel, req.vehicle]):
        raise BadRequestException("At least one of package, hotel, or vehicle is required.")

    slots = []
    if req.hotel:   slots.append(("hotel_room", str(req.hotel.room_id)))
    if req.vehicle: slots.append(("vehicle",    str(req.vehicle.vehicle_id)))
    if req.package: slots.append(("package",    str(req.package.package_id)))

    async with _locked_booking(redis, db, slots, user_id):
        subtotal   = Decimal("0")
        start_date = None

        if req.hotel:
            nights      = (req.hotel.check_out - req.hotel.check_in).days
            subtotal   += _STUB["hotel_room_rate"] * nights
            start_date  = req.hotel.check_in
        if req.vehicle:
            subtotal   += _STUB["combo_vehicle"]
        if req.package:
            subtotal   += _STUB["package"]
            start_date  = start_date or req.package.start_date

        totals  = _calculate_totals(subtotal, await _apply_coupon(req.coupon_code, subtotal))
        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.COMBO,
            "start_date": start_date, "coupon_code": req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        if req.hotel:
            nights    = (req.hotel.check_out - req.hotel.check_in).days
            room_rate = _STUB["hotel_room_rate"]
            await booking_repo.create_hotel_booking(db, booking.id, {
                "hotel_id": req.hotel.hotel_id, "room_id": req.hotel.room_id,
                "check_in": req.hotel.check_in, "check_out": req.hotel.check_out,
                "rooms_count": req.hotel.rooms_count, "adults": req.hotel.adults, "children": req.hotel.children,
                "room_rate_per_night": room_rate, "total_room_charge": room_rate * nights,
            })
        if req.vehicle:
            await booking_repo.create_vehicle_booking(db, booking.id, {
                "vehicle_id": req.vehicle.vehicle_id, "trip_type": req.vehicle.trip_type,
                "pickup_address": req.vehicle.pickup_address, "pickup_lat": req.vehicle.pickup_lat,
                "pickup_lng": req.vehicle.pickup_lng, "drop_address": req.vehicle.drop_address,
                "drop_lat": req.vehicle.drop_lat, "drop_lng": req.vehicle.drop_lng,
                "pickup_datetime": req.vehicle.pickup_datetime, "return_datetime": req.vehicle.return_datetime,
                "rate_per_km": _STUB["vehicle_rate_km"], "total_charge": _STUB["combo_vehicle"],
            })
        if req.package:
            await booking_repo.create_package_booking(db, booking.id, {
                "package_id": req.package.package_id,
                "start_date": req.package.start_date, "end_date": req.package.end_date,
                "num_adults": req.package.num_adults, "num_children": req.package.num_children,
                "package_price": _STUB["package"], "addon_charges": Decimal("0"),
                "total_price": _STUB["package"], "customizations": req.package.customizations,
            })

        await db.commit()
        logger.info("endpoint=POST /combo user=%s booking=%s", user_id, booking.booking_number)
        return _booking_response(booking, BookingType.COMBO, totals, "Combo booking created. Complete payment to confirm.")


async def book_custom(db: AsyncSession, user_id: UUID, req: BookCustomRequest) -> BookingCreatedResponse:
    """POST /custom — Custom trip request. No slot locking; no upfront price."""
    try:
        totals  = _calculate_totals(Decimal("0"), Decimal("0"), apply_convenience_fee=False)
        booking = await booking_repo.create_booking(db, {
            "user_id": user_id, "booking_type": BookingType.CUSTOM,
            "start_date": req.start_date, "end_date": req.end_date,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            "custom_trip_details": {
                "destinations":    [str(d) for d in req.destinations],
                "services_needed": req.services_needed,
                "group_size":      req.group_size,
                "budget":          str(req.budget) if req.budget else None,
            },
            **totals,
        })
        if req.traveler_details:
            await booking_repo.create_booking_travelers(db, booking.id, [t.model_dump() for t in req.traveler_details])
        await db.commit()
        logger.info("endpoint=POST /custom user=%s booking=%s", user_id, booking.booking_number)
        return BookingCreatedResponse(
            booking_id=booking.id, booking_number=booking.booking_number,
            booking_type=BookingType.CUSTOM, status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING, total_amount=Decimal("0"),
            payment_required=False,
            message="Custom trip request submitted. Our team will contact you within 24 hours.",
        )
    except Exception as e:
        await db.rollback()
        logger.error("Custom booking failed user=%s error=%s", user_id, e)
        raise InternalServerException("Request failed. Please try again.")


# ─────────────────────────────────────────────────────────────────────────────
# MY BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

def _build_list_response(items, total: int, page: int, per_page: int) -> BookingListResponse:
    return BookingListResponse(
        items=[
            BookingListItem(
                id=b.id, booking_number=b.booking_number, booking_type=b.booking_type,
                status=b.status, payment_status=b.payment_status,
                total_amount=b.total_amount, paid_amount=b.total_amount,
                start_date=b.start_date, end_date=b.end_date, created_at=b.created_at,
                cancellation_reason=b.cancellation_reason, cancelled_at=b.cancelled_at,
            )
            for b in items
        ],
        total=total, page=page, per_page=per_page,
        total_pages=math.ceil(total / per_page) if total else 0,
    )


async def get_my_bookings(db: AsyncSession, user_id: UUID, filters: BookingListFilter) -> BookingListResponse:
    """GET / — All user bookings with optional status/type/date filters."""
    items, total = await booking_repo.get_bookings_by_user(
        db, user_id=user_id, status=filters.status, booking_type=filters.booking_type,
        date_from=filters.date_from, date_to=filters.date_to,
        page=filters.page, per_page=filters.per_page,
    )
    return _build_list_response(items, total, filters.page, filters.per_page)


async def get_upcoming_bookings(db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10) -> BookingListResponse:
    """GET /upcoming — start_date >= today AND status = CONFIRMED."""
    items, total = await booking_repo.get_upcoming_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


async def get_past_bookings(db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10) -> BookingListResponse:
    """GET /past — Completed bookings."""
    items, total = await booking_repo.get_past_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


async def get_cancelled_bookings(db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10) -> BookingListResponse:
    """GET /cancelled — Cancelled bookings with refund status."""
    items, total = await booking_repo.get_cancelled_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


async def get_booking_detail(db: AsyncSession, booking_id: UUID, user_id: UUID) -> BookingDetailResponse:
    """GET /{id} — Full booking detail: items, payment, guide, driver, itinerary."""
    booking = await booking_repo.get_booking_by_id(db, booking_id)
    if not booking:               raise NotFoundException("Booking not found")
    if booking.user_id != user_id: raise ForbiddenException("Access denied")

    payment_info = None
    txn = await booking_repo.get_booking_with_transaction(db, booking_id)
    if txn and txn.get("transaction_id"):
        payment_info = PaymentInfoSchema(
            transaction_id=txn["transaction_id"],
            razorpay_order_id=txn.get("razorpay_order_id"),
            razorpay_payment_id=txn.get("razorpay_payment_id"),
            payment_method=txn.get("payment_method"),
            paid_at=txn.get("paid_at"),
        )

    return BookingDetailResponse(
        id=booking.id, booking_number=booking.booking_number,
        booking_type=booking.booking_type, status=booking.status,
        payment_status=booking.payment_status, booking_date=booking.booking_date,
        start_date=booking.start_date, end_date=booking.end_date,
        subtotal=booking.subtotal, discount_amount=booking.discount_amount,
        tax_amount=booking.tax_amount, convenience_fee=booking.convenience_fee,
        total_amount=booking.total_amount, paid_amount=booking.total_amount,
        coupon_code=booking.coupon_code, special_requests=booking.special_requests,
        contact_details=booking.contact_details,
        cancellation_reason=booking.cancellation_reason, cancelled_at=booking.cancelled_at,
        confirmed_at=booking.confirmed_at, completed_at=booking.completed_at,
        created_at=booking.created_at, updated_at=booking.updated_at,
        payment_info=payment_info,
        hotel_booking=booking.hotel_booking, vehicle_booking=booking.vehicle_booking,
        darshan_booking=booking.darshan_booking, package_booking=booking.package_booking,
        guide_booking=booking.guide_booking, pooja_booking=booking.pooja_booking,
        prasadam_orders=booking.prasadam_orders or [],
        travelers=booking.travelers or [], addons=booking.addons or [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE & TICKET
# ─────────────────────────────────────────────────────────────────────────────

async def get_invoice(db: AsyncSession, booking_id: UUID, user_id: UUID) -> InvoiceResponse:
    """
    GET /{id}/invoice — GST-compliant invoice with line items.
    PDF generated async by booking_tasks.generate_invoice_pdf.
    """
    booking = await booking_repo.get_invoice_data(db, booking_id)
    if not booking:                raise NotFoundException("Booking not found")
    if booking.user_id != user_id: raise ForbiddenException("Access denied")

    line_items: list[InvoiceLineItem] = []

    if booking.hotel_booking:
        hb = booking.hotel_booking
        nights = (hb.check_out_date - hb.check_in_date).days
        line_items.append(InvoiceLineItem(
            description=f"Hotel Room × {hb.rooms_count} room(s) × {nights} night(s)",
            quantity=hb.rooms_count * nights, unit_price=hb.room_rate_per_night, total=hb.total_room_charge,
        ))
    if booking.vehicle_booking:
        vb = booking.vehicle_booking
        line_items.append(InvoiceLineItem(
            description=f"Vehicle — {vb.trip_type.value}", quantity=1,
            unit_price=vb.total_charge, total=vb.total_charge,
        ))
    if booking.darshan_booking:
        db_ = booking.darshan_booking
        line_items.append(InvoiceLineItem(
            description=f"Darshan × {db_.num_persons} person(s)",
            quantity=db_.num_persons, unit_price=db_.price_per_person, total=db_.total_price,
        ))
    if booking.package_booking:
        pb = booking.package_booking
        line_items.append(InvoiceLineItem(
            description=f"Tour Package × {pb.num_adults + pb.num_children} person(s)",
            quantity=pb.num_adults + pb.num_children, unit_price=pb.package_price, total=pb.total_price,
        ))
    if booking.guide_booking:
        gb = booking.guide_booking
        line_items.append(InvoiceLineItem(
            description=f"Guide Service × {gb.num_days or 1} day(s)",
            quantity=gb.num_days or 1, unit_price=gb.rate, total=gb.total_charge,
        ))
    if booking.pooja_booking:
        pb = booking.pooja_booking
        line_items.append(InvoiceLineItem(description="Pooja Service", quantity=1, unit_price=pb.price, total=pb.price))

    line_items += [
        InvoiceLineItem(
            description=f"Prasadam × {po.quantity}",
            quantity=po.quantity, unit_price=po.unit_price, total=po.total_price,
        )
        for po in (booking.prasadam_orders or [])
    ]
    line_items += [
        InvoiceLineItem(
            description=addon.addon_name,
            quantity=addon.quantity, unit_price=addon.unit_price, total=addon.total_price,
        )
        for addon in (booking.addons or [])
    ]

    taxable = booking.subtotal - booking.discount_amount
    cgst    = (taxable * CGST_RATE).quantize(Decimal("0.01"))
    sgst    = (taxable * SGST_RATE).quantize(Decimal("0.01"))
    txn     = await booking_repo.get_booking_with_transaction(db, booking_id)
    contact = booking.contact_details or {}

    return InvoiceResponse(
        invoice_number=f"INV-{booking.booking_number}",
        booking_number=booking.booking_number, booking_type=booking.booking_type,
        customer_name=contact.get("name", ""), customer_phone=contact.get("phone", ""),
        customer_email=contact.get("email"), invoice_date=booking.booking_date,
        line_items=line_items, subtotal=booking.subtotal, discount=booking.discount_amount,
        cgst=cgst, sgst=sgst, total_tax=booking.tax_amount,
        convenience_fee=booking.convenience_fee, total_amount=booking.total_amount,
        paid_amount=booking.total_amount,
        payment_method=txn.get("payment_method") if txn else None,
        payment_proof=txn.get("razorpay_payment_id") if txn else None,
        pdf_url=None,   # Generated async by booking_tasks.generate_invoice_pdf
    )


async def get_ticket(db: AsyncSession, booking_id: UUID, user_id: UUID) -> TicketResponse:
    """GET /{id}/ticket — E-ticket with QR code for darshan or pooja bookings only."""
    booking = await booking_repo.get_darshan_ticket_data(db, booking_id)
    if not booking:
        raise NotFoundException("Ticket not found. Only darshan and pooja bookings have tickets.")
    if booking.user_id != user_id:     raise ForbiddenException("Access denied")
    if booking.status != BookingStatus.CONFIRMED:
        raise BadRequestException("Ticket available only after payment confirmation.")

    if booking.darshan_booking:
        db_ = booking.darshan_booking
        return TicketResponse(
            ticket_number=db_.ticket_number or booking.booking_number,
            booking_number=booking.booking_number, booking_type=booking.booking_type,
            temple_name="",           # TODO: fetch from temple_service M7
            darshan_type=str(db_.darshan_type_id), pooja_name=None,
            visit_date=db_.darshan_date, visit_time=db_.darshan_time,
            num_persons=db_.num_persons,
            devotee_names=[t.name for t in (booking.travelers or [])],
            qr_code_url="",           # Generated async by booking_tasks.generate_qr_code
            pdf_url=None,
            instructions="Please carry original ID proof for all devotees.",
        )

    if booking.pooja_booking:
        pb = booking.pooja_booking
        return TicketResponse(
            ticket_number=booking.booking_number, booking_number=booking.booking_number,
            booking_type=booking.booking_type,
            temple_name="",           # TODO: fetch from temple_service M7
            darshan_type=None, pooja_name=str(pb.pooja_service_id),
            visit_date=pb.pooja_date, visit_time=pb.pooja_time,
            num_persons=len(pb.devotee_names) if pb.devotee_names else 1,
            devotee_names=pb.devotee_names or [],
            qr_code_url="",           # Generated async by booking_tasks.generate_qr_code
            pdf_url=None,
            instructions="Please arrive 30 minutes before pooja time.",
        )

    raise BadRequestException("Ticket not available for this booking type.")


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL & MODIFY
# ─────────────────────────────────────────────────────────────────────────────

async def cancel_booking(
    db: AsyncSession, redis, booking_id: UUID, user_id: UUID, req: CancelBookingRequest
) -> CancelBookingResponse:
    """
    PUT /{id}/cancel — Cancel with SOW refund policy.
    Releases Redis locks, restores DB slot availability, triggers refund if paid.
    """
    booking = await booking_repo.get_booking_by_id(db, booking_id)
    if not booking:                               raise NotFoundException("Booking not found")
    if booking.user_id != user_id:                raise ForbiddenException("Access denied")
    if booking.status == BookingStatus.CANCELLED: raise BadRequestException("Booking is already cancelled")
    if booking.status == BookingStatus.COMPLETED: raise BadRequestException("Completed bookings cannot be cancelled")

    refund_amount, refund_pct = _calculate_refund(booking)
    await booking_repo.cancel_booking(db, booking_id, req.reason)

    # Release Redis slot locks
    slot_map = [
        ("hotel_room",   booking.hotel_booking,   lambda b: str(b.room_id)),
        ("vehicle",      booking.vehicle_booking,  lambda b: str(b.vehicle_id)),
        ("darshan_slot", booking.darshan_booking,  lambda b: str(b.darshan_slot_id)),
        ("package",      booking.package_booking,  lambda b: str(b.package_id)),
        ("guide",        booking.guide_booking,    lambda b: str(b.guide_id)),
    ]
    for entity_type, sub, get_id in slot_map:
        if sub:
            await booking_repo.release_booking_slot(redis, entity_type, get_id(sub))

    # Restore DB slot availability
    from sqlalchemy import update as sql_update
    from src.models.darshan import DarshanSlot
    from src.models.vehicle import Vehicle

    if booking.darshan_booking:
        await db.execute(
            sql_update(DarshanSlot)
            .where(DarshanSlot.id == booking.darshan_booking.darshan_slot_id)
            .values(booked_count=DarshanSlot.booked_count - booking.darshan_booking.num_persons)
        )
    if booking.vehicle_booking:
        await db.execute(
            sql_update(Vehicle).where(Vehicle.id == booking.vehicle_booking.vehicle_id).values(status="ACTIVE")
        )

    await db.commit()

    # Trigger refund if payment already made
    if refund_amount > 0 and booking.payment_status == PaymentStatus.SUCCESS:
        from src.services import payment_service
        from src.schemas.payment import RefundRequest
        await payment_service.request_refund(db, RefundRequest(
            transaction_id=booking.transaction_id, user_id=user_id,
            amount=float(refund_amount), reason=req.reason or "Booking cancelled",
        ))
    # TODO: publish booking.cancelled event to RabbitMQ when notification service ready

    logger.info("endpoint=PUT /cancel user=%s booking=%s refund=%s pct=%s%%",
                user_id, booking.booking_number, refund_amount, refund_pct)
    return CancelBookingResponse(
        booking_id=booking_id, booking_number=booking.booking_number,
        status=BookingStatus.CANCELLED, refund_amount=refund_amount, refund_percent=refund_pct,
        refund_status="initiated" if refund_amount > 0 else "not_applicable",
        message=(
            f"Booking cancelled. Refund of ₹{refund_amount} will be processed within 5-7 business days."
            if refund_amount > 0
            else "Booking cancelled. No refund applicable as per cancellation policy."
        ),
    )


async def modify_booking(
    db: AsyncSession, booking_id: UUID, user_id: UUID, req: ModifyBookingRequest
) -> ModifyBookingResponse:
    """POST /{id}/modify — Submit date/guest change request for admin approval."""
    booking = await booking_repo.get_booking_for_modify(db, booking_id)
    if not booking:                               raise NotFoundException("Booking not found")
    if booking.user_id != user_id:                raise ForbiddenException("Access denied")
    if booking.status == BookingStatus.COMPLETED: raise BadRequestException("Completed bookings cannot be modified")
    if booking.status == BookingStatus.CANCELLED: raise BadRequestException("Cancelled bookings cannot be modified")

    await booking_repo.create_modify_request(db, booking_id, user_id, {
        "new_start_date":  req.new_start_date.isoformat() if req.new_start_date else None,
        "new_end_date":    req.new_end_date.isoformat() if req.new_end_date else None,
        "new_guest_count": req.new_guest_count,
        "reason":          req.reason,
        "requested_at":    datetime.now(timezone.utc).isoformat(),
    })
    await db.commit()
    logger.info("endpoint=POST /modify user=%s booking=%s", user_id, booking.booking_number)
    return ModifyBookingResponse(
        booking_id=booking_id, booking_number=booking.booking_number, status=booking.status,
        message="Modification request submitted. Admin will review and confirm within 24 hours.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: ASSIGN GUIDE / VEHICLE
# ─────────────────────────────────────────────────────────────────────────────

async def _notify_silently(db: AsyncSession, user_ids: list, ntype: str, title: str, body: str) -> None:
    """Send push notification, swallowing errors so they never block the main flow."""
    try:
        from src.services.notification_service import send_notification
        from src.schemas.notification import SendNotificationRequest
        await send_notification(
            data=SendNotificationRequest(user_ids=user_ids, type=ntype, title=title, body=body, channel="push"),
            db=db,
        )
    except Exception as e:
        logger.warning("Notification failed type=%s error=%s", ntype, e)


async def assign_guide(booking_id: str, data: dict, db: AsyncSession) -> dict:
    """Admin: assign a guide to a guide booking sub-record."""
    from src.models.booking import Booking, GuideBooking
    from src.models.guide import Guide

    booking = (await db.execute(select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()
    if not booking: raise NotFoundException("Booking not found")

    guide_id = data.get("guide_id")
    guide    = (await db.execute(select(Guide).where(Guide.id == guide_id))).scalar_one_or_none()
    if not guide: raise NotFoundException("Guide not found")

    gb = (await db.execute(select(GuideBooking).where(GuideBooking.booking_id == booking.id))).scalar_one_or_none()
    if gb:
        gb.guide_id = guide_id
    await db.commit()

    await _notify_silently(db, [guide.user_id],    "GUIDE_ASSIGNED", "New Trip Assigned",
                           f"You have been assigned to booking #{booking.booking_number}.")
    await _notify_silently(db, [booking.user_id],  "GUIDE_ASSIGNED", "Guide Assigned",
                           "Your guide has been assigned to your trip.")
    return {"booking_id": booking_id, "guide_id": guide_id}


async def assign_vehicle(booking_id: str, data: dict, db: AsyncSession) -> dict:
    """Admin: assign a vehicle to a vehicle booking sub-record."""
    from src.models.booking import Booking, VehicleBooking
    from src.models.vehicle import Vehicle

    booking    = (await db.execute(select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()
    if not booking: raise NotFoundException("Booking not found")

    vehicle_id = data.get("vehicle_id")
    vehicle    = (await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))).scalar_one_or_none()
    if not vehicle: raise NotFoundException("Vehicle not found")

    vb = (await db.execute(select(VehicleBooking).where(VehicleBooking.booking_id == booking.id))).scalar_one_or_none()
    if vb:
        vb.vehicle_id = vehicle_id
    await db.commit()

    await _notify_silently(db, [booking.user_id], "VEHICLE_ASSIGNED", "Vehicle Assigned",
                           f"Your vehicle has been assigned for booking #{booking.booking_number}.")
    return {"booking_id": booking_id, "vehicle_id": vehicle_id}


# ─────────────────────────────────────────────────────────────────────────────
# LIST BOOKINGS — thin wrapper called by GET /users/me/bookings
# ─────────────────────────────────────────────────────────────────────────────

async def list_bookings(
    db: AsyncSession, user, page: int = 1, per_page: int = 10,
    status_filter: Optional[str] = None,
) -> dict:
    """Flat-param wrapper used by the users endpoint."""
    filters  = BookingListFilter(
        page=page, per_page=per_page,
        status=BookingStatus(status_filter) if status_filter else None,
    )
    response = await get_my_bookings(db, user_id=user.id, filters=filters)
    return response.model_dump()