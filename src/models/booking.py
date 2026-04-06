"""
models/booking.py  —  M11 Booking Module
Author : LEV151 Shree Hari Pappaka

Changes vs original:
  Booking (master)  — 19 columns added:
                       booking_number, booking_date, start_date, end_date,
                       subtotal, discount_amount, tax_amount, convenience_fee,
                       paid_amount, coupon_code, special_requests,
                       contact_details, cancellation_reason, cancelled_at,
                       confirmed_at, completed_at, refund_amount,
                       refund_status, custom_trip_details
  HotelBooking      —  2 columns added: check_in_time, check_out_time
  VehicleBooking    —  7 columns added: actual_km, pickup_lat, pickup_lng,
                       drop_lat, drop_lng, driver_allowance, toll_charges
  GuideBooking      —  1 column  added: destination_id
  BookingTraveler   —  1 column  added: family_member_id
  All nullable=True on new columns so Alembic migration runs on existing rows.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Enum, Date, Time, DateTime,
    Numeric, Integer, Boolean, Text, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.common.enums import BookingType, BookingStatus, PaymentStatus, TripType, Gender


# ─────────────────────────────────────────────────────────────────────────────
# BOOKINGS  (master table)
# ─────────────────────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    booking_type   = Column(Enum(BookingType),   nullable=False)
    status         = Column(Enum(BookingStatus),  default=BookingStatus.PENDING,  nullable=False)
    payment_status = Column(Enum(PaymentStatus),  default=PaymentStatus.PENDING,  nullable=False)
    total_amount   = Column(Numeric(10, 2),       nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ── Previously missing columns (all nullable for safe migration) ──────────

    booking_number      = Column(String(20),    unique=True,  nullable=True)   # APT-YYYYMMDD-XXXX
    booking_date        = Column(Date,                        nullable=True)
    start_date          = Column(Date,                        nullable=True)
    end_date            = Column(Date,                        nullable=True)
    subtotal            = Column(Numeric(10, 2), default=0,   nullable=True)
    discount_amount     = Column(Numeric(10, 2), default=0,   nullable=True)
    tax_amount          = Column(Numeric(10, 2), default=0,   nullable=True)
    convenience_fee     = Column(Numeric(10, 2), default=0,   nullable=True)
    paid_amount         = Column(Numeric(10, 2), default=0,   nullable=True)
    coupon_code         = Column(String(50),                  nullable=True)
    special_requests    = Column(Text,                        nullable=True)
    contact_details     = Column(JSONB,                       nullable=True)   # {name, phone, email}
    cancellation_reason = Column(Text,                        nullable=True)
    cancelled_at        = Column(DateTime,                    nullable=True)
    confirmed_at        = Column(DateTime,                    nullable=True)
    completed_at        = Column(DateTime,                    nullable=True)
    refund_amount       = Column(Numeric(10, 2),              nullable=True)
    refund_status       = Column(String(20),                  nullable=True)   # pending|processed|failed|not_applicable
    custom_trip_details = Column(JSONB,                       nullable=True)   # only for CUSTOM booking type

    # ── Relationships ─────────────────────────────────────────────────────────

    hotel_booking   = relationship("HotelBooking",   back_populates="booking", uselist=False)
    vehicle_booking = relationship("VehicleBooking", back_populates="booking", uselist=False)
    darshan_booking = relationship("DarshanBooking", back_populates="booking", uselist=False)
    pooja_booking   = relationship("PoojaBooking",   back_populates="booking", uselist=False)
    package_booking = relationship("PackageBooking", back_populates="booking", uselist=False)
    guide_booking   = relationship("GuideBooking",   back_populates="booking", uselist=False)

    prasadam_orders = relationship(
        "PrasadamOrder", back_populates="booking", cascade="all, delete-orphan"
    )
    travelers = relationship(
        "BookingTraveler", back_populates="booking", cascade="all, delete-orphan"
    )
    addons = relationship(
        "BookingAddon", back_populates="booking", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_bookings_user_status",    "user_id", "status"),
        Index("ix_bookings_user_type",      "user_id", "booking_type"),
        Index("ix_bookings_payment_status", "payment_status"),
        Index("ix_bookings_start_date",     "start_date"),
        Index("ix_bookings_booking_number", "booking_number"),
    )

    def __repr__(self) -> str:
        return f"<Booking {self.booking_number} type={self.booking_type} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# HOTEL BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

class HotelBooking(Base):
    __tablename__ = "hotel_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, unique=True, index=True,
    )

    hotel_id = Column(UUID(as_uuid=True), nullable=False)
    room_id  = Column(UUID(as_uuid=True), nullable=False)

    check_in_date  = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)

    # Snapshot the hotel's check-in/out times at booking time so the record
    # stays accurate even if the hotel later changes its policy.
    check_in_time  = Column(String(10), nullable=True)   # e.g. "14:00"
    check_out_time = Column(String(10), nullable=True)   # e.g. "11:00"

    rooms_count         = Column(Integer,        default=1)
    adults              = Column(Integer,        default=1)
    children            = Column(Integer,        default=0)
    room_rate_per_night = Column(Numeric(10, 2), nullable=False)
    total_room_charge   = Column(Numeric(10, 2), nullable=False)
    guest_details       = Column(JSONB,          nullable=True)

    booking = relationship("Booking", back_populates="hotel_booking")

    def __repr__(self) -> str:
        return f"<HotelBooking hotel={self.hotel_id} room={self.room_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# VEHICLE BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

class VehicleBooking(Base):
    __tablename__ = "vehicle_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, unique=True, index=True,
    )

    vehicle_id = Column(UUID(as_uuid=True), nullable=False)
    driver_id  = Column(UUID(as_uuid=True), nullable=True)

    trip_type       = Column(Enum(TripType), nullable=False)
    pickup_location = Column(String(500),    nullable=False)
    drop_location   = Column(String(500),    nullable=False)

    pickup_datetime = Column(DateTime, nullable=False)
    return_datetime = Column(DateTime, nullable=True)

    estimated_km = Column(Numeric(10, 2), nullable=True)

    # GPS coordinates (used by Google Maps routing)
    actual_km        = Column(Numeric(10, 2), nullable=True)   # filled by driver after trip
    pickup_lat       = Column(Numeric(10, 7), nullable=True)
    pickup_lng       = Column(Numeric(10, 7), nullable=True)
    drop_lat         = Column(Numeric(10, 7), nullable=True)
    drop_lng         = Column(Numeric(10, 7), nullable=True)
    driver_allowance = Column(Numeric(10, 2), nullable=True, default=0)
    toll_charges     = Column(Numeric(10, 2), nullable=True, default=0)

    rate_per_km   = Column(Numeric(10, 2), nullable=False)
    total_charge  = Column(Numeric(10, 2), nullable=False)
    route_details = Column(JSONB,          nullable=True)

    booking = relationship("Booking", back_populates="vehicle_booking")

    def __repr__(self) -> str:
        return f"<VehicleBooking vehicle={self.vehicle_id} trip={self.trip_type}>"


# ─────────────────────────────────────────────────────────────────────────────
# PACKAGE BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

class PackageBooking(Base):
    __tablename__ = "package_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, unique=True, index=True,
    )

    package_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    start_date   = Column(Date,          nullable=False)
    end_date     = Column(Date,          nullable=False)
    num_adults   = Column(Integer,       default=1)
    num_children = Column(Integer,       default=0)

    package_price  = Column(Numeric(10, 2), nullable=False)
    addon_charges  = Column(Numeric(10, 2), default=0)
    total_price    = Column(Numeric(10, 2), nullable=False)
    customizations = Column(JSONB,          nullable=True)

    booking = relationship("Booking", back_populates="package_booking")

    def __repr__(self) -> str:
        return f"<PackageBooking package={self.package_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# GUIDE BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

class GuideBooking(Base):
    __tablename__ = "guide_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, unique=True, index=True,
    )

    guide_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # destination_id was being passed by BookGuideRequest and booking_service
    # but had no corresponding column — silently lost on every guide booking.
    destination_id = Column(UUID(as_uuid=True), nullable=True)

    start_date = Column(Date, nullable=False)
    end_date   = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time   = Column(Time, nullable=True)

    num_hours = Column(Integer,       nullable=True)
    num_days  = Column(Integer,       nullable=True)
    rate      = Column(Numeric(10, 2), nullable=False)
    total_charge = Column(Numeric(10, 2), nullable=False)

    meeting_point      = Column(String(500), nullable=True)
    locations_to_cover = Column(JSONB,       nullable=True)

    booking = relationship("Booking", back_populates="guide_booking")

    def __repr__(self) -> str:
        return f"<GuideBooking guide={self.guide_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING TRAVELERS
# ─────────────────────────────────────────────────────────────────────────────

class BookingTraveler(Base):
    __tablename__ = "booking_travelers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, index=True,
    )

    # booking_repo.create_booking_travelers() always writes family_member_id
    # but the column was absent — caused AttributeError on every traveler INSERT.
    family_member_id = Column(UUID(as_uuid=True), nullable=True)

    name            = Column(String(100), nullable=False)
    age             = Column(Integer,     nullable=False)
    gender          = Column(Enum(Gender), nullable=True)
    id_proof_type   = Column(String(50),  nullable=True)
    id_proof_number = Column(String(100), nullable=True)
    is_primary      = Column(Boolean,     default=False)

    booking = relationship("Booking", back_populates="travelers")

    def __repr__(self) -> str:
        return f"<BookingTraveler name={self.name} primary={self.is_primary}>"


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING ADDONS
# ─────────────────────────────────────────────────────────────────────────────

class BookingAddon(Base):
    __tablename__ = "booking_addons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True), ForeignKey("bookings.id"),
        nullable=False, index=True,
    )

    addon_type  = Column(String(50),     nullable=False)
    addon_name  = Column(String(200),    nullable=False)
    quantity    = Column(Integer,        default=1)
    unit_price  = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    booking = relationship("Booking", back_populates="addons")

    def __repr__(self) -> str:
        return f"<BookingAddon {self.addon_name} qty={self.quantity}>"