import uuid
import random
import string
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, ForeignKey, Numeric
)

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.core.database import Base


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def generate_reference(prefix: str) -> str:
    today = date.today().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{today}-{suffix}"


# ---------------------------------------------------------
# Darshan Type
# ---------------------------------------------------------

class DarshanType(Base):
    __tablename__ = "darshan_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    temple_id = Column(
        UUID(as_uuid=True),
        ForeignKey("temples.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name = Column(String(100), nullable=False)
    darshan_type = Column(String(50), nullable=False, index=True)

    description = Column(Text)
    price = Column(Float, default=0.0)
    duration_minutes = Column(Integer, default=30)

    what_is_included = Column(Text)

    max_persons_per_booking = Column(Integer, default=6)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple = relationship("Temple", back_populates="darshan_types")

    slots = relationship(
        "DarshanSlot",
        back_populates="darshan_type",
        cascade="all, delete-orphan"
    )


# ---------------------------------------------------------
# Darshan Slot
# ---------------------------------------------------------

class DarshanSlot(Base):
    __tablename__ = "darshan_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=False)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"), nullable=False)

    slot_date = Column(Date, nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    total_quota = Column(Integer, nullable=False)

    booked_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple = relationship("Temple", back_populates="darshan_slots")

    darshan_type = relationship("DarshanType", back_populates="slots")

    bookings = relationship(
        "DarshanBooking",
        back_populates="slot",
        cascade="all, delete-orphan"
    )

    @property
    def available_count(self):
        return max(0, self.total_quota - self.booked_count)

    @property
    def is_full(self):
        return self.booked_count >= self.total_quota


# ---------------------------------------------------------
# Darshan Booking
# ---------------------------------------------------------

class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"), nullable=False)

    darshan_slot_id = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id"))

    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id"))

    darshan_date = Column(Date, nullable=False)
    darshan_time = Column(Time, nullable=False)

    num_persons = Column(Integer, nullable=False)

    price_per_person = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    devotee_details = Column(JSONB)

    ticket_number = Column(String(50), unique=True)

    booking = relationship("Booking", back_populates="darshan_booking")

    temple = relationship("Temple", back_populates="darshan_bookings")

    slot = relationship("DarshanSlot", back_populates="bookings")


# ---------------------------------------------------------
# Pooja Service
# ---------------------------------------------------------

class PoojaService(Base):
    __tablename__ = "pooja_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))

    name = Column(String(255), nullable=False)

    description = Column(Text)

    price = Column(Float)

    duration_minutes = Column(Integer)

    items_included = Column(Text)

    priest_requirements = Column(Text)

    max_persons = Column(Integer)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple = relationship("Temple", back_populates="pooja_services")

    slots = relationship(
        "PoojaSlot",
        back_populates="pooja_service",
        cascade="all, delete-orphan"
    )

    bookings = relationship(
        "PoojaBooking",
        back_populates="pooja_service"
    )


# ---------------------------------------------------------
# Pooja Slot
# ---------------------------------------------------------

class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))

    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"))

    slot_date = Column(Date)

    start_time = Column(Time)

    end_time = Column(Time)

    total_quota = Column(Integer)

    booked_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pooja_service = relationship("PoojaService", back_populates="slots")

    bookings = relationship("PoojaBooking", back_populates="slot")


# ---------------------------------------------------------
# Pooja Booking
# ---------------------------------------------------------

class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, unique=True)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))

    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id"))

    slot_id = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id"))

    user_id = Column(UUID(as_uuid=True), nullable=False)

    booking_reference = Column(
        String(20),
        default=lambda: generate_reference("POJ"),
        unique=True
    )

    num_persons = Column(Integer, default=1)

    total_amount = Column(Float)

    status = Column(String(20), default="PENDING")

    payment_id = Column(String(100))

    devotee_name = Column(String(255))

    gotram = Column(String(100))

    special_requests = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking", back_populates="pooja_booking")

    temple = relationship("Temple", back_populates="pooja_bookings")

    pooja_service = relationship("PoojaService", back_populates="bookings")

    slot = relationship("PoojaSlot", back_populates="bookings")


# ---------------------------------------------------------
# Prasadam Item
# ---------------------------------------------------------

class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))

    name = Column(String(255))

    description = Column(Text)

    price = Column(Float)

    weight_grams = Column(Integer)

    image_url = Column(String(500))

    is_available = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    temple = relationship("Temple", back_populates="prasadam_items")

    order_items = relationship(
        "PrasadamOrderItem",
        back_populates="item",
        cascade="all, delete-orphan"
    )


# ---------------------------------------------------------
# Prasadam Order
# ---------------------------------------------------------

class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)

    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))

    user_id = Column(UUID(as_uuid=True))

    order_reference = Column(
        String(20),
        default=lambda: generate_reference("PRS"),
        unique=True
    )

    total_amount = Column(Float)

    pickup_date = Column(Date)

    status = Column(String(20), default="PENDING")

    payment_id = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking", back_populates="prasadam_orders")

    temple = relationship("Temple", back_populates="prasadam_orders")

    items = relationship(
        "PrasadamOrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )


# ---------------------------------------------------------
# Prasadam Order Item
# ---------------------------------------------------------

class PrasadamOrderItem(Base):
    __tablename__ = "prasadam_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    order_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id"))

    item_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id"))

    quantity = Column(Integer, default=1)

    unit_price = Column(Float)

    subtotal = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("PrasadamOrder", back_populates="items")

    item = relationship("PrasadamItem", back_populates="order_items")