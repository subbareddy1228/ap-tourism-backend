"""
booking_model.py  —  M11 Booking Module
Author  : LEV151 Shree Hari Pappaka
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Enum, Date, Time, DateTime,
    Numeric, Integer, Boolean, Text, ForeignKey, Index
)

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base

from src.common.enums import (
    BookingType,
    BookingStatus,
    PaymentStatus,
    TripType,
    Gender
)


# ─────────────────────────────────────────────
# BOOKINGS (MASTER TABLE)
# ─────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    booking_type = Column(Enum(BookingType), nullable=False)

    status = Column(
        Enum(BookingStatus),
        default=BookingStatus.PENDING,
        nullable=False
    )

    payment_status = Column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING
    )

    total_amount = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # ───────── relationships ─────────

    darshan_booking = relationship("DarshanBooking", back_populates="booking", uselist=False)

    pooja_booking = relationship("PoojaBooking", back_populates="booking", uselist=False)

    hotel_booking = relationship("HotelBooking", back_populates="booking", uselist=False)

    vehicle_booking = relationship("VehicleBooking", back_populates="booking", uselist=False)

    package_booking = relationship("PackageBooking", back_populates="booking", uselist=False)

    guide_booking = relationship("GuideBooking", back_populates="booking", uselist=False)

    prasadam_orders = relationship(
        "PrasadamOrder",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    travelers = relationship(
        "BookingTraveler",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    addons = relationship(
        "BookingAddon",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_bookings_user_status", "user_id", "status"),
        Index("ix_bookings_user_type", "user_id", "booking_type"),
        Index("ix_bookings_payment_status", "payment_status"),
    )


# ─────────────────────────────────────────────
# HOTEL BOOKINGS
# ─────────────────────────────────────────────

class HotelBooking(Base):
    __tablename__ = "hotel_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        unique=True,
        index=True
    )

    hotel_id = Column(UUID(as_uuid=True), nullable=False)

    room_id = Column(UUID(as_uuid=True), nullable=False)

    check_in_date = Column(Date, nullable=False)

    check_out_date = Column(Date, nullable=False)

    rooms_count = Column(Integer, default=1)

    adults = Column(Integer, default=1)

    children = Column(Integer, default=0)

    room_rate_per_night = Column(Numeric(10, 2), nullable=False)

    total_room_charge = Column(Numeric(10, 2), nullable=False)

    guest_details = Column(JSONB)

    booking = relationship("Booking", back_populates="hotel_booking")


# ─────────────────────────────────────────────
# VEHICLE BOOKINGS
# ─────────────────────────────────────────────

class VehicleBooking(Base):
    __tablename__ = "vehicle_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        unique=True,
        index=True
    )

    vehicle_id = Column(UUID(as_uuid=True), nullable=False)

    driver_id = Column(UUID(as_uuid=True))

    trip_type = Column(Enum(TripType), nullable=False)

    pickup_location = Column(String(500), nullable=False)

    drop_location = Column(String(500), nullable=False)

    pickup_datetime = Column(DateTime, nullable=False)

    return_datetime = Column(DateTime)

    estimated_km = Column(Numeric(10, 2))

    rate_per_km = Column(Numeric(10, 2), nullable=False)

    total_charge = Column(Numeric(10, 2), nullable=False)

    route_details = Column(JSONB)

    booking = relationship("Booking", back_populates="vehicle_booking")


class PackageBooking(Base):
    __tablename__ = "package_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        unique=True,
        index=True
    )

    package_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    num_adults = Column(Integer, default=1)
    num_children = Column(Integer, default=0)

    package_price = Column(Numeric(10, 2), nullable=False)

    addon_charges = Column(Numeric(10, 2), default=0)

    total_price = Column(Numeric(10, 2), nullable=False)

    customizations = Column(JSONB)

    booking = relationship("Booking", back_populates="package_booking")


class GuideBooking(Base):
    __tablename__ = "guide_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        unique=True,
        index=True
    )

    guide_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    start_time = Column(Time)
    end_time = Column(Time)

    num_hours = Column(Integer)
    num_days = Column(Integer)

    rate = Column(Numeric(10, 2), nullable=False)

    total_charge = Column(Numeric(10, 2), nullable=False)

    meeting_point = Column(String(500))

    locations_to_cover = Column(JSONB)

    booking = relationship("Booking", back_populates="guide_booking")


# ─────────────────────────────────────────────
# BOOKING TRAVELERS
# ─────────────────────────────────────────────

class BookingTraveler(Base):
    __tablename__ = "booking_travelers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        index=True
    )

    name = Column(String(100), nullable=False)

    age = Column(Integer, nullable=False)

    gender = Column(Enum(Gender))

    id_proof_type = Column(String(50))

    id_proof_number = Column(String(100))

    is_primary = Column(Boolean, default=False)

    booking = relationship("Booking", back_populates="travelers")


# ─────────────────────────────────────────────
# BOOKING ADDONS
# ─────────────────────────────────────────────

class BookingAddon(Base):
    __tablename__ = "booking_addons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
        index=True
    )

    addon_type = Column(String(50), nullable=False)

    addon_name = Column(String(200), nullable=False)

    quantity = Column(Integer, default=1)

    unit_price = Column(Numeric(10, 2), nullable=False)

    total_price = Column(Numeric(10, 2), nullable=False)

    booking = relationship("Booking", back_populates="addons")