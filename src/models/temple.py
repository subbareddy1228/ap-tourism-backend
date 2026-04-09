import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Date, Time, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.core.database import Base


# ─────────────────────────────────────────────
# Temple
# GET /            — List all temples
# GET /featured    — Featured, cached 1hr
# GET /popular     — Sorted by booking_count
# GET /nearby      — Near lat/lng within radius_km
# GET /by-deity    — Filter by deity
# GET /by-district — Filter by AP district
# GET /{id}        — Full detail
# GET /{id}/images — S3 images
# GET /{id}/timings — Day-wise schedule
# POST /           — Admin: Add temple
# PUT /{id}        — Admin: Update temple
# ─────────────────────────────────────────────
class Temple(Base):
    __tablename__ = "temples"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(255), nullable=False, index=True)
    description    = Column(Text, nullable=True)
    deity          = Column(String(100), nullable=False, index=True)
    district       = Column(String(100), nullable=False, index=True)
    address        = Column(Text, nullable=True)
    latitude       = Column(Float, nullable=True)
    longitude      = Column(Float, nullable=True)
    dress_code     = Column(Text, nullable=True)
    contact_number = Column(String(20), nullable=True)
    website        = Column(String(300), nullable=True)
    timings        = Column(JSONB, server_default='{}')
    images         = Column(JSONB, server_default='[]')
    is_featured    = Column(Boolean, default=False, nullable=False)
    booking_count  = Column(Integer, default=0, nullable=False)
    is_active      = Column(Boolean, default=True, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events           = relationship("TempleEvent",      back_populates="temple", cascade="all, delete-orphan")
    reviews          = relationship("TempleReview",     back_populates="temple", cascade="all, delete-orphan")
    darshan_types    = relationship("DarshanType", back_populates="temple", cascade="all, delete-orphan")
    darshan_slots    = relationship("DarshanSlot",      back_populates="temple", cascade="all, delete-orphan")
    darshan_bookings = relationship("DarshanBooking",   back_populates="temple", cascade="all, delete-orphan")
    pooja_services   = relationship("PoojaService",     back_populates="temple", cascade="all, delete-orphan")
    pooja_bookings   = relationship("PoojaBooking",     back_populates="temple", cascade="all, delete-orphan")
    prasadam_items   = relationship("PrasadamItem",     back_populates="temple", cascade="all, delete-orphan")
    prasadam_orders  = relationship("PrasadamOrder",    back_populates="temple", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Temple Event
# GET /{id}/events — Upcoming events and festivals
# ─────────────────────────────────────────────
class TempleEvent(Base):
    __tablename__ = "temple_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id   = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_date  = Column(Date, nullable=False)
    start_time  = Column(Time, nullable=True)
    end_time    = Column(Time, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple = relationship("Temple", back_populates="events")


# ─────────────────────────────────────────────
# Temple Review
# GET /{id}/reviews — Visitor reviews for temple
# ─────────────────────────────────────────────
class TempleReview(Base):
    __tablename__ = "temple_reviews"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id   = Column(UUID(as_uuid=True), ForeignKey("temples.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating      = Column(Float, nullable=False)
    title       = Column(String(255), nullable=True)
    body        = Column(Text, nullable=True)
    visit_date  = Column(Date, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    temple = relationship("Temple", back_populates="reviews")


class TemplePoojaService(Base):
    __tablename__ = "temple_pooja_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temple_id = Column(UUID(as_uuid=True), ForeignKey("temples.id"))
    name = Column(String)
    price = Column(Float)
    duration_minutes = Column(Integer)
    description = Column(Text)