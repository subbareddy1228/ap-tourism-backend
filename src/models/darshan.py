import uuid
import random
import string
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, ForeignKey, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.core.database import Base


def _generate_reference(prefix: str) -> str:
    today = date.today().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{today}-{suffix}"


# ─────────────────────────────────────────────
# Darshan Type
# GET /{id}/darshan-types          — List: FREE, SPECIAL_ENTRY, SUPRABHATA, VIP
# GET /{id}/darshan-types/{type_id} — Detail: price, duration, what_is_included
# ─────────────────────────────────────────────
class DarshanTypeModel(Base):
    __tablename__ = "darshan_types"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id               = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    name                    = Column(String(100), nullable=False)
    darshan_type            = Column(String(50), nullable=False, index=True)   # FREE, SPECIAL_ENTRY, SUPRABHATA, VIP
    description             = Column(Text, nullable=True)
    price                   = Column(Float, default=0.0, nullable=False)
    duration_minutes        = Column(Integer, default=30, nullable=False)
    what_is_included        = Column(Text, nullable=True)
    max_persons_per_booking = Column(Integer, default=6, nullable=False)
    is_active               = Column(Boolean, default=True, nullable=False)
    created_at              = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple = relationship("Temple",      back_populates="darshan_types")
    slots  = relationship("DarshanSlot", back_populates="darshan_type", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Darshan Slot
# GET /{id}/darshan-slots         — All slots next 30 days, cached 2 min
# GET /{id}/darshan-slots/{date}  — Slots for date: quota, booked_count, available_count
# POST /{id}/darshan/check-availability
# ─────────────────────────────────────────────
class DarshanSlot(Base):
    __tablename__ = "darshan_slots"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_date       = Column(Date, nullable=False, index=True)
    start_time      = Column(Time, nullable=False)
    end_time        = Column(Time, nullable=False)
    total_quota     = Column(Integer, nullable=False)
    booked_count    = Column(Integer, default=0, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple       = relationship("Temple",           back_populates="darshan_slots")
    darshan_type = relationship("DarshanTypeModel", back_populates="slots")
    bookings     = relationship("DarshanBooking",   back_populates="slot", cascade="all, delete-orphan")

    @property
    def available_count(self) -> int:
        return max(0, self.total_quota - self.booked_count)

    @property
    def is_full(self) -> bool:
        return self.booked_count >= self.total_quota


# ─────────────────────────────────────────────
# Darshan Booking
# POST /{id}/darshan/book              — Lock Redis 15 min → PENDING → trigger payment
# GET /{id}/darshan/booking/{id}       — Booking detail with QR ticket
# ─────────────────────────────────────────────
class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id         = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id           = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id", ondelete="CASCADE"), nullable=False)
    user_id           = Column(UUID(as_uuid=True), nullable=False, index=True)
    # FIX (W6): safe default so DB never gets a null booking_reference
    booking_reference = Column(String(20), unique=True, nullable=False, default=lambda: _generate_reference("DRS"))
    num_persons       = Column(Integer, nullable=False, default=1)
    total_amount      = Column(Float, default=0.0, nullable=False)
    status            = Column(String(20), default="PENDING", nullable=False)   # PENDING, CONFIRMED, CANCELLED, EXPIRED
    payment_id        = Column(String(100), nullable=True)
    qr_code           = Column(Text, nullable=True)
    pilgrim_details   = Column(JSONB, server_default='[]')                      # [{name, age, id_proof_type, id_proof_number}]
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple = relationship("Temple",      back_populates="darshan_bookings")
    slot   = relationship("DarshanSlot", back_populates="bookings")


# ─────────────────────────────────────────────
# Pooja Service
# GET /{id}/pooja-services          — List with price
# GET /{id}/pooja-services/{id}     — Detail: description, duration, items, priest requirements
# GET /{id}/pooja-services/{id}/slots — Available slots
# ─────────────────────────────────────────────
class PoojaService(Base):
    __tablename__ = "pooja_services"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id           = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    name                = Column(String(255), nullable=False)
    description         = Column(Text, nullable=True)
    price               = Column(Float, nullable=False)
    duration_minutes    = Column(Integer, default=30, nullable=False)
    items_included      = Column(Text, nullable=True)
    priest_requirements = Column(Text, nullable=True)
    max_persons         = Column(Integer, default=10, nullable=False)
    is_active           = Column(Boolean, default=True, nullable=False)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple   = relationship("Temple",       back_populates="pooja_services")
    slots    = relationship("PoojaSlot",    back_populates="pooja_service", cascade="all, delete-orphan")
    bookings = relationship("PoojaBooking", back_populates="pooja_service", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Pooja Slot
# GET /{id}/pooja-services/{id}/slots — Available time slots
# ─────────────────────────────────────────────
class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id        = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_date        = Column(Date, nullable=False, index=True)
    start_time       = Column(Time, nullable=False)
    end_time         = Column(Time, nullable=False)
    total_quota      = Column(Integer, nullable=False)
    booked_count     = Column(Integer, default=0, nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pooja_service = relationship("PoojaService", back_populates="slots")
    bookings      = relationship("PoojaBooking", back_populates="slot", cascade="all, delete-orphan")

    @property
    def available_count(self) -> int:
        return max(0, self.total_quota - self.booked_count)

    @property
    def is_full(self) -> bool:
        return self.booked_count >= self.total_quota


# ─────────────────────────────────────────────
# Pooja Booking
# POST /{id}/pooja/book — lock-pay-confirm flow
# ─────────────────────────────────────────────
class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id         = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    pooja_service_id  = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False)
    slot_id           = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id", ondelete="CASCADE"), nullable=True)
    user_id           = Column(UUID(as_uuid=True), nullable=False, index=True)
    # FIX (W6): safe default
    booking_reference = Column(String(20), unique=True, nullable=False, default=lambda: _generate_reference("POJ"))
    num_persons       = Column(Integer, nullable=False, default=1)
    total_amount      = Column(Float, nullable=False)
    status            = Column(String(20), default="PENDING", nullable=False)
    payment_id        = Column(String(100), nullable=True)
    devotee_name      = Column(String(255), nullable=True)
    gotram            = Column(String(100), nullable=True)
    special_requests  = Column(Text, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple        = relationship("Temple",       back_populates="pooja_bookings")
    pooja_service = relationship("PoojaService", back_populates="bookings")
    slot          = relationship("PoojaSlot",    back_populates="bookings")


# ─────────────────────────────────────────────
# Prasadam Item
# GET /{id}/prasadam           — List for pre-order
# GET /{id}/prasadam/{item_id} — Item detail with price
# ─────────────────────────────────────────────
class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id    = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    price        = Column(Float, nullable=False)
    weight_grams = Column(Integer, nullable=True)
    image_url    = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple      = relationship("Temple",            back_populates="prasadam_items")
    order_items = relationship("PrasadamOrderItem", back_populates="item", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Prasadam Order
# POST /{id}/prasadam/order  — Order for pickup during visit
# GET /{id}/prasadam/orders  — My orders
# ─────────────────────────────────────────────
class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = Column(UUID(as_uuid=True), nullable=False, index=True)
    # FIX (W6): safe default
    order_reference = Column(String(20), unique=True, nullable=False, default=lambda: _generate_reference("PRS"))
    total_amount    = Column(Float, nullable=False)
    pickup_date     = Column(Date, nullable=True)
    status          = Column(String(20), default="PENDING", nullable=False)
    payment_id      = Column(String(100), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple = relationship("Temple",            back_populates="prasadam_orders")
    items  = relationship("PrasadamOrderItem", back_populates="order", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Prasadam Order Item
# ─────────────────────────────────────────────
class PrasadamOrderItem(Base):
    __tablename__ = "prasadam_order_items"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id   = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id    = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id", ondelete="CASCADE"), nullable=False)
    quantity   = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal   = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("PrasadamOrder", back_populates="items")
    item  = relationship("PrasadamItem",  back_populates="order_items")