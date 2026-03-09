"""
models/user.py
SQLAlchemy User model — the core user table for all roles.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Enum as SAEnum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.base import Base
from src.common.responses import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # ── Identity ──────────────────────────────────────────────
    phone        = Column(String(15), unique=True, nullable=False, index=True)
    email        = Column(String(255), unique=True, nullable=True, index=True)
    full_name    = Column(String(100), nullable=True)
    password_hash = Column(Text, nullable=True)   # nullable for OTP-only users

    # ── Role & Status ─────────────────────────────────────────
    role   = Column(SAEnum(UserRole),   default=UserRole.TRAVELER,  nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.ACTIVE,  nullable=False)

    # ── Verification Flags ────────────────────────────────────
    is_phone_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login  = Column(DateTime, nullable=True)
    deleted_at  = Column(DateTime, nullable=True)   # soft delete

    # ── Relationships ─────────────────────────────────────────
    profile     = relationship("UserProfile",    back_populates="user", uselist=False)
    addresses   = relationship("Address",        back_populates="user")
    family      = relationship("FamilyMember",   back_populates="user")
    bookings    = relationship("Booking",        back_populates="user")
    reviews     = relationship("Review",         back_populates="user")
    wallet      = relationship("Wallet",         back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<User {self.phone} ({self.role})>"
