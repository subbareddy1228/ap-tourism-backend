import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Time, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.temple import DarshanType, BookingStatus


class DarshanTypeModel(Base):
    __tablename__ = "darshan_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    darshan_type = Column(SAEnum(DarshanType), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0.0)
    duration_minutes = Column(Integer, default=30)
    max_persons_per_booking = Column(Integer, default=6)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="darshan_types")
    slots = relationship("DarshanSlot", back_populates="darshan_type", cascade="all, delete-orphan")


class DarshanSlot(Base):
    __tablename__ = "darshan_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    darshan_type_id = Column(UUID(as_uuid=True), ForeignKey("darshan_types.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_quota = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="darshan_slots")
    darshan_type = relationship("DarshanTypeModel", back_populates="slots")
    bookings = relationship("DarshanBooking", back_populates="slot", cascade="all, delete-orphan")

    @property
    def available_quota(self):
        return self.total_quota - self.booked_count


class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("darshan_slots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    booking_reference = Column(String(20), unique=True, nullable=False)
    num_persons = Column(Integer, nullable=False, default=1)
    total_amount = Column(Float, default=0.0)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)
    payment_id = Column(String(100), nullable=True)
    qr_code = Column(Text, nullable=True)
    pilgrim_details = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="darshan_bookings")
    slot = relationship("DarshanSlot", back_populates="bookings")


class PoojaService(Base):
    __tablename__ = "pooja_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer, default=30)
    max_persons = Column(Integer, default=10)
    requires_priest = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="pooja_services")
    slots = relationship("PoojaSlot", back_populates="service", cascade="all, delete-orphan")
    bookings = relationship("PoojaBooking", back_populates="service", cascade="all, delete-orphan")


class PoojaSlot(Base):
    __tablename__ = "pooja_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_quota = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    service = relationship("PoojaService", back_populates="slots")
    bookings = relationship("PoojaBooking", back_populates="slot", cascade="all, delete-orphan")


class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("pooja_services.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("pooja_slots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    booking_reference = Column(String(20), unique=True, nullable=False)
    num_persons = Column(Integer, nullable=False, default=1)
    total_amount = Column(Float, default=0.0)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)
    payment_id = Column(String(100), nullable=True)
    special_requests = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="pooja_bookings")
    service = relationship("PoojaService", back_populates="bookings")
    slot = relationship("PoojaSlot", back_populates="bookings")


class PrasadamItem(Base):
    __tablename__ = "prasadam_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    weight_grams = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="prasadam_items")
    order_items = relationship("PrasadamOrderItem", back_populates="item", cascade="all, delete-orphan")


class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    order_reference = Column(String(20), unique=True, nullable=False)
    total_amount = Column(Float, default=0.0)
    pickup_date = Column(Date, nullable=True)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)
    payment_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    temple = relationship("Temple", back_populates="prasadam_orders")
    items = relationship("PrasadamOrderItem", back_populates="order", cascade="all, delete-orphan")


class PrasadamOrderItem(Base):
    __tablename__ = "prasadam_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_orders.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("prasadam_items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relationships
    order = relationship("PrasadamOrder", back_populates="items")
    item = relationship("PrasadamItem", back_populates="order_items")