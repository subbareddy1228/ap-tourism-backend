import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, JSON, Enum as SAEnum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum


class DarshanType(str, enum.Enum):
    FREE = "FREE"
    SPECIAL_ENTRY = "SPECIAL_ENTRY"
    SUPRABHATA = "SUPRABHATA"
    VIP = "VIP"


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Temple(Base):
    __tablename__ = "temples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    deity = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    is_featured = Column(Boolean, default=False)
    booking_count = Column(Integer, default=0)
    dress_code = Column(Text)
    timings = Column(JSON)           # {"monday": {"open": "06:00", "close": "20:00"}, ...}
    images = Column(JSON, default=list)  # list of S3 URLs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships — use strings to avoid circular imports
    darshan_types = relationship("DarshanTypeModel", back_populates="temple", cascade="all, delete-orphan")
    darshan_slots = relationship("DarshanSlot", back_populates="temple", cascade="all, delete-orphan")
    pooja_services = relationship("PoojaService", back_populates="temple", cascade="all, delete-orphan")
    prasadam_items = relationship("PrasadamItem", back_populates="temple", cascade="all, delete-orphan")
    events = relationship("TempleEvent", back_populates="temple", cascade="all, delete-orphan")
    reviews = relationship("TempleReview", back_populates="temple", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Temple Event
# ─────────────────────────────────────────────
class TempleEvent(Base):
    __tablename__ = "temple_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    event_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    temple = relationship("Temple", back_populates="events")


# ─────────────────────────────────────────────
# Temple Review
# ─────────────────────────────────────────────
class TempleReview(Base):
    __tablename__ = "temple_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(Float, nullable=False)          # 1.0 - 5.0
    title = Column(String(255))
    body = Column(Text)
    visit_date = Column(Date)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # temple = relationship("Temple", back_populates="reviews")