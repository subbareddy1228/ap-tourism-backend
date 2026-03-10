import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, JSON, Enum as SAEnum,
    ForeignKey, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.models.temple import DarshanType, BookingStatus


# ─────────────────────────────────────────────
# Darshan Type (e.g. FREE, VIP, SUPRABHATA)
# ─────────────────────────────────────────────
class DarshanTypeModel(Base):
    __tablename__ = "darshan_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(SAEnum(DarshanType), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), default=0.00)
    duration_minutes = Column(Integer)
    what_is_included = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    temple = relationship("Temple", back_populates="darshan_types")
    slots = relationship("DarshanSlot", back_populates="darshan_type", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Darshan Slot (date + time block)
# ─────────────────────────────────────────────
class DarshanSlot(Base):
    __tablename__ = "darshan_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_quota = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    temple = relationship("Temple", back_populates="darshan_slots")
    darshan_type = relationship("DarshanTypeModel", back_populates="slots")
    bookings = relationship("DarshanBooking", back_populates="slot", cascade="all, delete-orphan")

    @property
    def available_count(self):
        return self.total_quota - self.booked_count

    @property
    def is_full(self):
        return self.booked_count >= self.total_quota


# ─────────────────────────────────────────────
# Darshan Booking
# ─────────────────────────────────────────────
class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    devotees_count = Column(Integer, nullable=False, default=1)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2), default=0.00)
    payment_id = Column(String(255))
    qr_code = Column(Text)                  # Base64 or S3 URL
    booking_reference = Column(String(50), unique=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    slot = relationship("DarshanSlot", back_populates="bookings")


# ─────────────────────────────────────────────
# Pooja / Seva Service
# ─────────────────────────────────────────────
class PoojaService(Base):
    __tablename__ = "pooja_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer)
    items_included = Column(Text)
    priest_requirements = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    temple = relationship("Temple", back_populates="pooja_services")
    slots = relationship("PoojaSlot", back_populates="pooja_service", cascade="all, delete-orphan")
    bookings = relationship("PoojaBooking", back_populates="pooja_service")


# ─────────────────────────────────────────────
# Pooja Slot
# ─────────────────────────────────────────────
class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_quota = Column(Integer, default=1)
    booked_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    pooja_service = relationship("PoojaService", back_populates="slots")
    bookings = relationship("PoojaBooking", back_populates="slot")

    @property
    def available_count(self):
        return self.total_quota - self.booked_count


# ─────────────────────────────────────────────
# Pooja Booking
# ─────────────────────────────────────────────
class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pooja_service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2))
    payment_id = Column(String(255))
    booking_reference = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pooja_service = relationship("PoojaService", back_populates="bookings")
    slot = relationship("PoojaSlot", back_populates="bookings")


# ─────────────────────────────────────────────
# Prasadam Item
# ─────────────────────────────────────────────
class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500))
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    temple = relationship("Temple", back_populates="prasadam_items")
    order_items = relationship("PrasadamOrderItem", back_populates="prasadam_item")


# ─────────────────────────────────────────────
# Prasadam Order
# ─────────────────────────────────────────────
class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2), default=0.00)
    payment_id = Column(String(255))
    pickup_date = Column(Date)
    booking_reference = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = relationship("PrasadamOrderItem", back_populates="order", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Prasadam Order Item
# ─────────────────────────────────────────────
class PrasadamOrderItem(Base):
    __tablename__ = "prasadam_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id", ondelete="CASCADE"), nullable=False)
    prasadam_item_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("PrasadamOrder", back_populates="order_items")
    prasadam_item = relationship("PrasadamItem", back_populates="order_items")