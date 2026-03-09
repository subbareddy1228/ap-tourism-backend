#booking should be written by shreehari only

"""
booking_model.py  —  M11 Booking Module
Author  : LEV151 Shree Hari Pappaka
Module  : /api/v1/bookings
Tables  : bookings, hotel_bookings, vehicle_bookings, darshan_bookings,
          package_bookings, guide_bookings, pooja_bookings,
          prasadam_orders, booking_travelers, booking_addons

Cross-checked against:
  - Entity Relationship Diagram.drawio  (57 tables, all columns verified)
  - Booking Flow.drawio                 (slot lock, payment flow, status transitions)
  - Travel___Temple.xlsx                (M11 endpoints, Redis keys, coding standards)
  - AP_Tourism_Backend API Specs.drawio (25 endpoints confirmed)
"""

import uuid

from sqlalchemy import (
    Column, String, Enum, Date, Time, DateTime,
    Numeric, Integer, Boolean, Text, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.base import Base
from src.common.enums import (
    BookingType,
    BookingStatus,
    PaymentStatus,
    TripType,
    Gender,
    DeliveryStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# BOOKINGS  (master table)
# ERD columns verified ✅  |  All 24 columns present
# ─────────────────────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_number = Column(String(20), unique=True, nullable=False)   # e.g. APT-20260306-0001
    user_id        = Column(UUID(as_uuid=True), nullable=False)        # FK → users.id (M2)

    booking_type   = Column(Enum(BookingType),   nullable=False)
    status         = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)

    booking_date = Column(Date, nullable=False, server_default=func.current_date())
    start_date   = Column(Date, nullable=True)
    end_date     = Column(Date, nullable=True)

    subtotal        = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount      = Column(Numeric(10, 2), nullable=False, default=0)
    convenience_fee = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount    = Column(Numeric(10, 2), nullable=False, default=0)
    paid_amount     = Column(Numeric(10, 2), nullable=False, default=0)

    coupon_code         = Column(String(50),  nullable=True)
    special_requests    = Column(Text,        nullable=True)
    custom_trip_details = Column(JSONB,       nullable=True)   # {destinations, services_needed, group_size, budget}
    contact_details     = Column(JSONB,       nullable=True)   # {name, phone, email}
    cancellation_reason = Column(String(500), nullable=True)

    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), nullable=False,
                          server_default=func.now(), onupdate=func.now())

    # ── relationships ──
    hotel_booking   = relationship("HotelBooking",    back_populates="booking", uselist=False)
    vehicle_booking = relationship("VehicleBooking",  back_populates="booking", uselist=False)
    darshan_booking = relationship("DarshanBooking",  back_populates="booking", uselist=False)
    package_booking = relationship("PackageBooking",  back_populates="booking", uselist=False)
    guide_booking   = relationship("GuideBooking",    back_populates="booking", uselist=False)
    pooja_booking   = relationship("PoojaBooking",    back_populates="booking", uselist=False)
    prasadam_orders = relationship("PrasadamOrder",   back_populates="booking")
    travelers       = relationship("BookingTraveler", back_populates="booking")
    addons          = relationship("BookingAddon",    back_populates="booking")

    # ── indexes ──
    # Composite indexes cover user_id + status/type/dates — no separate index=True needed
    # to avoid duplicate index creation by SQLAlchemy
    __table_args__ = (
        Index("ix_bookings_user_status",   "user_id", "status"),
        Index("ix_bookings_user_type",     "user_id", "booking_type"),
        Index("ix_bookings_user_dates",    "user_id", "start_date", "end_date"),
        Index("ix_bookings_payment_status","payment_status"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# HOTEL_BOOKINGS
# ERD columns verified ✅  |  All 14 columns present
# status NOT in ERD for sub-tables — master bookings.status is the source of truth
# ─────────────────────────────────────────────────────────────────────────────

class HotelBooking(Base):
    __tablename__ = "hotel_bookings"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                        nullable=False, unique=True, index=True)
    hotel_id   = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → hotels.id (M5)
    room_id    = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → rooms.id  (M5)

    check_in_date  = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    check_in_time  = Column(Time, nullable=True)
    check_out_time = Column(Time, nullable=True)

    rooms_count         = Column(Integer,        nullable=False, default=1)
    adults              = Column(Integer,        nullable=False, default=1)
    children            = Column(Integer,        nullable=False, default=0)
    room_rate_per_night = Column(Numeric(10, 2), nullable=False)
    total_room_charge   = Column(Numeric(10, 2), nullable=False)

    guest_details = Column(JSONB, nullable=True)   # [{name, age, id_proof}]

    booking = relationship("Booking", back_populates="hotel_booking")


# ─────────────────────────────────────────────────────────────────────────────
# VEHICLE_BOOKINGS
# ERD columns verified ✅  |  All 20 columns present
# ─────────────────────────────────────────────────────────────────────────────

class VehicleBooking(Base):
    __tablename__ = "vehicle_bookings"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                        nullable=False, unique=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → vehicles.id (M6)
    driver_id  = Column(UUID(as_uuid=True), nullable=True,  index=True)   # FK → drivers.id  (M6)

    trip_type       = Column(Enum(TripType), nullable=False)
    pickup_location = Column(String(500),    nullable=False)
    pickup_lat      = Column(Numeric(10, 7), nullable=True)
    pickup_lng      = Column(Numeric(10, 7), nullable=True)
    drop_location   = Column(String(500),    nullable=False)
    drop_lat        = Column(Numeric(10, 7), nullable=True)
    drop_lng        = Column(Numeric(10, 7), nullable=True)
    pickup_datetime = Column(DateTime(timezone=True), nullable=False)
    return_datetime = Column(DateTime(timezone=True), nullable=True)

    estimated_km     = Column(Numeric(10, 2), nullable=True)
    actual_km        = Column(Numeric(10, 2), nullable=True)
    rate_per_km      = Column(Numeric(10, 2), nullable=False)
    driver_allowance = Column(Numeric(10, 2), nullable=False, default=0)
    toll_charges     = Column(Numeric(10, 2), nullable=False, default=0)
    total_charge     = Column(Numeric(10, 2), nullable=False)

    route_details = Column(JSONB, nullable=True)   # waypoints, stops

    booking = relationship("Booking", back_populates="vehicle_booking")


# ─────────────────────────────────────────────────────────────────────────────
# DARSHAN_BOOKINGS
# ERD columns verified ✅  |  All 12 columns present
# ─────────────────────────────────────────────────────────────────────────────

class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id      = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                             nullable=False, unique=True, index=True)
    temple_id       = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → temples.id       (M7)
    darshan_slot_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → darshan_slots.id (M7)
    darshan_type_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → darshan_types.id (M7)

    darshan_date     = Column(Date,           nullable=False)
    darshan_time     = Column(Time,           nullable=False)
    num_persons      = Column(Integer,        nullable=False)
    price_per_person = Column(Numeric(10, 2), nullable=False)
    total_price      = Column(Numeric(10, 2), nullable=False)

    devotee_details = Column(JSONB,      nullable=False)   # [{name, age, id_proof_type, id_proof_number}]
    ticket_number   = Column(String(50), nullable=True, unique=True)

    booking = relationship("Booking", back_populates="darshan_booking")


# ─────────────────────────────────────────────────────────────────────────────
# PACKAGE_BOOKINGS
# ERD columns verified ✅  |  All 11 columns present
# ─────────────────────────────────────────────────────────────────────────────

class PackageBooking(Base):
    __tablename__ = "package_bookings"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                        nullable=False, unique=True, index=True)
    package_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → tour_packages.id (M9)

    start_date   = Column(Date,    nullable=False)
    end_date     = Column(Date,    nullable=False)
    num_adults   = Column(Integer, nullable=False, default=1)
    num_children = Column(Integer, nullable=False, default=0)

    package_price  = Column(Numeric(10, 2), nullable=False)
    addon_charges  = Column(Numeric(10, 2), nullable=False, default=0)
    total_price    = Column(Numeric(10, 2), nullable=False)
    customizations = Column(JSONB, nullable=True)   # {meals, room_type, extra_stops}

    booking = relationship("Booking", back_populates="package_booking")


# ─────────────────────────────────────────────────────────────────────────────
# GUIDE_BOOKINGS
# ERD columns verified ✅  |  All 13 columns present
# ─────────────────────────────────────────────────────────────────────────────

class GuideBooking(Base):
    __tablename__ = "guide_bookings"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                        nullable=False, unique=True, index=True)
    guide_id   = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → guides.id (M10)

    start_date = Column(Date, nullable=False)
    end_date   = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time   = Column(Time, nullable=True)

    num_hours    = Column(Integer,        nullable=True)
    num_days     = Column(Integer,        nullable=True)
    rate         = Column(Numeric(10, 2), nullable=False)
    total_charge = Column(Numeric(10, 2), nullable=False)

    meeting_point      = Column(String(500), nullable=True)
    locations_to_cover = Column(JSONB,       nullable=True)   # [destination_id, ...]

    booking = relationship("Booking", back_populates="guide_booking")


# ─────────────────────────────────────────────────────────────────────────────
# POOJA_BOOKINGS
# ERD columns verified ✅  |  All 10 columns present
# ─────────────────────────────────────────────────────────────────────────────

class PoojaBooking(Base):
    __tablename__ = "pooja_bookings"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id       = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                              nullable=False, unique=True, index=True)
    pooja_service_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → pooja_services.id (M7)

    pooja_date = Column(Date, nullable=False)
    pooja_time = Column(Time, nullable=True)

    devotee_names        = Column(JSONB,         nullable=False)   # ["name1", "name2"]
    gothram              = Column(String(100),    nullable=True)
    nakshatra            = Column(String(100),    nullable=True)
    special_instructions = Column(Text,           nullable=True)
    price                = Column(Numeric(10, 2), nullable=False)

    booking = relationship("Booking", back_populates="pooja_booking")


# ─────────────────────────────────────────────────────────────────────────────
# PRASADAM_ORDERS
# ERD columns verified ✅  |  All 9 columns present
# ─────────────────────────────────────────────────────────────────────────────

class PrasadamOrder(Base):
    __tablename__ = "prasadam_orders"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id       = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                              nullable=False, index=True)
    prasadam_item_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # FK → prasadam_items.id (M7)

    quantity            = Column(Integer,        nullable=False, default=1)
    unit_price          = Column(Numeric(10, 2), nullable=False)
    total_price         = Column(Numeric(10, 2), nullable=False)
    delivery_address_id = Column(UUID(as_uuid=True), nullable=True)             # FK → user_addresses.id (M2)
    delivery_status     = Column(Enum(DeliveryStatus), nullable=False,
                                 default=DeliveryStatus.PENDING, index=True)
    tracking_number     = Column(String(100), nullable=True)

    booking = relationship("Booking", back_populates="prasadam_orders")


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING_TRAVELERS
# ERD columns verified ✅  |  All 9 columns present
# ─────────────────────────────────────────────────────────────────────────────

class BookingTraveler(Base):
    __tablename__ = "booking_travelers"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id       = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                              nullable=False, index=True)
    family_member_id = Column(UUID(as_uuid=True), nullable=True)   # FK → family_members.id (M2) — optional

    name            = Column(String(100),  nullable=False)
    age             = Column(Integer,      nullable=False)
    gender          = Column(Enum(Gender), nullable=True)
    id_proof_type   = Column(String(50),   nullable=True)    # AADHAAR | PAN | PASSPORT | VOTER_ID
    id_proof_number = Column(String(100),  nullable=True)
    is_primary      = Column(Boolean,      nullable=False, default=False)

    booking = relationship("Booking", back_populates="travelers")


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING_ADDONS
# ERD columns verified ✅
# ERD shows: id, booking_id, addon_type, addon_name, quantity, unit_price
# total_price added beyond ERD — stored for performance (avoids quantity × unit_price
# calculation on every read). This is intentional and consistent with all other sub-tables.
# ─────────────────────────────────────────────────────────────────────────────

class BookingAddon(Base):
    __tablename__ = "booking_addons"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"),
                        nullable=False, index=True)

    addon_type  = Column(String(50),     nullable=False)    # travel_insurance | meal | photography | porterage
    addon_name  = Column(String(200),    nullable=False)
    quantity    = Column(Integer,        nullable=False, default=1)
    unit_price  = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)    # stored: quantity × unit_price

    booking = relationship("Booking", back_populates="addons")
