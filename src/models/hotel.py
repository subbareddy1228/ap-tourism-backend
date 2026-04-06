"""
models/hotel.py
Hotel module models:
  - Hotel           (main hotel listing — owned by a Partner)
  - HotelRoom       (room types per hotel)
  - HotelImage      (S3 image gallery)
  - HotelAmenity    (amenities list)
  - HotelRoomBooking (room availability blocks — linked later to Booking module)

Changes (admin approval fix):
  - Hotel.admin_note      — stores admin's internal note on review (new)
  - Hotel.rejection_reason — stores reason when admin rejects (new)
  - Hotel.reviewed_at     — timestamp when admin took action (new)
  - Hotel.reviewed_by     — FK to users.id of the admin who reviewed (new)
  - Hotel.is_active default changed to False so a PENDING hotel is
    never publicly visible until approved (was True — bug)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Numeric, Integer, Date
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base


# ══════════════════ HOTEL ══════════════════

class Hotel(Base):
    __tablename__ = "hotels"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    partner_id          = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Basic Info ────────────────────────────────────────────
    name                = Column(String(200), nullable=False)
    description         = Column(Text, nullable=True)
    star_rating         = Column(Integer, default=3, nullable=False)
    # 1 | 2 | 3 | 4 | 5

    hotel_type          = Column(String(50), default="HOTEL", nullable=False)
    # HOTEL | RESORT | HOMESTAY | GUESTHOUSE | DHARAMSHALA

    # ── Location ──────────────────────────────────────────────
    address             = Column(Text, nullable=False)
    city                = Column(String(100), nullable=False)
    state               = Column(String(100), nullable=False)
    pincode             = Column(String(10), nullable=True)
    latitude            = Column(Float, nullable=True)
    longitude           = Column(Float, nullable=True)
    distance_from_temple = Column(Float, nullable=True)  # in km

    # ── Contact ───────────────────────────────────────────────
    contact_phone       = Column(String(15), nullable=True)
    contact_email       = Column(String(255), nullable=True)
    website             = Column(String(255), nullable=True)

    # ── Policies ──────────────────────────────────────────────
    check_in_time       = Column(String(10), default="12:00", nullable=False)   # "12:00"
    check_out_time      = Column(String(10), default="11:00", nullable=False)   # "11:00"
    cancellation_policy = Column(Text, nullable=True)
    pet_policy          = Column(String(20), default="NOT_ALLOWED", nullable=False)
    # NOT_ALLOWED | ALLOWED | ON_REQUEST

    # ── Meal Options ──────────────────────────────────────────
    meal_options        = Column(JSON, default=list, nullable=True)
    # ["ROOM_ONLY", "BED_BREAKFAST", "HALF_BOARD", "FULL_BOARD"]

    # ── Status ────────────────────────────────────────────────
    # IMPORTANT: is_active is False by default so a new PENDING hotel is
    # never publicly visible. Admin approval sets it to True.
    is_active           = Column(Boolean, default=False, nullable=False)
    is_featured         = Column(Boolean, default=False, nullable=False)
    status              = Column(String(20), default="PENDING", nullable=False)
    # PENDING | ACTIVE | INACTIVE | REJECTED

    # ── Admin Review Tracking ─────────────────────────────────
    rejection_reason    = Column(Text, nullable=True)
    admin_note          = Column(Text, nullable=True)        # internal note, not shown to partner
    reviewed_at         = Column(DateTime, nullable=True)
    reviewed_by         = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Pricing ───────────────────────────────────────────────
    base_price          = Column(Numeric(10, 2), nullable=True)   # lowest room price

    # ── Stats ─────────────────────────────────────────────────
    rating              = Column(Float, default=0.0, nullable=True)
    total_reviews       = Column(Integer, default=0, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────
    partner             = relationship("Partner",      foreign_keys=[partner_id])
    reviewed_by_user    = relationship("User",         foreign_keys=[reviewed_by])
    rooms               = relationship("HotelRoom",    back_populates="hotel", cascade="all, delete-orphan")
    images              = relationship("HotelImage",   back_populates="hotel", cascade="all, delete-orphan")
    amenities           = relationship("HotelAmenity", back_populates="hotel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Hotel {self.name} ({self.city}) status={self.status} stars={self.star_rating}>"


# ══════════════════ HOTEL ROOM ══════════════════

class HotelRoom(Base):
    __tablename__ = "hotel_rooms"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    hotel_id            = Column(UUID(as_uuid=True), ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Room Info ─────────────────────────────────────────────
    room_type           = Column(String(50), nullable=False)
    # STANDARD | DELUXE | SUITE | FAMILY | DORMITORY

    name                = Column(String(100), nullable=True)      # e.g. "Deluxe Temple View"
    description         = Column(Text, nullable=True)
    max_occupancy       = Column(Integer, default=2, nullable=False)
    total_rooms         = Column(Integer, default=1, nullable=False)
    floor_number        = Column(Integer, nullable=True)

    # ── Pricing ───────────────────────────────────────────────
    price_per_night     = Column(Numeric(10, 2), nullable=False)
    weekend_price       = Column(Numeric(10, 2), nullable=True)   # Fri-Sun surge
    extra_bed_price     = Column(Numeric(10, 2), default=0, nullable=False)

    # ── Features ──────────────────────────────────────────────
    bed_type            = Column(String(30), nullable=True)
    # SINGLE | DOUBLE | TWIN | KING | QUEEN

    has_ac              = Column(Boolean, default=True, nullable=False)
    has_wifi            = Column(Boolean, default=True, nullable=False)
    has_tv              = Column(Boolean, default=True, nullable=False)
    has_geyser          = Column(Boolean, default=True, nullable=False)
    is_smoking          = Column(Boolean, default=False, nullable=False)
    amenities           = Column(JSON, default=list, nullable=True)
    # ["MINIBAR", "BALCONY", "TEMPLE_VIEW", "GARDEN_VIEW"]

    # ── Status ────────────────────────────────────────────────
    is_active           = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────
    hotel               = relationship("Hotel", back_populates="rooms")

    def __repr__(self):
        return f"<HotelRoom {self.room_type} ₹{self.price_per_night}/night hotel_id={self.hotel_id}>"


# ══════════════════ HOTEL IMAGE ══════════════════

class HotelImage(Base):
    __tablename__ = "hotel_images"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    hotel_id            = Column(UUID(as_uuid=True), ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)

    image_url           = Column(Text, nullable=False)       # S3 URL
    caption             = Column(String(255), nullable=True)
    category            = Column(String(50), default="EXTERIOR", nullable=False)
    # EXTERIOR | INTERIOR | ROOM | RESTAURANT | POOL | OTHER

    is_primary          = Column(Boolean, default=False, nullable=False)
    display_order       = Column(Integer, default=0, nullable=False)

    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)

    hotel               = relationship("Hotel", back_populates="images")

    def __repr__(self):
        return f"<HotelImage {self.category} primary={self.is_primary}>"


# ══════════════════ HOTEL AMENITY ══════════════════

class HotelAmenity(Base):
    __tablename__ = "hotel_amenities"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    hotel_id            = Column(UUID(as_uuid=True), ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)

    name                = Column(String(100), nullable=False)
    # "Swimming Pool" | "Parking" | "Restaurant" | "Prasadam Counter"
    category            = Column(String(50), nullable=True)
    # GENERAL | WELLNESS | DINING | TRANSPORT | RELIGIOUS | KIDS

    icon                = Column(String(50), nullable=True)   # icon key for frontend
    is_paid             = Column(Boolean, default=False, nullable=False)

    hotel               = relationship("Hotel", back_populates="amenities")

    def __repr__(self):
        return f"<HotelAmenity {self.name} paid={self.is_paid}>"