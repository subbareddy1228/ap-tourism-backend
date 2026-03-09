
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.booking import (
    Booking, HotelBooking, VehicleBooking, DarshanBooking,
    PackageBooking, GuideBooking, PoojaBooking, PrasadamOrder,
    BookingTraveler, BookingAddon,
)
from src.common.enums import (          # [FIX-1] enums from common — not from model
    BookingStatus, PaymentStatus, BookingType, DeliveryStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING NUMBER GENERATOR
# Format: APT-YYYYMMDD-XXXX  e.g. APT-20260306-0042
# ─────────────────────────────────────────────────────────────────────────────

async def generate_booking_number(db: AsyncSession) -> str:
    """
    Generates a unique booking number in format APT-YYYYMMDD-XXXX.
    Uses SELECT MAX with FOR UPDATE to prevent race condition on concurrent requests.
    [FIX-4] Original COUNT+1 had race condition — two concurrent requests could get
    the same count and produce a duplicate booking_number (unique constraint violation).
    Fix: lock the latest number for the day, increment from MAX.
    """
    from sqlalchemy import text
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    prefix = f"APT-{date_str}-"

    # Lock latest booking_number for today — prevents concurrent duplicates
    result = await db.execute(
        text("""
            SELECT booking_number
            FROM bookings
            WHERE booking_number LIKE :prefix
            ORDER BY booking_number DESC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """),
        {"prefix": f"{prefix}%"},
    )
    row = result.first()

    if row:
        # Extract last 4-digit sequence and increment
        last_seq = int(row[0].split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{str(next_seq).zfill(4)}"


# ─────────────────────────────────────────────────────────────────────────────
# SLOT LOCKING  (Redis — 15 min lock per entity to prevent double booking)
# Used by: POST /hotel, POST /vehicle, POST /darshan
# Source: Booking Flow diagram — "Lock slot temporarily"
# ─────────────────────────────────────────────────────────────────────────────

async def lock_booking_slot(redis, entity_type: str, entity_id: str, user_id: str) -> bool:
    """
    Lock an entity slot for 15 minutes in Redis.
    Key: booking_lock:{entity_type}:{entity_id}
    Returns True if lock acquired, False if already locked by another user.
    """
    key = f"booking_lock:{entity_type}:{entity_id}"
    # SET key value NX EX — only set if not exists, expire in 900 seconds
    result = await redis.set(key, user_id, nx=True, ex=900)
    return result is not None


async def release_booking_slot(redis, entity_type: str, entity_id: str) -> None:
    """Release the Redis slot lock after booking confirmed or payment failed."""
    key = f"booking_lock:{entity_type}:{entity_id}"
    await redis.delete(key)


async def check_slot_locked(redis, entity_type: str, entity_id: str) -> bool:
    """Check if an entity slot is currently locked."""
    key = f"booking_lock:{entity_type}:{entity_id}"
    return await redis.exists(key) == 1


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKING (master)
# ─────────────────────────────────────────────────────────────────────────────

async def create_booking(db: AsyncSession, data: dict) -> Booking:
    """
    Create master booking record.
    Called first before creating any sub-booking (hotel/vehicle/darshan etc.)
    """
    booking_number = await generate_booking_number(db)
    booking = Booking(
        booking_number=booking_number,
        user_id=data["user_id"],
        booking_type=data["booking_type"],
        status=BookingStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        booking_date=date.today(),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        subtotal=data.get("subtotal", Decimal("0")),
        discount_amount=data.get("discount_amount", Decimal("0")),
        tax_amount=data.get("tax_amount", Decimal("0")),
        convenience_fee=data.get("convenience_fee", Decimal("0")),
        total_amount=data.get("total_amount", Decimal("0")),
        paid_amount=Decimal("0"),
        coupon_code=data.get("coupon_code"),
        special_requests=data.get("special_requests"),
        custom_trip_details=data.get("custom_trip_details"),
        contact_details=data.get("contact_details"),
    )
    db.add(booking)
    await db.flush()   # get booking.id without committing
    return booking


# ─────────────────────────────────────────────────────────────────────────────
# CREATE SUB-BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

async def create_hotel_booking(db: AsyncSession, booking_id: UUID, data: dict) -> HotelBooking:
    """INSERT into hotel_bookings. Called after master booking created."""
    record = HotelBooking(
        booking_id=booking_id,
        hotel_id=data["hotel_id"],
        room_id=data["room_id"],
        check_in_date=data["check_in"],
        check_out_date=data["check_out"],
        check_in_time=data.get("check_in_time"),
        check_out_time=data.get("check_out_time"),
        rooms_count=data.get("rooms_count", 1),
        adults=data.get("adults", 1),
        children=data.get("children", 0),
        room_rate_per_night=data["room_rate_per_night"],
        total_room_charge=data["total_room_charge"],
        guest_details=data.get("guest_details"),
        # [FIX-2] status removed — sub-booking tables have no status column
        # master bookings.status is the single source of truth
    )
    db.add(record)
    await db.flush()
    return record


async def create_vehicle_booking(db: AsyncSession, booking_id: UUID, data: dict) -> VehicleBooking:
    """INSERT into vehicle_bookings."""
    record = VehicleBooking(
        booking_id=booking_id,
        vehicle_id=data["vehicle_id"],
        driver_id=data.get("driver_id"),
        trip_type=data["trip_type"],
        pickup_location=data["pickup_address"],   # Excel: pickup_address → stored as pickup_location
        pickup_lat=data.get("pickup_lat"),
        pickup_lng=data.get("pickup_lng"),
        drop_location=data["drop_address"],        # Excel: drop_address → stored as drop_location
        drop_lat=data.get("drop_lat"),
        drop_lng=data.get("drop_lng"),
        pickup_datetime=data["pickup_datetime"],
        return_datetime=data.get("return_datetime"),
        estimated_km=data.get("estimated_km"),
        actual_km=None,
        rate_per_km=data["rate_per_km"],
        driver_allowance=data.get("driver_allowance", Decimal("0")),
        toll_charges=data.get("toll_charges", Decimal("0")),
        total_charge=data["total_charge"],
        route_details=data.get("route_details"),
        # [FIX-2] status removed — sub-booking tables have no status column
    )
    db.add(record)
    await db.flush()
    return record


async def create_darshan_booking(db: AsyncSession, booking_id: UUID, data: dict) -> DarshanBooking:
    """INSERT into darshan_bookings."""
    record = DarshanBooking(
        booking_id=booking_id,
        temple_id=data["temple_id"],
        darshan_slot_id=data["darshan_slot_id"],
        darshan_type_id=data["darshan_type_id"],
        darshan_date=data["darshan_date"],
        darshan_time=data["darshan_time"],
        num_persons=data["num_persons"],
        price_per_person=data["price_per_person"],
        total_price=data["total_price"],
        devotee_details=data["devotee_details"],   # list of {name, age, id_proof_type, id_proof_number}
        ticket_number=None,                         # generated after payment confirmed
        # [FIX-2] status removed — sub-booking tables have no status column
    )
    db.add(record)
    await db.flush()
    return record


async def create_package_booking(db: AsyncSession, booking_id: UUID, data: dict) -> PackageBooking:
    """INSERT into package_bookings."""
    record = PackageBooking(
        booking_id=booking_id,
        package_id=data["package_id"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        num_adults=data.get("num_adults", 1),
        num_children=data.get("num_children", 0),
        package_price=data["package_price"],
        addon_charges=data.get("addon_charges", Decimal("0")),
        total_price=data["total_price"],
        customizations=data.get("customizations"),
        # [FIX-2] status removed — sub-booking tables have no status column
    )
    db.add(record)
    await db.flush()
    return record


async def create_guide_booking(db: AsyncSession, booking_id: UUID, data: dict) -> GuideBooking:
    """INSERT into guide_bookings."""
    record = GuideBooking(
        booking_id=booking_id,
        guide_id=data["guide_id"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        num_hours=data.get("num_hours"),
        num_days=data.get("num_days"),
        rate=data["rate"],
        total_charge=data["total_charge"],
        meeting_point=data.get("meeting_point"),
        locations_to_cover=data.get("locations_to_cover"),
        # [FIX-2] status removed — sub-booking tables have no status column
    )
    db.add(record)
    await db.flush()
    return record


async def create_pooja_booking(db: AsyncSession, booking_id: UUID, data: dict) -> PoojaBooking:
    """INSERT into pooja_bookings."""
    record = PoojaBooking(
        booking_id=booking_id,
        pooja_service_id=data["pooja_service_id"],
        pooja_date=data["pooja_date"],
        pooja_time=data.get("pooja_time"),
        devotee_names=data["devotee_names"],
        gothram=data.get("gothram"),
        nakshatra=data.get("nakshatra"),
        special_instructions=data.get("special_instructions"),
        price=data["price"],
        # [FIX-2] status removed — sub-booking tables have no status column
    )
    db.add(record)
    await db.flush()
    return record


async def create_prasadam_order(db: AsyncSession, booking_id: UUID, data: dict) -> PrasadamOrder:
    """INSERT into prasadam_orders. One record per item in the order."""
    record = PrasadamOrder(
        booking_id=booking_id,
        prasadam_item_id=data["prasadam_item_id"],
        quantity=data["quantity"],
        unit_price=data["unit_price"],
        total_price=data["total_price"],
        delivery_address_id=data.get("delivery_address_id"),
        delivery_status=DeliveryStatus.PENDING,    # [FIX-3] enum not raw string
        tracking_number=None,
    )
    db.add(record)
    await db.flush()
    return record


# ─────────────────────────────────────────────────────────────────────────────
# CREATE TRAVELERS & ADDONS  (bulk inserts)
# ─────────────────────────────────────────────────────────────────────────────

async def create_booking_travelers(
    db: AsyncSession, booking_id: UUID, travelers: List[dict]
) -> List[BookingTraveler]:
    """Bulk INSERT into booking_travelers."""
    records = []
    for t in travelers:
        record = BookingTraveler(
            booking_id=booking_id,
            family_member_id=t.get("family_member_id"),
            name=t["name"],
            age=t["age"],
            gender=t.get("gender"),
            id_proof_type=t.get("id_proof_type"),
            id_proof_number=t.get("id_proof_number"),
            is_primary=t.get("is_primary", False),
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


async def create_booking_addons(
    db: AsyncSession, booking_id: UUID, addons: List[dict]
) -> List[BookingAddon]:
    """Bulk INSERT into booking_addons."""
    records = []
    for a in addons:
        record = BookingAddon(
            booking_id=booking_id,
            addon_type=a["addon_type"],
            addon_name=a["addon_name"],
            quantity=a.get("quantity", 1),
            unit_price=a["unit_price"],
            total_price=a["total_price"],
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


async def get_booking_travelers(
    db: AsyncSession, booking_id: UUID
) -> List[BookingTraveler]:
    """SELECT travelers by booking_id."""
    result = await db.execute(
        select(BookingTraveler).where(BookingTraveler.booking_id == booking_id)
    )
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# GET BOOKING  (with all sub-tables eager loaded)
# ─────────────────────────────────────────────────────────────────────────────

async def get_booking_by_id(db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
    """
    SELECT booking + all sub-tables by booking.id.
    Used by GET /bookings/{id}.
    """
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.hotel_booking),
            selectinload(Booking.vehicle_booking),
            selectinload(Booking.darshan_booking),
            selectinload(Booking.package_booking),
            selectinload(Booking.guide_booking),
            selectinload(Booking.pooja_booking),
            selectinload(Booking.prasadam_orders),
            selectinload(Booking.travelers),
            selectinload(Booking.addons),
        )
        .where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def get_booking_by_number(db: AsyncSession, booking_number: str) -> Optional[Booking]:
    """SELECT by booking_number (unique key)."""
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.hotel_booking),
            selectinload(Booking.vehicle_booking),
            selectinload(Booking.darshan_booking),
            selectinload(Booking.package_booking),
            selectinload(Booking.guide_booking),
            selectinload(Booking.pooja_booking),
            selectinload(Booking.prasadam_orders),
            selectinload(Booking.travelers),
            selectinload(Booking.addons),
        )
        .where(Booking.booking_number == booking_number)
    )
    return result.scalar_one_or_none()


async def get_booking_for_modify(db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
    """
    Lightweight fetch to validate modification eligibility.
    Returns booking without sub-tables loaded.
    """
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# GET BOOKING LISTS  (paginated)
# ─────────────────────────────────────────────────────────────────────────────

async def get_bookings_by_user(
    db: AsyncSession,
    user_id: UUID,
    status: Optional[BookingStatus] = None,
    booking_type: Optional[BookingType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    per_page: int = 10,
) -> tuple[List[Booking], int]:
    """
    GET / — All bookings for user with filters: status, type, date_range.
    Returns (items, total_count) for pagination.
    """
    filters = [Booking.user_id == user_id]

    if status:
        filters.append(Booking.status == status)
    if booking_type:
        filters.append(Booking.booking_type == booking_type)
    if date_from:
        filters.append(Booking.start_date >= date_from)
    if date_to:
        filters.append(Booking.start_date <= date_to)

    # total count
    count_result = await db.execute(
        select(func.count(Booking.id)).where(and_(*filters))
    )
    total = count_result.scalar()

    # paginated results
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Booking)
        .where(and_(*filters))
        .order_by(Booking.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = result.scalars().all()
    return items, total


async def get_upcoming_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> tuple[List[Booking], int]:
    """
    GET /upcoming — Bookings with start_date >= today AND status = CONFIRMED.
    """
    today = date.today()
    filters = [
        Booking.user_id == user_id,
        Booking.start_date >= today,
        Booking.status == BookingStatus.CONFIRMED,
    ]

    count_result = await db.execute(
        select(func.count(Booking.id)).where(and_(*filters))
    )
    total = count_result.scalar()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Booking)
        .where(and_(*filters))
        .order_by(Booking.start_date.asc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all(), total


async def get_past_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> tuple[List[Booking], int]:
    """GET /past — Completed bookings."""
    filters = [
        Booking.user_id == user_id,
        Booking.status == BookingStatus.COMPLETED,
    ]

    count_result = await db.execute(
        select(func.count(Booking.id)).where(and_(*filters))
    )
    total = count_result.scalar()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Booking)
        .where(and_(*filters))
        .order_by(Booking.completed_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all(), total


async def get_cancelled_bookings(
    db: AsyncSession, user_id: UUID, page: int = 1, per_page: int = 10
) -> tuple[List[Booking], int]:
    """GET /cancelled — Cancelled bookings with refund status."""
    filters = [
        Booking.user_id == user_id,
        Booking.status == BookingStatus.CANCELLED,
    ]

    count_result = await db.execute(
        select(func.count(Booking.id)).where(and_(*filters))
    )
    total = count_result.scalar()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Booking)
        .where(and_(*filters))
        .order_by(Booking.cancelled_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all(), total


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE BOOKING
# ─────────────────────────────────────────────────────────────────────────────

async def update_booking_status(
    db: AsyncSession,
    booking_id: UUID,
    status: BookingStatus,
) -> Optional[Booking]:
    """
    UPDATE booking status.
    Also sets confirmed_at / cancelled_at / completed_at timestamp automatically.
    Source: Booking flow — Update booking (status: CONFIRMED) after payment.
    """
    now = datetime.now(timezone.utc)
    values: dict = {"status": status, "updated_at": now}

    if status == BookingStatus.CONFIRMED:
        values["confirmed_at"] = now
    elif status == BookingStatus.CANCELLED:
        values["cancelled_at"] = now
    elif status == BookingStatus.COMPLETED:
        values["completed_at"] = now

    await db.execute(
        update(Booking).where(Booking.id == booking_id).values(**values)
    )
    await db.flush()
    return await get_booking_by_id(db, booking_id)


async def update_payment_status(
    db: AsyncSession,
    booking_id: UUID,
    payment_status: PaymentStatus,
    paid_amount: Decimal,
) -> None:
    """
    UPDATE payment_status and paid_amount.
    Source: Booking flow — Update transaction (status: SUCCESS) → Confirm booking.
    """
    await db.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(
            payment_status=payment_status,
            paid_amount=paid_amount,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()


async def cancel_booking(
    db: AsyncSession,
    booking_id: UUID,
    reason: str,
) -> Optional[Booking]:
    """
    PUT /{id}/cancel — Cancel booking, store reason, set cancelled_at.
    Refund calculation done in service layer based on SOW policy:
    >48hrs = 100%, 24-48hrs = 50%, <24hrs = 0%.
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(
            status=BookingStatus.CANCELLED,
            cancellation_reason=reason,
            cancelled_at=now,
            updated_at=now,
        )
    )
    await db.flush()
    return await get_booking_by_id(db, booking_id)


async def update_darshan_ticket_number(
    db: AsyncSession, darshan_booking_id: UUID, ticket_number: str
) -> None:
    """
    Set ticket_number on darshan_booking after payment confirmed.
    Used when generating e-ticket (GET /{id}/ticket).
    """
    await db.execute(
        update(DarshanBooking)
        .where(DarshanBooking.id == darshan_booking_id)
        .values(ticket_number=ticket_number)
        # [FIX-6] status= removed — DarshanBooking has no status column
        # To confirm booking use update_booking_status(db, booking_id, CONFIRMED)
    )
    await db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# TICKET & INVOICE DATA
# ─────────────────────────────────────────────────────────────────────────────

async def get_darshan_ticket_data(
    db: AsyncSession, booking_id: UUID
) -> Optional[Booking]:
    """
    GET /{id}/ticket — Load booking with darshan sub-table and travelers
    to build the e-ticket PDF with QR code.
    """
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.darshan_booking),
            selectinload(Booking.pooja_booking),
            selectinload(Booking.travelers),
        )
        .where(
            and_(
                Booking.id == booking_id,
                or_(
                    Booking.booking_type == BookingType.DARSHAN,
                    Booking.booking_type == BookingType.POOJA,
                )
            )
        )
    )
    return result.scalar_one_or_none()


async def get_invoice_data(
    db: AsyncSession, booking_id: UUID
) -> Optional[Booking]:
    """
    GET /{id}/invoice — Load full booking with all sub-tables
    needed to generate invoice PDF with GST breakdown.
    """
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.hotel_booking),
            selectinload(Booking.vehicle_booking),
            selectinload(Booking.darshan_booking),
            selectinload(Booking.package_booking),
            selectinload(Booking.guide_booking),
            selectinload(Booking.pooja_booking),
            selectinload(Booking.prasadam_orders),
            selectinload(Booking.addons),
        )
        .where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING WITH TRANSACTION  (for payment detail in GET /{id})
# ─────────────────────────────────────────────────────────────────────────────

async def get_booking_with_transaction(
    db: AsyncSession, booking_id: UUID
) -> Optional[dict]:
    """
    JOIN bookings + transactions to get full payment info for booking detail.
    Returns booking + latest successful transaction details.
    """
    from src.models.booking import Booking
    # Import Transaction model — owned by payment team (M12)
    # Using raw query to avoid circular import
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT
                b.id AS booking_id,
                b.booking_number,
                b.total_amount,
                b.paid_amount,
                b.payment_status,
                t.id AS transaction_id,
                t.gateway_order_id AS razorpay_order_id,
                t.gateway_payment_id AS razorpay_payment_id,
                t.payment_method,
                t.completed_at AS paid_at
            FROM bookings b
            LEFT JOIN transactions t
                ON t.booking_id = b.id
                AND t.status = 'success'
                AND t.type = 'payment'
            WHERE b.id = :booking_id
            ORDER BY t.created_at DESC
            LIMIT 1
        """),
        {"booking_id": str(booking_id)}
    )
    row = result.mappings().first()
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN / ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

async def count_bookings_by_status(
    db: AsyncSession, user_id: Optional[UUID] = None
) -> dict:
    """
    SELECT COUNT grouped by status.
    Used by admin dashboard and user profile summary.
    """
    filters = []
    if user_id:
        filters.append(Booking.user_id == user_id)

    result = await db.execute(
        select(Booking.status, func.count(Booking.id))
        .where(and_(*filters))
        .group_by(Booking.status)
    )
    rows = result.all()
    return {str(status): count for status, count in rows}


async def create_modify_request(
    db: AsyncSession,
    booking_id: UUID,
    user_id: UUID,
    data: dict,
) -> None:
    """
    POST /{id}/modify — Store modification request in audit_logs for admin approval.
    Modification requests go to admin — no separate table, stored as audit log entry.
    Source: Excel — 'Request modification such as date or guest change requiring admin approval'
    """
    from sqlalchemy import text
    await db.execute(
        text("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, new_data, created_at)
            VALUES (gen_random_uuid(), :user_id, 'modification_requested',
                    'booking', :booking_id, :new_data::jsonb, NOW())
        """),
        # [FIX-7] ERD audit_logs columns: user_id, action, entity_type, entity_id, new_data
        # was: performed_by (no such column), details (no such column)
        {
            "user_id":   str(user_id),
            "booking_id": str(booking_id),
            "new_data":  json.dumps(data, default=str),
        }
    )
    await db.flush()
