"""
models/user_profile.py
Models for Users Module — UserProfile, Address, FamilyMember, UserSession.

Owner: Dev 2 (Users Module)
DO NOT EDIT: src/models/user.py — coordinate with Dev 1 (psubb)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Text, Date, ForeignKey, Integer, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.base import Base


# ══════════════════ USER PROFILE ══════════════════

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # ── Relationship ──────────────────────────────
    user       = relationship("User", back_populates="profile")

    # ── Personal Info ─────────────────────────────
    date_of_birth  = Column(Date, nullable=True)
    gender         = Column(String(20), nullable=True)   # male | female | other
    language       = Column(String(10), default="en", nullable=False)
    avatar_url     = Column(Text, nullable=True)         # S3 URL

    # ── KYC ───────────────────────────────────────
    kyc_status     = Column(String(20), default="pending", nullable=False)  # pending | verified | rejected

    # ── Preferences (JSONB) ───────────────────────
    preferences    = Column(JSON, default=dict, nullable=False)
    # Structure: { dietary, language, accessibility, notifications: { email, sms, push } }

    # ── Timestamps ────────────────────────────────
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile user_id={self.user_id}>"


# ══════════════════ ADDRESS ══════════════════

class Address(Base):
    __tablename__ = "addresses"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Relationship ──────────────────────────────
    user         = relationship("User", back_populates="addresses")

    # ── Address Fields ────────────────────────────
    label        = Column(String(50), nullable=False)    # home | work | other
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city         = Column(String(100), nullable=False)
    state        = Column(String(100), nullable=False)
    pincode      = Column(String(10), nullable=False)
    country      = Column(String(100), default="India", nullable=False)
    is_default   = Column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Address {self.label} user_id={self.user_id}>"


# ══════════════════ FAMILY MEMBER ══════════════════

class FamilyMember(Base):
    __tablename__ = "family_members"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Relationship ──────────────────────────────
    user           = relationship("User", back_populates="family")

    # ── Member Info ───────────────────────────────
    name           = Column(String(100), nullable=False)
    relation       = Column(String(50), nullable=False)   # spouse | child | parent | sibling | other
    date_of_birth  = Column(Date, nullable=True)
    gender         = Column(String(20), nullable=True)

    # ── ID Proof ──────────────────────────────────
    id_proof_type  = Column(String(50), nullable=True)    # aadhaar | passport | pan
    id_proof_number = Column(String(50), nullable=True)

    # ── Timestamps ────────────────────────────────
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FamilyMember {self.name} ({self.relation}) user_id={self.user_id}>"


# ══════════════════ USER SESSION ══════════════════

class UserSession(Base):
    __tablename__ = "user_sessions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Relationship ──────────────────────────────
    user         = relationship("User", back_populates="sessions")

    # ── Session Info ──────────────────────────────
    device_info  = Column(String(255), nullable=True)    # "iPhone 14 / iOS 17"
    ip_address   = Column(String(45), nullable=True)     # supports IPv6
    jti          = Column(String(100), nullable=False)   # JWT ID — for blacklisting
    is_active    = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────
    last_active  = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at   = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserSession user_id={self.user_id} ip={self.ip_address}>"
