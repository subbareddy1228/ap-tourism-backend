
"""
models/user_profile.py
Extended profile for the User — separates identity (users) from profile data.
Linked 1-to-1 with User.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text,
    Integer, Float, ForeignKey, JSON,
    Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class DietaryPreference(str):
    VEGETARIAN = "vegetarian"
    NON_VEG    = "non_veg"
    VEGAN      = "vegan"
    JAIN       = "jain"


class Gender(str):
    MALE              = "male"
    FEMALE            = "female"
    OTHER             = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False, index=True)

    # ── Personal Details ──────────────────────────────────────
    avatar_url       = Column(String(500), nullable=True)
    gender           = Column(String(20), nullable=True)    # male|female|other|prefer_not_to_say
    date_of_birth    = Column(DateTime, nullable=True)
    language_pref    = Column(String(10), default="en")     # en | te | hi
    bio              = Column(Text, nullable=True)

    # ── Travel Preferences ────────────────────────────────────
    dietary_preference = Column(String(30), nullable=True)  # vegetarian|non_veg|vegan|jain
    special_needs      = Column(Text, nullable=True)        # wheelchair, senior support, etc.
    # Stored as JSON: {"destinations": ["Tirupati"], "trip_types": ["pilgrimage"], "budget": "mid"}
    travel_preferences = Column(JSON, default=dict)

    # ── Emergency Contact ─────────────────────────────────────
    emergency_contact_name  = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(15),  nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)

    # ── Loyalty & Stats ───────────────────────────────────────
    loyalty_points = Column(Integer, default=0)
    total_trips    = Column(Integer, default=0)
    total_spent    = Column(Float,   default=0.0)

    # ── Push Notification Token ───────────────────────────────
    fcm_token = Column(String(500), nullable=True)

    # ── Profile Completeness ──────────────────────────────────
    is_profile_complete = Column(Boolean, default=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────
    user      = relationship("User",          back_populates="profile")
    addresses = relationship("UserAddress",   back_populates="profile",
                             cascade="all, delete-orphan")
    family_members = relationship("FamilyMember", back_populates="profile",
                                  cascade="all, delete-orphan")
    saved_items    = relationship("SavedItem",    back_populates="profile",
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserProfile user_id={self.user_id}>"


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    label         = Column(String(50), nullable=False)   # home | work | other
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city          = Column(String(100), nullable=False)
    state         = Column(String(100), nullable=False)
    pincode       = Column(String(10),  nullable=False)
    country       = Column(String(100), default="India")
    is_default    = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="addresses")


class FamilyMember(Base):
    """Traveler's family members — used for group bookings."""
    __tablename__ = "family_members"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    name          = Column(String(100), nullable=False)
    relation      = Column(String(50),  nullable=False)   # spouse|child|parent|sibling|other
    age           = Column(Integer,     nullable=True)
    gender        = Column(String(20),  nullable=True)
    is_senior     = Column(Boolean, default=False)        # 60+ for special temple assistance
    special_needs = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="family_members")


class SavedItem(Base):
    """Wishlist — temples, destinations, packages saved by user."""
    __tablename__ = "saved_items"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    item_id   = Column(UUID(as_uuid=True), nullable=False)
    item_type = Column(String(30), nullable=False)   # temple | destination | package | hotel
    saved_at  = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="saved_items")
