"""
models/darshan.py  —  Temple / Darshan / Pooja / Prasadam Module

Bugs fixed vs project file:
──────────────────────────────────────────────────────────────────────────────
  BUG-1  DarshanBooking.booking_id  — was nullable=False (NOT NULL) but
         darshan_service.book_darshan() never passes booking_id, which causes
         an IntegrityError on every direct darshan booking.  Changed to
         nullable=True so the temple-side booking path works without a master
         Booking record. The booking_service.book_darshan() path which DOES
         create a master Booking first can still populate this FK.

  BUG-2  PrasadamOrder.user_id — The column was ABSENT from the model but
         darshan_service.order_prasadam() writes `user_id=user_id` to the
         PrasadamOrder constructor, and darshan_repo.get_prasadam_orders_by_user()
         filters on PrasadamOrder.user_id.  Both calls raise AttributeError
         at runtime.  Added user_id column.

  BUG-3  PoojaBooking.booking_id — same as BUG-1: nullable=False but
         darshan_service.book_pooja() never passes booking_id. Changed to
         nullable=True.

  BUG-4  DarshanBooking — missing Index on temple_id for performance.
         All other booking tables index temple_id.  Added.

  BUG-5  PrasadamOrder — missing Index on temple_id and user_id. Added.

  All new / changed columns are nullable=True so the existing Alembic
  migration can apply on live data without touching existing rows.
"""

import uuid
import random
import string
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, ForeignKey, Numeric, Index,
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

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(
        UUID(as_uuid=True),
        ForeignKey("temples.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name                    = Column(String(100), nullable=False)
    darshan_type            = Column(String(50),  nullable=False, index=True)
    description             = Column(Text,        nullable=True)
    price                   = Column(Float,       default=0.0)
    duration_minutes        = Column(Integer,     default=30)
    what_is_included        = Column(Text,        nullable=True)
    max_persons_per_booking = Column(Integer,     default=6)
    is_active               = Column(Boolean,     default=True)

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
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id"),        nullable=False, index=True)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"),  nullable=False, index=True)

    slot_date  = Column(Date,    nullable=False)
    start_time = Column(Time,    nullable=False)
    end_time   = Column(Time,    nullable=False)

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

    __table_args__ = (
        Index("ix_darshan_slots_temple_date", "temple_id", "slot_date"),
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

    # BUG-1 FIX: Changed nullable=False → nullable=True.
    # The temple-side darshan booking path (darshan_service.book_darshan)
    # does NOT create a master Booking first, so booking_id is unavailable
    # at insert time and the NOT NULL constraint caused IntegrityError on
    # every booking attempt via this path.
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=True,      # was nullable=False — caused IntegrityError
        unique=True,
        index=True,
    )

    # BUG-4 FIX: Added index on temple_id (was missing)
    temple_id       = Column(UUID(as_uuid=True), ForeignKey("temples.id"),        nullable=False, index=True)
    darshan_slot_id = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id"),  nullable=True,  index=True)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"),  nullable=True,  index=True)

    darshan_date = Column(Date, nullable=False)
    darshan_time = Column(Time, nullable=False)

    num_persons      = Column(Integer,        nullable=False)
    price_per_person = Column(Numeric(10, 2), nullable=False)
    total_price      = Column(Numeric(10, 2), nullable=False)

    devotee_details = Column(JSONB,      nullable=True)
    ticket_number   = Column(String(50), unique=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking",     back_populates="darshan_booking")
    temple  = relationship("Temple",      back_populates="darshan_bookings")
    slot    = relationship("DarshanSlot", back_populates="bookings")
    # prasadam_orders = relationship("PrasadamOrder", back_populates="booking")
    def __repr__(self) -> str:
        return f"<DarshanBooking date={self.darshan_date} persons={self.num_persons}>"


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Service
# ─────────────────────────────────────────────────────────────────────────────

class PoojaService(Base):
    __tablename__ = "pooja_services"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=True, index=True)

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

    temple   = relationship("Temple",       back_populates="pooja_services")
    slots    = relationship("PoojaSlot",    back_populates="pooja_service", cascade="all, delete-orphan")
    bookings = relationship("PoojaBooking", back_populates="pooja_service")

    def __repr__(self) -> str:
        return f"<PoojaService {self.name} temple={self.temple_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Slot
# ─────────────────────────────────────────────────────────────────────────────

class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id        = Column(UUID(as_uuid=True), ForeignKey("temples.id"),        nullable=True, index=True)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"), nullable=True, index=True)

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
# ─────────────────────────────────────────────────────────────────────────────

class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # BUG-3 FIX: Changed nullable=False → nullable=True.
    # Same issue as DarshanBooking — darshan_service.book_pooja() never
    # creates/passes booking_id, causing IntegrityError at INSERT.
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=True,      # was nullable=False — caused IntegrityError
        unique=True,
        index=True,
    )

    temple_id        = Column(UUID(as_uuid=True), ForeignKey("temples.id"),         nullable=True, index=True)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"),  nullable=True, index=True)
    slot_id          = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id"),     nullable=True)

    # Corrected columns (from previous batch — kept intact)
    pooja_date           = Column(Date,          nullable=True)
    pooja_time           = Column(Time,          nullable=True)
    devotee_names        = Column(JSONB,         nullable=True)
    gothram              = Column(String(100),   nullable=True)
    nakshatra            = Column(String(100),   nullable=True)
    special_instructions = Column(Text,          nullable=True)
    price                = Column(Numeric(10,2), nullable=True)

    num_persons       = Column(Integer, default=1)
    booking_reference = Column(
        String(20),
        default=lambda: generate_reference("POJ"),
        unique=True,
        nullable=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking       = relationship("Booking",      back_populates="pooja_booking")
    temple        = relationship("Temple",       back_populates="pooja_bookings")
    pooja_service = relationship("PoojaService", back_populates="bookings")
    slot          = relationship("PoojaSlot",    back_populates="bookings")

    def __repr__(self) -> str:
        return f"<PoojaBooking service={self.pooja_service_id} date={self.pooja_date}>"


# ─────────────────────────────────────────────────────────────────────────────
# Prasadam Item
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=True, index=True)

    name         = Column(String(255), nullable=True)
    description  = Column(Text,        nullable=True)
    price        = Column(Float,       nullable=True)
    weight_grams = Column(Integer,     nullable=True)
    image_url    = Column(String(500), nullable=True)
    is_available = Column(Boolean,     default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple      = relationship("Temple",            back_populates="prasadam_items")
    order_items = relationship(
        "PrasadamOrderItem", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PrasadamItem {self.name} ₹{self.price}>"


# ─────────────────────────────────────────────────────────────────────────────
# Prasadam Order
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True)
    temple_id  = Column(UUID(as_uuid=True), ForeignKey("temples.id"),  nullable=True, index=True)

    # BUG-2 FIX: Added user_id column.
    # darshan_service.order_prasadam() passes user_id=user_id to the
    # PrasadamOrder constructor, and darshan_repo.get_prasadam_orders_by_user()
    # filters on PrasadamOrder.user_id == user_id.  Both raise AttributeError
    # without this column.
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)   # BUG-2 FIX

    # BUG-5 FIX: Added composite index on (temple_id, user_id) for the
    # "my orders" query which filters on both columns.
    __table_args__ = (
        Index("ix_prasadam_orders_temple_user", "temple_id", "user_id"),
    )

    # Columns added in previous batch — kept intact
    prasadam_item_id    = Column(UUID(as_uuid=True), nullable=True)
    quantity            = Column(Integer,            nullable=True, default=1)
    unit_price          = Column(Numeric(10, 2),     nullable=True)
    total_price         = Column(Numeric(10, 2),     nullable=True)
    

    order_reference = Column(
        String(20),
        default=lambda: generate_reference("PRS"),
        unique=True,
        nullable=True,
    )
    pickup_date  = Column(Date,    nullable=True)
    total_amount = Column(Float,   nullable=True)
    status       = Column(String(20), default="PENDING")

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
    order_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id"), nullable=True, index=True)
    item_id  = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id"),  nullable=True, index=True)

    quantity   = Column(Integer, default=1)
    unit_price = Column(Float,   nullable=True)
    subtotal   = Column(Float,   nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("PrasadamOrder", back_populates="items")
    item  = relationship("PrasadamItem",  back_populates="order_items")

    def __repr__(self) -> str:
        return f"<PrasadamOrderItem item={self.item_id} qty={self.quantity}>"
