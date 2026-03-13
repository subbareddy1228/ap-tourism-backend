from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from src.api.deps.database import Base


class GuideStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class Specialization(str, enum.Enum):
    TEMPLE = "TEMPLE"
    ADVENTURE = "ADVENTURE"
    HERITAGE = "HERITAGE"
    ECO_TOURISM = "ECO_TOURISM"


class LanguageProficiency(str, enum.Enum):
    BASIC = "BASIC"
    CONVERSATIONAL = "CONVERSATIONAL"
    FLUENT = "FLUENT"
    NATIVE = "NATIVE"


class Guide(Base):
    __tablename__ = "guides"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, nullable=False)  # temp until partner linking ready
    user_id = Column(Integer, nullable=False)      # LEV146 will add ForeignKey later

    # Profile
    full_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    profile_photo = Column(String(500), nullable=True)
    experience_years = Column(Integer, default=0)

    # Location
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    # Stats
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_trips = Column(Integer, default=0)

    # Status
    status = Column(Enum(GuideStatus), default=GuideStatus.ACTIVE)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Availability
    unavailable_dates = Column(JSON, default=[])

    # Pricing
    price_per_day = Column(Float, nullable=True)
    price_per_half_day = Column(Float, nullable=True)

    # Certifications & Destinations
    certifications = Column(JSON, default=[])
    destinations = Column(JSON, default=[])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    languages = relationship("GuideLanguage", back_populates="guide")
    specializations = relationship("GuideSpecialization", back_populates="guide")
    documents = relationship("GuideDocument", back_populates="guide")


class GuideLanguage(Base):
    __tablename__ = "guide_languages"

    id = Column(Integer, primary_key=True, index=True)
    guide_id = Column(Integer, ForeignKey("guides.id"), nullable=False)
    language = Column(String(50), nullable=False)
    proficiency = Column(Enum(LanguageProficiency), default=LanguageProficiency.CONVERSATIONAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="languages")


class GuideSpecialization(Base):
    __tablename__ = "guide_specializations"

    id = Column(Integer, primary_key=True, index=True)
    guide_id = Column(Integer, ForeignKey("guides.id"), nullable=False)
    specialization = Column(Enum(Specialization), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="specializations")


class GuideDocument(Base):
    __tablename__ = "guide_documents"

    id = Column(Integer, primary_key=True, index=True)
    guide_id = Column(Integer, ForeignKey("guides.id"), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_url = Column(String(500), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guide = relationship("Guide", back_populates="documents")
