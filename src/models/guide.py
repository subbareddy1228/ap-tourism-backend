"""
models/guide.py
Guide module models — fixed for LEV146 integration.
Changes:
  - Uses Base from src.core.database
  - Uses UUID primary keys (consistent with all other models)
"""

import uuid
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from src.core.database import Base


class GuideStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    INACTIVE  = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class Specialization(str, enum.Enum):
    TEMPLE      = "TEMPLE"
    ADVENTURE   = "ADVENTURE"
    HERITAGE    = "HERITAGE"
    ECO_TOURISM = "ECO_TOURISM"


class LanguageProficiency(str, enum.Enum):
    BASIC          = "BASIC"
    CONVERSATIONAL = "CONVERSATIONAL"
    FLUENT         = "FLUENT"
    NATIVE         = "NATIVE"


class Guide(Base):
    __tablename__ = "guides"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    partner_id  = Column(UUID(as_uuid=True), nullable=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Profile
    full_name        = Column(String(255), nullable=False)
    bio              = Column(Text, nullable=True)
    profile_photo    = Column(String(500), nullable=True)
    experience_years = Column(Integer, default=0)

    # Location
    city  = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    # Stats
    rating        = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_trips   = Column(Integer, default=0)

    # Status
    status      = Column(Enum(GuideStatus), default=GuideStatus.ACTIVE)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Availability
    unavailable_dates = Column(JSON, default=list)

    # Pricing
    price_per_day      = Column(Float, nullable=True)
    price_per_half_day = Column(Float, nullable=True)

    # Certifications & Destinations
    certifications = Column(JSON, default=list)
    destinations   = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    languages       = relationship("GuideLanguage",       back_populates="guide", cascade="all, delete-orphan")
    specializations = relationship("GuideSpecialization", back_populates="guide", cascade="all, delete-orphan")
    documents       = relationship("GuideDocument",       back_populates="guide", cascade="all, delete-orphan")
    destination     = relationship("Destination", foreign_keys=[destination_id])


class GuideLanguage(Base):
    __tablename__ = "guide_languages"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    guide_id    = Column(UUID(as_uuid=True), ForeignKey("guides.id", ondelete="CASCADE"), nullable=False)
    language    = Column(String(50), nullable=False)
    proficiency = Column(Enum(LanguageProficiency), default=LanguageProficiency.CONVERSATIONAL)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="languages")


class GuideSpecialization(Base):
    __tablename__ = "guide_specializations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    guide_id       = Column(UUID(as_uuid=True), ForeignKey("guides.id", ondelete="CASCADE"), nullable=False)
    specialization = Column(Enum(Specialization), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="specializations")


class GuideDocument(Base):
    __tablename__ = "guide_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    guide_id      = Column(UUID(as_uuid=True), ForeignKey("guides.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_url      = Column(String(500), nullable=False)
    is_verified   = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="documents")