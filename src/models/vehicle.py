"""
models/vehicle.py
Vehicle module models — fixed for LEV146 integration.
Changes:
  - Removed ForeignKey to bookings.id (bookings module not yet built)
  - Uses Base from src.core.database (LEV146 pattern)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from src.core.database import Base


class VehicleType(str, enum.Enum):
    SEDAN           = "SEDAN"
    SUV             = "SUV"
    TEMPO_TRAVELLER = "TEMPO_TRAVELLER"
    BUS             = "BUS"
    AUTO            = "AUTO"
    BIKE            = "BIKE"


class VehicleStatus(str, enum.Enum):
    ACTIVE            = "ACTIVE"
    INACTIVE          = "INACTIVE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    SUSPENDED         = "SUSPENDED"


class DriverStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_TRIP  = "ON_TRIP"


class VehicleDocumentType(str, enum.Enum):
    RC                  = "RC"
    INSURANCE           = "INSURANCE"
    FITNESS_CERTIFICATE = "FITNESS_CERTIFICATE"
    PERMIT              = "PERMIT"
    PUC                 = "PUC"


# Base rate per km by vehicle type (in INR)
VEHICLE_BASE_RATES = {
    VehicleType.SEDAN:           12.0,
    VehicleType.SUV:             16.0,
    VehicleType.TEMPO_TRAVELLER: 22.0,
    VehicleType.BUS:             40.0,
    VehicleType.AUTO:             8.0,
    VehicleType.BIKE:             5.0,
}


class Vehicle(Base):
    __tablename__ = "vehicles"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id          = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Info
    vehicle_type        = Column(SAEnum(VehicleType), nullable=False)
    make                = Column(String(100), nullable=False)
    model               = Column(String(100), nullable=False)
    year                = Column(Integer, nullable=False)
    registration_number = Column(String(20), unique=True, nullable=False)
    color               = Column(String(50))

    # Capacity & Features
    capacity            = Column(Integer, nullable=False)
    has_ac              = Column(Boolean, default=True)
    has_wifi            = Column(Boolean, default=False)
    has_gps             = Column(Boolean, default=False)
    gps_device_id       = Column(String(100))
    features            = Column(JSONB, default=dict)

    # Pricing
    price_per_km        = Column(Float, nullable=False)
    min_fare            = Column(Float, default=200.0)

    # Location & Availability
    current_city        = Column(String(100))
    available_cities    = Column(JSONB, default=list)
    status              = Column(SAEnum(VehicleStatus), default=VehicleStatus.ACTIVE)

    # Media
    images              = Column(JSONB, default=list)

    # Stats
    rating              = Column(Float, default=0.0)
    total_reviews       = Column(Integer, default=0)
    total_trips         = Column(Integer, default=0)

    # Timestamps
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at          = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    documents = relationship("VehicleDocument", back_populates="vehicle", cascade="all, delete-orphan")
    drivers   = relationship("Driver",          back_populates="vehicle")
    reviews   = relationship("VehicleReview",   back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.registration_number} ({self.vehicle_type})>"


class VehicleDocument(Base):
    __tablename__ = "vehicle_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id    = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(SAEnum(VehicleDocumentType), nullable=False)
    file_url      = Column(String(500), nullable=False)
    expiry_date   = Column(DateTime(timezone=True), nullable=True)
    is_verified   = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="documents")


class Driver(Base):
    __tablename__ = "drivers"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    vehicle_id     = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    name           = Column(String(200), nullable=False)
    phone          = Column(String(15), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    license_expiry = Column(DateTime(timezone=True), nullable=False)
    photo_url      = Column(String(500))
    status         = Column(SAEnum(DriverStatus), default=DriverStatus.ACTIVE)
    rating         = Column(Float, default=0.0)
    total_trips    = Column(Integer, default=0)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="drivers")


class VehicleReview(Base):
    __tablename__ = "vehicle_reviews"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id  = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    booking_id  = Column(UUID(as_uuid=True), nullable=True)   # ← No FK — bookings module not yet built
    rating      = Column(Integer, nullable=False)
    comment     = Column(Text)
    is_verified = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="reviews")