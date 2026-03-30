"""
models/auth.py
Auth-related DB models:
  - OTPCode         — stores OTP records for audit/rate-limiting
  - RefreshToken    — persistent refresh token store
  - BlacklistedToken — revoked JWT JTIs
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class OTPCode(Base):
    """
    Stores OTP codes for audit trail.
    Primary store is Redis — this table is for audit/analytics only.
    """
    __tablename__ = "otp_codes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone      = Column(String(15),  nullable=False, index=True)
    purpose    = Column(String(50),  nullable=False)   # register | login | reset_password
    otp_hash   = Column(String(128), nullable=False)   # bcrypt hash of OTP
    is_used    = Column(Boolean,     default=False)
    attempts   = Column(String(5),   default="0")
    expires_at = Column(DateTime,    nullable=False)
    created_at = Column(DateTime,    default=datetime.utcnow)
    used_at    = Column(DateTime,    nullable=True)

    def __repr__(self):
        return f"<OTPCode phone={self.phone} purpose={self.purpose} used={self.is_used}>"


class RefreshToken(Base):
    """
    Persistent refresh token store.
    Allows multi-device login and forced logout.
    """
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    jti        = Column(String(128), unique=True, nullable=False, index=True)
    device_id  = Column(String(128), nullable=True)
    device_name = Column(String(200), nullable=True)
    ip_address = Column(String(45),  nullable=True)
    user_agent = Column(Text,        nullable=True)
    is_active  = Column(Boolean,     default=True)
    expires_at = Column(DateTime,    nullable=False)
    created_at = Column(DateTime,    default=datetime.utcnow)
    revoked_at = Column(DateTime,    nullable=True)

    def __repr__(self):
        return f"<RefreshToken user_id={self.user_id} active={self.is_active}>"


class BlacklistedToken(Base):
    """
    Revoked JWT JTIs — checked on every protected request.
    Redis is the primary fast store; this is the persistent fallback.
    """
    __tablename__ = "blacklisted_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti        = Column(String(128), unique=True, nullable=False, index=True)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    reason     = Column(String(100), nullable=True)   # logout | password_change | admin_revoke
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime,    nullable=False)

    def __repr__(self):
        return f"<BlacklistedToken jti={self.jti[:12]}...>"