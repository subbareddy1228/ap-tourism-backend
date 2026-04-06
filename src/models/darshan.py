"""
models/darshan.py  —  Temple / Darshan / Pooja / Prasadam Module

Changes vs original:
  PoojaBooking — 7 columns fixed:
    • Renamed  gotram          → gothram  (matches booking schema PoojaBookingDetail)
    • Renamed  devotee_name    → devotee_names (JSONB list, not a single string)
    • Renamed  special_requests→ special_instructions (matches booking schema)
    • Renamed  total_amount    → price  (matches booking schema PoojaBookingDetail)
    • Added    pooja_date      (Date)   — booking_repo writes it, column was missing
    • Added    pooja_time      (Time)   — booking_repo writes it, column was missing
    • Added    nakshatra       (String) — booking schema sends it, column was missing

  PrasadamOrder — 4 columns fixed:
    • Added    prasadam_item_id (UUID) — booking_repo writes it, column was missing
    • Added    quantity         (Integer) — booking_repo writes it, column was missing
    • Added    unit_price       (Numeric) — booking_repo writes it, column was missing
    • Added    total_price      (Numeric) — booking_repo writes it, column was missing
    • Added    delivery_address_id (UUID) — booking_repo writes it, column was missing
    • Added    delivery_status  (String)  — booking_repo writes it, column was missing
    • Added    tracking_number  (String)  — used by PrasadamOrderDetail schema

  All new columns nullable=True for safe Alembic migration on existing rows.
"""

import uuid
import random
import string
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, ForeignKey, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def generate_reference(prefix: str) -> str:
    today  = date.today().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{today}-{suffix}"


# ─────────────────────────────────────────────────────────────────────────────
# Darshan Type
# ─────────────────────────────────────────────────────────────────────────────

class DarshanType(Base):
    __tablename__ = "darshan_types"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(
        UUID(as_uuid=True),
        ForeignKey("temples.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name         = Column(String(100), nullable=False)
    darshan_type = Column(String(50),  nullable=False, index=True)
    description  = Column(Text,        nullable=True)

    price            = Column(Float,   default=0.0)
    duration_minutes = Column(Integer, default=30)
    what_is_included = Column(Text,    nullable=True)

    max_persons_per_booking = Column(Integer, default=6)
    is_active               = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple = relationship("Temple", back_populates="darshan_types")
    slots  = relationship(
        "DarshanSlot", back_populates="darshan_type", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DarshanType {self.name} temple={self.temple_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Darshan Slot
# ─────────────────────────────────────────────────────────────────────────────

class DarshanSlot(Base):
    __tablename__ = "darshan_slots"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=False)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"), nullable=False)

    slot_date  = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time   = Column(Time, nullable=False)

    total_quota  = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    is_active    = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple       = relationship("Temple",      back_populates="darshan_slots")
    darshan_type = relationship("DarshanType", back_populates="slots")
    bookings     = relationship(
        "DarshanBooking", back_populates="slot", cascade="all, delete-orphan"
    )

    @property
    def available_count(self) -> int:
        return max(0, self.total_quota - self.booked_count)

    @property
    def is_full(self) -> bool:
        return self.booked_count >= self.total_quota

    def __repr__(self) -> str:
        return f"<DarshanSlot {self.slot_date} {self.start_time} quota={self.total_quota}>"


# ─────────────────────────────────────────────────────────────────────────────
# Darshan Booking
# ─────────────────────────────────────────────────────────────────────────────

class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id"),       nullable=False)
    darshan_slot_id = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id"), nullable=True)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"), nullable=True)

    darshan_date = Column(Date, nullable=False)
    darshan_time = Column(Time, nullable=False)

    num_persons      = Column(Integer,       nullable=False)
    price_per_person = Column(Numeric(10, 2), nullable=False)
    total_price      = Column(Numeric(10, 2), nullable=False)

    devotee_details = Column(JSONB,       nullable=True)   # [{name, age, id_proof_type, id_proof_number}]
    ticket_number   = Column(String(50),  unique=True, nullable=True)  # generated after payment

    booking = relationship("Booking",     back_populates="darshan_booking")
    temple  = relationship("Temple",      back_populates="darshan_bookings")
    slot    = relationship("DarshanSlot", back_populates="bookings")

    def __repr__(self) -> str:
        return f"<DarshanBooking date={self.darshan_date} persons={self.num_persons}>"


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Service
# ─────────────────────────────────────────────────────────────────────────────

class PoojaService(Base):
    __tablename__ = "pooja_services"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=True)

    name                = Column(String(255), nullable=False)
    description         = Column(Text,        nullable=True)
    price               = Column(Float,       nullable=True)
    duration_minutes    = Column(Integer,     nullable=True)
    items_included      = Column(Text,        nullable=True)
    priest_requirements = Column(Text,        nullable=True)
    max_persons         = Column(Integer,     nullable=True)
    is_active           = Column(Boolean,     default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple   = relationship("Temple",      back_populates="pooja_services")
    slots    = relationship("PoojaSlot",   back_populates="pooja_service", cascade="all, delete-orphan")
    bookings = relationship("PoojaBooking", back_populates="pooja_service")

    def __repr__(self) -> str:
        return f"<PoojaService {self.name} temple={self.temple_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Slot
# ─────────────────────────────────────────────────────────────────────────────

class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id        = Column(UUID(as_uuid=True), ForeignKey("temples.id"),       nullable=True)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"), nullable=True)

    slot_date    = Column(Date,    nullable=True)
    start_time   = Column(Time,    nullable=True)
    end_time     = Column(Time,    nullable=True)
    total_quota  = Column(Integer, nullable=True)
    booked_count = Column(Integer, default=0)
    is_active    = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pooja_service = relationship("PoojaService", back_populates="slots")
    bookings      = relationship("PoojaBooking", back_populates="slot")

    @property
    def available_count(self) -> int:
        return max(0, (self.total_quota or 0) - (self.booked_count or 0))

    @property
    def is_full(self) -> bool:
        return (self.booked_count or 0) >= (self.total_quota or 0)

    def __repr__(self) -> str:
        return f"<PoojaSlot {self.slot_date} {self.start_time}>"


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Booking
# Fixed: 7 columns corrected/added — see module docstring above.
# ─────────────────────────────────────────────────────────────────────────────

class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, unique=True,
    )
    temple_id        = Column(UUID(as_uuid=True), ForeignKey("temples.id"),        nullable=True)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"), nullable=True)
    slot_id          = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id"),    nullable=True)

    # ── Corrected / added columns ──────────────────────────────────────────
    pooja_date           = Column(Date,         nullable=True)   # was missing
    pooja_time           = Column(Time,         nullable=True)   # was missing
    devotee_names        = Column(JSONB,        nullable=True)   # was devotee_name (singular String)
    gothram              = Column(String(100),  nullable=True)   # was gotram (spelling mismatch)
    nakshatra            = Column(String(100),  nullable=True)   # was missing entirely
    special_instructions = Column(Text,         nullable=True)   # was special_requests
    price                = Column(Numeric(10,2),nullable=True)   # was total_amount (Float)

    # ── Kept from original ─────────────────────────────────────────────────
    num_persons       = Column(Integer,     default=1)
    booking_reference = Column(
        String(20),
        default=lambda: generate_reference("POJ"),
        unique=True,
        nullable=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking       = relationship("Booking",      back_populates="pooja_booking")
    temple        = relationship("Temple",        back_populates="pooja_bookings")
    pooja_service = relationship("PoojaService",  back_populates="bookings")
    slot          = relationship("PoojaSlot",     back_populates="bookings")

    def __repr__(self) -> str:
        return f"<PoojaBooking service={self.pooja_service_id} date={self.pooja_date}>"


# ─────────────────────────────────────────────────────────────────────────────
# Prasadam Item
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=True)

    name         = Column(String(255), nullable=True)
    description  = Column(Text,        nullable=True)
    price        = Column(Float,       nullable=True)
    weight_grams = Column(Integer,     nullable=True)
    image_url    = Column(String(500), nullable=True)
    is_available = Column(Boolean,     default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple      = relationship("Temple",           back_populates="prasadam_items")
    order_items = relationship(
        "PrasadamOrderItem", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PrasadamItem {self.name} ₹{self.price}>"


# ─────────────────────────────────────────────────────────────────────────────
# Prasadam Order
# Fixed: 7 columns added — see module docstring above.
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False
    )
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=True)

    # ── Columns that booking_repo writes — were absent from original model ──
    prasadam_item_id    = Column(UUID(as_uuid=True), nullable=True)   # item being ordered
    quantity            = Column(Integer,            nullable=True, default=1)
    unit_price          = Column(Numeric(10, 2),     nullable=True)
    total_price         = Column(Numeric(10, 2),     nullable=True)
    delivery_address_id = Column(UUID(as_uuid=True), nullable=True)   # None = pickup at temple
    delivery_status     = Column(String(20),         nullable=True, default="pending")
    tracking_number     = Column(String(100),        nullable=True)

    # ── Kept from original ─────────────────────────────────────────────────
    order_reference = Column(
        String(20),
        default=lambda: generate_reference("PRS"),
        unique=True,
        nullable=True,
    )
    pickup_date = Column(Date,      nullable=True)
    total_amount = Column(Float,    nullable=True)   # kept for backward compat
    status      = Column(String(20), default="PENDING")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking", back_populates="prasadam_orders")
    temple  = relationship("Temple",  back_populates="prasadam_orders")
    items   = relationship(
        "PrasadamOrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PrasadamOrder ref={self.order_reference} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# Prasadam Order Item
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamOrderItem(Base):
    __tablename__ = "prasadam_order_items"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id"), nullable=True)
    item_id  = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id"),  nullable=True)

    quantity   = Column(Integer, default=1)
    unit_price = Column(Float,   nullable=True)
    subtotal   = Column(Float,   nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("PrasadamOrder", back_populates="items")
    item  = relationship("PrasadamItem",  back_populates="order_items")

    def __repr__(self) -> str:
        return f"<PrasadamOrderItem item={self.item_id} qty={self.quantity}>"