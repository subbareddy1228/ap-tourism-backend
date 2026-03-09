
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
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import BookingStatus, BookingType, PaymentStatus   # [FIX-1] from common not model
from src.repositories import booking_repo
from src.schemas.booking import (
    # Cart
    CartItemAddRequest, CartItemUpdateRequest, CartResponse, CartItemResponse,
    # Create requests
    BookHotelRequest, BookVehicleRequest, BookDarshanRequest, BookPoojaRequest,
    BookPrasadamRequest, BookPackageRequest, BookGuideRequest,
    BookComboRequest, BookCustomRequest,
    # Responses
    BookingCreatedResponse, BookingDetailResponse, BookingListResponse,
    BookingListItem, BookingListFilter,
    CancelBookingRequest, CancelBookingResponse,
    ModifyBookingRequest, ModifyBookingResponse,
    InvoiceResponse, InvoiceLineItem, TicketResponse,
    PaymentInfoSchema,
)

logger = logging.getLogger(__name__)

# ── Tax & Fee Constants ──────────────────────────────────────────────────────
CGST_RATE       = Decimal("0.09")   # 9%
SGST_RATE       = Decimal("0.09")   # 9%
CONVENIENCE_FEE = Decimal("29.00")  # flat fee per booking


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_totals(
    subtotal: Decimal,
    discount_amount: Decimal = Decimal("0"),
    apply_convenience_fee: bool = True,
) -> dict:
    """
    Calculate tax breakdown and total.
    GST = CGST 9% + SGST 9% = 18% on (subtotal - discount).
    Called by every book_* method before creating booking.
    """
    taxable   = subtotal - discount_amount
    cgst      = (taxable * CGST_RATE).quantize(Decimal("0.01"))
    sgst      = (taxable * SGST_RATE).quantize(Decimal("0.01"))
    tax       = cgst + sgst
    conv_fee  = CONVENIENCE_FEE if apply_convenience_fee else Decimal("0")
    total     = taxable + tax + conv_fee

    return {
        "subtotal":         subtotal,
        "discount_amount":  discount_amount,
        "tax_amount":       tax,
        "convenience_fee":  conv_fee,
        "total_amount":     total,
    }


def _calculate_refund(booking, reason: str) -> tuple[Decimal, int]:
    """
    Refund policy per SOW:
      > 48 hrs before travel  → 100% refund
      24–48 hrs before travel → 50% refund
      < 24 hrs before travel  → 0% refund
    Returns (refund_amount, refund_percent).
    """
    if not booking.start_date:
        return Decimal("0"), 0

    now              = datetime.now(timezone.utc).date()
    hours_remaining  = (booking.start_date - now).total_seconds() / 3600

    if hours_remaining > 48:
        percent = 100
    elif hours_remaining >= 24:
        percent = 50
    else:
        percent = 0

    refund_amount = (booking.paid_amount * Decimal(percent) / 100).quantize(Decimal("0.01"))
    return refund_amount, percent


async def _apply_coupon(coupon_code: Optional[str], subtotal: Decimal) -> Decimal:
    """
    Validate coupon and return discount amount.
    Coupon validation is owned by M16 (Coupon APIs).
    Stub until M16 is ready — returns 0 discount for now.
    # TODO: call coupon_service.validate_coupon(coupon_code, subtotal) when M16 ready
    """
    if not coupon_code:
        return Decimal("0")
    # TODO: integrate with M16 coupon service
    return Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# CART  (Redis only — no DB writes)
# Key: cart:{user_id}   TTL: 1hr (3600 seconds)
# ─────────────────────────────────────────────────────────────────────────────

CART_TTL = 3600   # 1 hour per Excel spec


async def get_cart(redis, user_id: UUID) -> CartResponse:
    """GET /cart — Get current cart items from Redis."""
    cart_key = f"cart:{user_id}"
    raw      = await redis.get(cart_key)
    ttl      = await redis.ttl(cart_key)

    items = []
    if raw:
        cart_data = json.loads(raw)
        for item in cart_data.get("items", []):
            items.append(CartItemResponse(
                item_id=item["item_id"],
                entity_type=item["entity_type"],
                entity_id=UUID(item["entity_id"]),
                date=date.fromisoformat(item["date"]),
                guests=item["guests"],
                options=item.get("options"),
                added_at=datetime.fromisoformat(item["added_at"]),
            ))

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 0))
    return CartResponse(
        user_id=user_id,
        items=items,
        item_count=len(items),
        expires_at=expires_at,
    )


async def add_to_cart(redis, user_id: UUID, req: CartItemAddRequest) -> CartResponse:
    """
    POST /cart/add — Add item to Redis cart.
    Excel: Validate availability first.
    # TODO: call availability check on each entity type when other modules ready
    """
    cart_key  = f"cart:{user_id}"
    raw       = await redis.get(cart_key)
    cart_data = json.loads(raw) if raw else {"items": []}

    new_item = {
        "item_id":     str(uuid.uuid4()),
        "entity_type": req.entity_type.value,
        "entity_id":   str(req.entity_id),
        "date":        req.date.isoformat(),
        "guests":      req.guests,
        "options":     req.options,
        "added_at":    datetime.now(timezone.utc).isoformat(),
    }
    cart_data["items"].append(new_item)

    await redis.set(cart_key, json.dumps(cart_data), ex=CART_TTL)
    logger.info(f"endpoint=POST /cart/add user={user_id} entity_type={req.entity_type} entity_id={req.entity_id}")
    return await get_cart(redis, user_id)


async def update_cart_item(
    redis, user_id: UUID, item_id: str, req: CartItemUpdateRequest
) -> CartResponse:
    """PUT /cart/{item_id} — Update cart item dates or guests count."""
    cart_key  = f"cart:{user_id}"
    raw       = await redis.get(cart_key)
    if not raw:
        raise HTTPException(status_code=404, detail="Cart is empty")

    cart_data = json.loads(raw)
    found     = False
    for item in cart_data["items"]:
        if item["item_id"] == item_id:
            if req.date:
                item["date"] = req.date.isoformat()
            if req.guests:
                item["guests"] = req.guests
            if req.options:
                item["options"] = req.options
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await redis.set(cart_key, json.dumps(cart_data), ex=CART_TTL)
    return await get_cart(redis, user_id)


async def remove_cart_item(redis, user_id: UUID, item_id: str) -> CartResponse:
    """DELETE /cart/{item_id} — Remove item from cart."""
    cart_key  = f"cart:{user_id}"
    raw       = await redis.get(cart_key)
    if not raw:
        raise HTTPException(status_code=404, detail="Cart is empty")

    cart_data         = json.loads(raw)
    original_count    = len(cart_data["items"])
    cart_data["items"] = [i for i in cart_data["items"] if i["item_id"] != item_id]

    if len(cart_data["items"]) == original_count:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await redis.set(cart_key, json.dumps(cart_data), ex=CART_TTL)
    return await get_cart(redis, user_id)


async def clear_cart(redis, user_id: UUID) -> None:
    """DELETE /cart/clear — Clear entire cart. Endpoint returns standard success response."""
    await redis.delete(f"cart:{user_id}")
    logger.info(f"endpoint=DELETE /cart/clear user={user_id}")


async def checkout_cart(
    db: AsyncSession, redis, user_id: UUID
) -> BookingCreatedResponse:
    """
    POST /cart/checkout — Convert cart to booking.
    Excel: Lock slots, create booking with status PENDING, trigger payment.
    """
    cart_key  = f"cart:{user_id}"
    raw       = await redis.get(cart_key)
    if not raw:
        raise HTTPException(status_code=400, detail="Cart is empty")

    cart_data = json.loads(raw)
    items     = cart_data.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Lock all slots before creating booking
    for item in items:
        locked = await booking_repo.lock_booking_slot(
            redis, item["entity_type"], item["entity_id"], str(user_id)
        )
        if not locked:
            raise HTTPException(
                status_code=409,
                detail=f"{item['entity_type']} {item['entity_id']} is no longer available"
            )

    # Determine booking type from first item (combo if multiple types)
    entity_types = {item["entity_type"] for item in items}
    if len(entity_types) > 1:
        booking_type = BookingType.COMBO
    else:
        booking_type = BookingType(items[0]["entity_type"])

    # Calculate totals (stub pricing — real pricing from each module)
    # TODO: calculate subtotal per item when entity modules (M5,M6,M7,M9,M10) are ready
    # For now each item is priced at stub rate; real pricing fetched from each module
    subtotal = Decimal("0")
    for item in items:
        # TODO: call respective module pricing endpoint per entity_type
        subtotal += Decimal("1000.00")   # stub price per cart item

    totals = _calculate_totals(subtotal)
    booking = await booking_repo.create_booking(db, {
        "user_id":      user_id,
        "booking_type": booking_type,
        **totals,
    })

    await db.commit()
    await clear_cart(redis, user_id)

    logger.info(f"endpoint=POST /cart/checkout status=201 user={user_id} booking={booking.booking_number}")
    return BookingCreatedResponse(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        booking_type=booking.booking_type,
        status=booking.status,
        payment_status=booking.payment_status,
        total_amount=booking.total_amount,
        payment_required=True,
        message="Booking created. Please complete payment to confirm.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

async def book_hotel(
    db: AsyncSession, redis, user_id: UUID, req: BookHotelRequest
) -> BookingCreatedResponse:
    """
    POST /hotel — Book hotel room.
    Excel: Lock room 15 minutes in Redis.
    """
    # Lock room slot
    locked = await booking_repo.lock_booking_slot(
        redis, "hotel_room", str(req.room_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Room is no longer available. Please try another room.")

    try:
        # Calculate nights
        nights    = (req.check_out - req.check_in).days
        if nights <= 0:
            raise HTTPException(status_code=400, detail="check_out must be after check_in")

        # Pricing — stub rate until M5 is ready
        # TODO: fetch room_rate from hotel_service when M5 ready
        room_rate = Decimal("2000.00")   # stub
        subtotal  = room_rate * nights * req.rooms_count

        discount  = await _apply_coupon(req.coupon_code, subtotal)
        totals    = _calculate_totals(subtotal, discount)

        # Create master booking
        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.HOTEL,
            "start_date":      req.check_in,
            "end_date":        req.check_out,
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        # Create hotel sub-booking
        await booking_repo.create_hotel_booking(db, booking.id, {
            "hotel_id":            req.hotel_id,
            "room_id":             req.room_id,
            "check_in":            req.check_in,
            "check_out":           req.check_out,
            "rooms_count":         req.rooms_count,
            "adults":              req.adults,
            "children":            req.children,
            "room_rate_per_night": room_rate,
            "total_room_charge":   room_rate * nights * req.rooms_count,
        })

        # Travelers
        if req.travelers:
            await booking_repo.create_booking_travelers(
                db, booking.id,
                [t.model_dump() for t in req.travelers]
            )

        # Addons
        if req.addons:
            await booking_repo.create_booking_addons(
                db, booking.id,
                [a.model_dump() for a in req.addons]
            )

        await db.commit()
        logger.info(f"endpoint=POST /hotel status=201 user={user_id} booking={booking.booking_number} hotel={req.hotel_id}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.HOTEL,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Hotel booked. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "hotel_room", str(req.room_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "hotel_room", str(req.room_id))
        await db.rollback()
        logger.error(f"Hotel booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_vehicle(
    db: AsyncSession, redis, user_id: UUID, req: BookVehicleRequest
) -> BookingCreatedResponse:
    """POST /vehicle — Book vehicle."""
    locked = await booking_repo.lock_booking_slot(
        redis, "vehicle", str(req.vehicle_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Vehicle is not available for selected date.")

    try:
        # TODO: fetch rate_per_km from vehicle_service when M6 ready
        rate_per_km = Decimal("16.00")   # stub SUV rate
        est_km      = Decimal("100.00")  # stub
        subtotal    = rate_per_km * est_km

        discount = await _apply_coupon(req.coupon_code, subtotal)
        totals   = _calculate_totals(subtotal, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.VEHICLE,
            "start_date":      req.pickup_date,
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        await booking_repo.create_vehicle_booking(db, booking.id, {
            "vehicle_id":      req.vehicle_id,
            "trip_type":       req.trip_type,
            "pickup_address":  req.pickup_address,
            "pickup_lat":      req.pickup_lat,
            "pickup_lng":      req.pickup_lng,
            "drop_address":    req.drop_address,
            "drop_lat":        req.drop_lat,
            "drop_lng":        req.drop_lng,
            "pickup_datetime": req.pickup_datetime,
            "return_datetime": req.return_datetime,
            "estimated_km":    est_km,
            "rate_per_km":     rate_per_km,
            "total_charge":    subtotal,
        })

        if req.travelers:
            await booking_repo.create_booking_travelers(
                db, booking.id, [t.model_dump() for t in req.travelers]
            )
        if req.addons:
            await booking_repo.create_booking_addons(
                db, booking.id, [a.model_dump() for a in req.addons]
            )

        await db.commit()
        logger.info(f"endpoint=POST /vehicle status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.VEHICLE,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Vehicle booked. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "vehicle", str(req.vehicle_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "vehicle", str(req.vehicle_id))
        await db.rollback()
        logger.error(f"Vehicle booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_darshan(
    db: AsyncSession, redis, user_id: UUID, req: BookDarshanRequest
) -> BookingCreatedResponse:
    """
    POST /darshan — Book darshan slot.
    Booking flow: verify slot → lock → calculate → create → trigger payment.
    """
    # Check slot not already locked
    if await booking_repo.check_slot_locked(redis, "darshan_slot", str(req.darshan_slot_id)):
        raise HTTPException(status_code=409, detail="Darshan slot is no longer available.")

    locked = await booking_repo.lock_booking_slot(
        redis, "darshan_slot", str(req.darshan_slot_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Darshan slot is no longer available.")

    try:
        num_persons = len(req.devotees)
        # TODO: fetch price_per_person from temple_service when M7 ready
        price_per_person = Decimal("300.00")   # stub
        subtotal         = price_per_person * num_persons

        discount = await _apply_coupon(req.coupon_code, subtotal)
        totals   = _calculate_totals(subtotal, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.DARSHAN,
            "start_date":      req.darshan_date,
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        await booking_repo.create_darshan_booking(db, booking.id, {
            "temple_id":       req.temple_id,
            "darshan_slot_id": req.darshan_slot_id,
            "darshan_type_id": req.darshan_type_id,
            "darshan_date":    req.darshan_date,
            "darshan_time":    req.darshan_time,   # [FIX-8] was None hardcoded — req.darshan_time exists in schema
            "num_persons":     num_persons,
            "price_per_person": price_per_person,
            "total_price":     subtotal,
            "devotee_details": [d.model_dump() for d in req.devotees],
        })

        # Store devotees as travelers
        await booking_repo.create_booking_travelers(db, booking.id, [
            {
                "name":            d.name,
                "age":             d.age,
                "id_proof_type":   d.id_proof_type,
                "id_proof_number": d.id_proof_number,
                "is_primary":      i == 0,
            }
            for i, d in enumerate(req.devotees)
        ])

        await db.commit()
        logger.info(f"endpoint=POST /darshan status=201 user={user_id} booking={booking.booking_number} temple={req.temple_id}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.DARSHAN,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Darshan slot reserved for 15 minutes. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "darshan_slot", str(req.darshan_slot_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "darshan_slot", str(req.darshan_slot_id))
        await db.rollback()
        logger.error(f"Darshan booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_pooja(
    db: AsyncSession, redis, user_id: UUID, req: BookPoojaRequest
) -> BookingCreatedResponse:
    """POST /pooja — Book pooja service with devotees list."""
    locked = await booking_repo.lock_booking_slot(
        redis, "pooja_service", str(req.pooja_service_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Pooja slot is not available.")

    try:
        # TODO: fetch price from pooja_service when M7 ready
        price    = Decimal("500.00")   # stub
        discount = await _apply_coupon(req.coupon_code, price)
        totals   = _calculate_totals(price, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.POOJA,
            "start_date":      req.pooja_date,
            "coupon_code":     req.coupon_code,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        await booking_repo.create_pooja_booking(db, booking.id, {
            "pooja_service_id":     req.pooja_service_id,
            "pooja_date":           req.pooja_date,
            "pooja_time":           req.pooja_time,
            "devotee_names":        req.devotee_names,
            "gothram":              req.gothram,
            "nakshatra":            req.nakshatra,
            "special_instructions": req.special_instructions,
            "price":                price,
        })

        await db.commit()
        logger.info(f"endpoint=POST /pooja status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.POOJA,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Pooja slot reserved. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "pooja_service", str(req.pooja_service_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "pooja_service", str(req.pooja_service_id))
        await db.rollback()
        logger.error(f"Pooja booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_prasadam(
    db: AsyncSession, redis, user_id: UUID, req: BookPrasadamRequest
) -> BookingCreatedResponse:
    """POST /prasadam — Order prasadam for pickup."""
    try:
        # Calculate per item — TODO: fetch unit prices from M7 when ready
        item_price = Decimal("150.00")   # stub per item
        subtotal   = sum(
            item_price * item.quantity for item in req.items
        )
        discount = await _apply_coupon(req.coupon_code, subtotal)
        totals   = _calculate_totals(subtotal, discount, apply_convenience_fee=False)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.PRASADAM,
            "start_date":      req.pickup_date,
            "coupon_code":     req.coupon_code,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        # One prasadam_order record per item
        for item in req.items:
            item_total = item_price * item.quantity
            await booking_repo.create_prasadam_order(db, booking.id, {
                "prasadam_item_id":  item.prasadam_item_id,
                "quantity":          item.quantity,
                "unit_price":        item_price,
                "total_price":       item_total,
                "delivery_address_id": req.delivery_address_id,
            })

        await db.commit()
        logger.info(f"endpoint=POST /prasadam status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.PRASADAM,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Prasadam order placed. Complete payment to confirm.",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Prasadam order failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Order failed. Please try again.")


async def book_package(
    db: AsyncSession, redis, user_id: UUID, req: BookPackageRequest
) -> BookingCreatedResponse:
    """POST /package — Book tour package."""
    locked = await booking_repo.lock_booking_slot(
        redis, "package", str(req.package_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Package is fully booked for selected date.")

    try:
        # TODO: fetch package_price from package_service when M9 ready
        package_price = Decimal("15000.00")   # stub
        addon_charges = sum(
            a.total_price for a in req.addons
        ) if req.addons else Decimal("0")

        subtotal = package_price * (req.num_adults + req.num_children) + addon_charges
        discount = await _apply_coupon(req.coupon_code, subtotal)
        totals   = _calculate_totals(subtotal, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.PACKAGE,
            "start_date":      req.start_date,
            "end_date":        req.end_date,   # [FIX-5] was stub start+2 days — req.end_date is required in schema
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        await booking_repo.create_package_booking(db, booking.id, {
            "package_id":    req.package_id,
            "start_date":    req.start_date,
            "end_date":      req.end_date,     # [FIX-5] was stub end_date variable — use req.end_date
            "num_adults":    req.num_adults,
            "num_children":  req.num_children,
            "package_price": package_price,
            "addon_charges": addon_charges,
            "total_price":   subtotal,
            "customizations": req.customizations,
        })

        if req.traveler_details:
            await booking_repo.create_booking_travelers(
                db, booking.id, [t.model_dump() for t in req.traveler_details]
            )
        if req.addons:
            await booking_repo.create_booking_addons(
                db, booking.id, [a.model_dump() for a in req.addons]
            )

        await db.commit()
        logger.info(f"endpoint=POST /package status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.PACKAGE,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Package booked. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "package", str(req.package_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "package", str(req.package_id))
        await db.rollback()
        logger.error(f"Package booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_guide(
    db: AsyncSession, redis, user_id: UUID, req: BookGuideRequest
) -> BookingCreatedResponse:
    """POST /guide — Book guide with start_date, end_date, destination_id."""
    locked = await booking_repo.lock_booking_slot(
        redis, "guide", str(req.guide_id), str(user_id)
    )
    if not locked:
        raise HTTPException(status_code=409, detail="Guide is not available for selected dates.")

    try:
        num_days = (req.end_date - req.start_date).days + 1
        # TODO: fetch rate from guide_service when M10 ready
        rate         = Decimal("1500.00")   # stub per day
        total_charge = rate * num_days

        discount = await _apply_coupon(req.coupon_code, total_charge)
        totals   = _calculate_totals(total_charge, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.GUIDE,
            "start_date":      req.start_date,
            "end_date":        req.end_date,
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        await booking_repo.create_guide_booking(db, booking.id, {
            "guide_id":           req.guide_id,
            "start_date":         req.start_date,
            "end_date":           req.end_date,
            "num_days":           num_days,
            "rate":               rate,
            "total_charge":       total_charge,
            "meeting_point":      req.meeting_point,
            "locations_to_cover": [str(lid) for lid in req.locations_to_cover] if req.locations_to_cover else None,
        })

        await db.commit()
        logger.info(f"endpoint=POST /guide status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.GUIDE,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Guide booked. Complete payment to confirm.",
        )

    except HTTPException:
        await booking_repo.release_booking_slot(redis, "guide", str(req.guide_id))
        raise
    except Exception as e:
        await booking_repo.release_booking_slot(redis, "guide", str(req.guide_id))
        await db.rollback()
        logger.error(f"Guide booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_combo(
    db: AsyncSession, redis, user_id: UUID, req: BookComboRequest
) -> BookingCreatedResponse:
    """
    POST /combo — Combo booking: package + hotel + vehicle in one transaction.
    Creates one master booking with multiple sub-bookings.
    """
    if not any([req.package, req.hotel, req.vehicle]):
        raise HTTPException(status_code=400, detail="At least one of package, hotel, or vehicle is required.")

    locked_slots = []
    try:
        total_subtotal = Decimal("0")
        start_date     = None

        # Lock all slots first
        if req.hotel:
            locked = await booking_repo.lock_booking_slot(
                redis, "hotel_room", str(req.hotel.room_id), str(user_id)
            )
            if not locked:
                raise HTTPException(status_code=409, detail="Selected room is not available.")
            locked_slots.append(("hotel_room", str(req.hotel.room_id)))
            nights = (req.hotel.check_out - req.hotel.check_in).days
            total_subtotal += Decimal("2000.00") * nights   # stub
            start_date = req.hotel.check_in

        if req.vehicle:
            locked = await booking_repo.lock_booking_slot(
                redis, "vehicle", str(req.vehicle.vehicle_id), str(user_id)
            )
            if not locked:
                raise HTTPException(status_code=409, detail="Selected vehicle is not available.")
            locked_slots.append(("vehicle", str(req.vehicle.vehicle_id)))
            total_subtotal += Decimal("1600.00")   # stub

        if req.package:
            locked = await booking_repo.lock_booking_slot(
                redis, "package", str(req.package.package_id), str(user_id)
            )
            if not locked:
                raise HTTPException(status_code=409, detail="Selected package is fully booked.")
            locked_slots.append(("package", str(req.package.package_id)))
            total_subtotal += Decimal("15000.00")   # stub
            if not start_date:
                start_date = req.package.start_date

        discount = await _apply_coupon(req.coupon_code, total_subtotal)
        totals   = _calculate_totals(total_subtotal, discount)

        booking = await booking_repo.create_booking(db, {
            "user_id":         user_id,
            "booking_type":    BookingType.COMBO,
            "start_date":      start_date,
            "coupon_code":     req.coupon_code,
            "special_requests": req.special_requests,
            "contact_details": req.contact_details.model_dump() if req.contact_details else None,
            **totals,
        })

        # Create each sub-booking
        if req.hotel:
            nights = (req.hotel.check_out - req.hotel.check_in).days
            room_rate = Decimal("2000.00")
            await booking_repo.create_hotel_booking(db, booking.id, {
                "hotel_id":            req.hotel.hotel_id,
                "room_id":             req.hotel.room_id,
                "check_in":            req.hotel.check_in,
                "check_out":           req.hotel.check_out,
                "rooms_count":         req.hotel.rooms_count,
                "adults":              req.hotel.adults,
                "children":            req.hotel.children,
                "room_rate_per_night": room_rate,
                "total_room_charge":   room_rate * nights,
            })

        if req.vehicle:
            await booking_repo.create_vehicle_booking(db, booking.id, {
                "vehicle_id":      req.vehicle.vehicle_id,
                "trip_type":       req.vehicle.trip_type,
                "pickup_address":  req.vehicle.pickup_address,
                "pickup_lat":      req.vehicle.pickup_lat,
                "pickup_lng":      req.vehicle.pickup_lng,
                "drop_address":    req.vehicle.drop_address,
                "drop_lat":        req.vehicle.drop_lat,
                "drop_lng":        req.vehicle.drop_lng,
                "pickup_datetime": req.vehicle.pickup_datetime,
                "return_datetime": req.vehicle.return_datetime,
                "rate_per_km":     Decimal("16.00"),
                "total_charge":    Decimal("1600.00"),
            })

        if req.package:
            await booking_repo.create_package_booking(db, booking.id, {
                "package_id":    req.package.package_id,
                "start_date":    req.package.start_date,
                "end_date":      req.package.end_date,   # [FIX-6] was stub start+2 days — req.package.end_date is required
                "num_adults":    req.package.num_adults,
                "num_children":  req.package.num_children,
                "package_price": Decimal("15000.00"),
                "addon_charges": Decimal("0"),
                "total_price":   Decimal("15000.00"),
                "customizations": req.package.customizations,
            })

        await db.commit()
        logger.info(f"endpoint=POST /combo status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.COMBO,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=totals["total_amount"],
            payment_required=True,
            message="Combo booking created. Complete payment to confirm.",
        )

    except HTTPException:
        for entity_type, entity_id in locked_slots:
            await booking_repo.release_booking_slot(redis, entity_type, entity_id)
        raise
    except Exception as e:
        for entity_type, entity_id in locked_slots:
            await booking_repo.release_booking_slot(redis, entity_type, entity_id)
        await db.rollback()
        logger.error(f"Combo booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Booking failed. Please try again.")


async def book_custom(
    db: AsyncSession, user_id: UUID, req: BookCustomRequest
) -> BookingCreatedResponse:
    """POST /custom — Custom trip request. No slot locking needed."""
    try:
        # Custom bookings have no upfront price — stored as request only
        totals = _calculate_totals(                     # [FIX-9] was _calculate_totals(Decimal("0"), apply_convenience_fee=False)
            subtotal=Decimal("0"),                      # second positional arg is discount_amount not apply_convenience_fee
            discount_amount=Decimal("0"),
            apply_convenience_fee=False,
        )

        booking = await booking_repo.create_booking(db, {
            "user_id":           user_id,
            "booking_type":      BookingType.CUSTOM,
            "start_date":        req.start_date,
            "end_date":          req.end_date,
            "special_requests":  req.special_requests,
            "contact_details":   req.contact_details.model_dump() if req.contact_details else None,
            "custom_trip_details": {
                "destinations":    [str(d) for d in req.destinations],
                "services_needed": req.services_needed,
                "group_size":      req.group_size,
                "budget":          str(req.budget) if req.budget else None,
            },
            **totals,
        })

        if req.traveler_details:
            await booking_repo.create_booking_travelers(
                db, booking.id, [t.model_dump() for t in req.traveler_details]
            )

        await db.commit()
        logger.info(f"endpoint=POST /custom status=201 user={user_id} booking={booking.booking_number}")

        return BookingCreatedResponse(
            booking_id=booking.id,
            booking_number=booking.booking_number,
            booking_type=BookingType.CUSTOM,
            status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=Decimal("0"),
            payment_required=False,
            message="Custom trip request submitted. Our team will contact you within 24 hours.",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Custom booking failed user={user_id} error={e}")
        raise HTTPException(status_code=500, detail="Request failed. Please try again.")


# ─────────────────────────────────────────────────────────────────────────────
# MY BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

async def get_my_bookings(
    db: AsyncSession, user_id: UUID, filters: BookingListFilter
) -> BookingListResponse:
    """GET / — All bookings for user with filters: status, type, date_range."""
    items, total = await booking_repo.get_bookings_by_user(
        db,
        user_id=user_id,
        status=filters.status,
        booking_type=filters.booking_type,     # [FIX-2] was filters.type — field renamed in schema
        date_from=filters.date_from,
        date_to=filters.date_to,
        page=filters.page,
        per_page=filters.per_page,
    )
    return _build_list_response(items, total, filters.page, filters.per_page)


async def get_upcoming_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> BookingListResponse:
    """GET /upcoming — start_date >= today AND status = CONFIRMED."""
    items, total = await booking_repo.get_upcoming_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


async def get_past_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> BookingListResponse:
    """GET /past — Completed bookings."""
    items, total = await booking_repo.get_past_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


async def get_cancelled_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> BookingListResponse:
    """GET /cancelled — Cancelled bookings with refund status."""
    items, total = await booking_repo.get_cancelled_bookings(db, user_id, page, per_page)
    return _build_list_response(items, total, page, per_page)


def _build_list_response(
    items, total: int, page: int, per_page: int
) -> BookingListResponse:
    """Build paginated BookingListResponse from ORM objects."""
    list_items = [
        BookingListItem(
            id=b.id,
            booking_number=b.booking_number,
            booking_type=b.booking_type,
            status=b.status,
            payment_status=b.payment_status,
            total_amount=b.total_amount,
            paid_amount=b.paid_amount,
            start_date=b.start_date,
            end_date=b.end_date,
            created_at=b.created_at,
            cancellation_reason=b.cancellation_reason,
            cancelled_at=b.cancelled_at,
        )
        for b in items
    ]
    return BookingListResponse(
        items=list_items,                                           # [FIX-7] was data=
        total=total,
        page=page,
        per_page=per_page,                                          # [FIX-7] was limit=
        total_pages=math.ceil(total / per_page) if total else 0,   # [FIX-7] was pages=
    )


async def get_booking_detail(
    db: AsyncSession, booking_id: UUID, user_id: UUID
) -> BookingDetailResponse:
    """GET /{id} — Full booking detail including items, payment, guide, driver, itinerary."""
    booking = await booking_repo.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get payment info from transactions table
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
        id=booking.id,
        booking_number=booking.booking_number,
        booking_type=booking.booking_type,
        status=booking.status,
        payment_status=booking.payment_status,
        booking_date=booking.booking_date,
        start_date=booking.start_date,
        end_date=booking.end_date,
        subtotal=booking.subtotal,
        discount_amount=booking.discount_amount,
        tax_amount=booking.tax_amount,
        convenience_fee=booking.convenience_fee,
        total_amount=booking.total_amount,
        paid_amount=booking.paid_amount,
        coupon_code=booking.coupon_code,
        special_requests=booking.special_requests,
        contact_details=booking.contact_details,
        cancellation_reason=booking.cancellation_reason,
        cancelled_at=booking.cancelled_at,
        confirmed_at=booking.confirmed_at,
        completed_at=booking.completed_at,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        payment_info=payment_info,
        hotel_booking=booking.hotel_booking,
        vehicle_booking=booking.vehicle_booking,
        darshan_booking=booking.darshan_booking,
        package_booking=booking.package_booking,
        guide_booking=booking.guide_booking,
        pooja_booking=booking.pooja_booking,
        prasadam_orders=booking.prasadam_orders or [],
        travelers=booking.travelers or [],
        addons=booking.addons or [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE & TICKET
# ─────────────────────────────────────────────────────────────────────────────

async def get_invoice(
    db: AsyncSession, booking_id: UUID, user_id: UUID
) -> InvoiceResponse:
    """
    GET /{id}/invoice — Invoice PDF with GST breakdown and payment proof.
    Builds line items, calculates CGST + SGST, returns InvoiceResponse.
    PDF generation done in background task (booking_tasks.py).
    """
    booking = await booking_repo.get_invoice_data(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    contact = booking.contact_details or {}
    line_items = []

    # Build line items based on booking type
    if booking.hotel_booking:
        hb = booking.hotel_booking
        nights = (hb.check_out_date - hb.check_in_date).days
        line_items.append(InvoiceLineItem(
            description=f"Hotel Room × {hb.rooms_count} room(s) × {nights} night(s)",
            quantity=hb.rooms_count * nights,
            unit_price=hb.room_rate_per_night,
            total=hb.total_room_charge,
        ))

    if booking.vehicle_booking:
        vb = booking.vehicle_booking
        line_items.append(InvoiceLineItem(
            description=f"Vehicle — {vb.trip_type.value}",
            quantity=1,
            unit_price=vb.total_charge,
            total=vb.total_charge,
        ))

    if booking.darshan_booking:
        darshan_b = booking.darshan_booking
        line_items.append(InvoiceLineItem(
            description=f"Darshan × {darshan_b.num_persons} person(s)",
            quantity=darshan_b.num_persons,     # [FIX-3] was db_.num_persons — NameError, undefined variable
            unit_price=darshan_b.price_per_person,
            total=darshan_b.total_price,
        ))

    if booking.package_booking:
        pb = booking.package_booking
        line_items.append(InvoiceLineItem(
            description=f"Tour Package × {pb.num_adults + pb.num_children} person(s)",
            quantity=pb.num_adults + pb.num_children,
            unit_price=pb.package_price,
            total=pb.total_price,
        ))

    if booking.guide_booking:
        gb = booking.guide_booking
        line_items.append(InvoiceLineItem(
            description=f"Guide Service × {gb.num_days or 1} day(s)",
            quantity=gb.num_days or 1,
            unit_price=gb.rate,
            total=gb.total_charge,
        ))

    if booking.pooja_booking:
        pb = booking.pooja_booking
        line_items.append(InvoiceLineItem(
            description="Pooja Service",
            quantity=1,
            unit_price=pb.price,
            total=pb.price,
        ))

    for po in (booking.prasadam_orders or []):
        line_items.append(InvoiceLineItem(
            description=f"Prasadam × {po.quantity}",
            quantity=po.quantity,
            unit_price=po.unit_price,
            total=po.total_price,
        ))

    for addon in (booking.addons or []):
        line_items.append(InvoiceLineItem(
            description=addon.addon_name,
            quantity=addon.quantity,
            unit_price=addon.unit_price,
            total=addon.total_price,
        ))

    taxable  = booking.subtotal - booking.discount_amount
    cgst     = (taxable * CGST_RATE).quantize(Decimal("0.01"))
    sgst     = (taxable * SGST_RATE).quantize(Decimal("0.01"))

    # Get payment info
    txn = await booking_repo.get_booking_with_transaction(db, booking_id)

    invoice_number = f"INV-{booking.booking_number}"

    return InvoiceResponse(
        invoice_number=invoice_number,
        booking_number=booking.booking_number,
        booking_type=booking.booking_type,
        customer_name=contact.get("name", ""),
        customer_phone=contact.get("phone", ""),
        customer_email=contact.get("email"),
        invoice_date=booking.booking_date,
        line_items=line_items,
        subtotal=booking.subtotal,
        discount=booking.discount_amount,
        cgst=cgst,
        sgst=sgst,
        total_tax=booking.tax_amount,
        convenience_fee=booking.convenience_fee,
        total_amount=booking.total_amount,
        paid_amount=booking.paid_amount,
        payment_method=txn.get("payment_method") if txn else None,
        payment_proof=txn.get("razorpay_payment_id") if txn else None,
        pdf_url=None,   # Generated async by booking_tasks.generate_invoice_pdf
    )


async def get_ticket(
    db: AsyncSession, booking_id: UUID, user_id: UUID
) -> TicketResponse:
    """
    GET /{id}/ticket — E-ticket with QR code for darshan or pooja.
    """
    booking = await booking_repo.get_darshan_ticket_data(db, booking_id)
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found. Only darshan and pooja bookings have tickets."
        )
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Ticket available only after payment confirmation.")

    # Build ticket from darshan or pooja booking
    if booking.darshan_booking:
        darshan_b = booking.darshan_booking
        devotee_names = [t.name for t in (booking.travelers or [])]
        return TicketResponse(
            ticket_number=darshan_b.ticket_number or booking.booking_number,   # [FIX-4] was db_.ticket_number — NameError
            booking_number=booking.booking_number,
            booking_type=booking.booking_type,
            temple_name="",           # TODO: fetch from temple_service M7
            darshan_type=str(darshan_b.darshan_type_id),
            pooja_name=None,
            visit_date=darshan_b.darshan_date,
            visit_time=darshan_b.darshan_time,
            num_persons=darshan_b.num_persons,
            devotee_names=devotee_names,
            qr_code_url="",           # Generated async by booking_tasks.generate_qr_code
            pdf_url=None,
            instructions="Please carry original ID proof for all devotees.",
        )

    elif booking.pooja_booking:
        pb = booking.pooja_booking
        return TicketResponse(
            ticket_number=booking.booking_number,
            booking_number=booking.booking_number,
            booking_type=booking.booking_type,
            temple_name="",           # TODO: fetch from temple_service M7
            darshan_type=None,
            pooja_name=str(pb.pooja_service_id),
            visit_date=pb.pooja_date,
            visit_time=pb.pooja_time,
            num_persons=len(pb.devotee_names) if pb.devotee_names else 1,
            devotee_names=pb.devotee_names or [],
            qr_code_url="",           # Generated async by booking_tasks.generate_qr_code
            pdf_url=None,
            instructions="Please arrive 30 minutes before pooja time.",
        )

    raise HTTPException(status_code=400, detail="Ticket not available for this booking type.")


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL & MODIFY
# ─────────────────────────────────────────────────────────────────────────────

async def cancel_booking(
    db: AsyncSession, redis, booking_id: UUID, user_id: UUID,
    req: CancelBookingRequest
) -> CancelBookingResponse:
    """
    PUT /{id}/cancel — Cancel booking with refund policy.
    SOW: >48hrs = 100%, 24-48hrs = 50%, <24hrs = 0%.
    """
    booking = await booking_repo.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    if booking.status == BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Completed bookings cannot be cancelled")

    refund_amount, refund_percent = _calculate_refund(booking, req.reason)

    # Cancel in DB
    await booking_repo.cancel_booking(db, booking_id, req.reason)

    # Release Redis slot locks
    if booking.hotel_booking:
        await booking_repo.release_booking_slot(redis, "hotel_room", str(booking.hotel_booking.room_id))
    if booking.vehicle_booking:
        await booking_repo.release_booking_slot(redis, "vehicle", str(booking.vehicle_booking.vehicle_id))
    if booking.darshan_booking:
        await booking_repo.release_booking_slot(redis, "darshan_slot", str(booking.darshan_booking.darshan_slot_id))
    if booking.package_booking:
        await booking_repo.release_booking_slot(redis, "package", str(booking.package_booking.package_id))
    if booking.guide_booking:
        await booking_repo.release_booking_slot(redis, "guide", str(booking.guide_booking.guide_id))

    await db.commit()

    # TODO: trigger refund via payment_service when M12 ready
    # TODO: publish booking.cancelled event to RabbitMQ when notification service ready

    logger.info(f"endpoint=PUT /cancel status=200 user={user_id} booking={booking.booking_number} refund_amount={refund_amount} refund_percent={refund_percent}")

    return CancelBookingResponse(
        booking_id=booking_id,
        booking_number=booking.booking_number,
        status=BookingStatus.CANCELLED,
        refund_amount=refund_amount,
        refund_percent=refund_percent,
        refund_status="initiated" if refund_amount > 0 else "not_applicable",
        message=f"Booking cancelled. Refund of ₹{refund_amount} will be processed within 5-7 business days."
        if refund_amount > 0 else "Booking cancelled. No refund applicable as per cancellation policy.",
    )


async def modify_booking(
    db: AsyncSession, booking_id: UUID, user_id: UUID,
    req: ModifyBookingRequest
) -> ModifyBookingResponse:
    """
    POST /{id}/modify — Request modification requiring admin approval.
    Excel: date or guest change requiring admin approval.
    """
    booking = await booking_repo.get_booking_for_modify(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status == BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Completed bookings cannot be modified")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cancelled bookings cannot be modified")

    await booking_repo.create_modify_request(db, booking_id, user_id, {
        "new_start_date":  req.new_start_date.isoformat() if req.new_start_date else None,
        "new_end_date":    req.new_end_date.isoformat() if req.new_end_date else None,
        "new_guest_count": req.new_guest_count,
        "reason":          req.reason,
        "requested_at":    datetime.now(timezone.utc).isoformat(),
    })

    await db.commit()
    logger.info(f"endpoint=POST /modify status=200 user={user_id} booking={booking.booking_number}")

    return ModifyBookingResponse(
        booking_id=booking_id,
        booking_number=booking.booking_number,
        status=booking.status,
        message="Modification request submitted. Admin will review and confirm within 24 hours.",
    )
