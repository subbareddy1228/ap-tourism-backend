"""
models/coupon.py  —  M16 Coupon / Referral Module
 
Changes vs original:
  Coupon — removed 6 duplicate columns left over from a merge conflict:
    Removed: applicable_to, max_uses, max_uses_per_user, current_uses,
             is_public, is_referral
    Kept:    applicable_on, usage_limit, usage_per_user, used_count,
             coupon_type
  These duplicates caused confusion in the service layer and redundant
  DB columns.  Canonical column names match schemas/coupon.py exactly.
 
  is_valid() — cleaned to use only the canonical columns.
 
Data migration SQL (run BEFORE alembic upgrade head):
    UPDATE coupons SET used_count    = current_uses WHERE current_uses > 0;
    UPDATE coupons SET usage_limit   = max_uses     WHERE max_uses IS NOT NULL;
    UPDATE coupons SET coupon_type   =
        CASE WHEN is_referral THEN 'referral'
             WHEN is_public   THEN 'public'
             ELSE 'private' END;
    UPDATE coupons SET applicable_on = applicable_to
        WHERE applicable_on = 'all' AND applicable_to IS NOT NULL;
"""
 
import uuid
from datetime import datetime
from enum import Enum as PyEnum
 
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, Numeric,event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
 
from src.core.database import Base
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Local enums (used by services / schemas that import from this module)
# ─────────────────────────────────────────────────────────────────────────────
 
class DiscountType(str, PyEnum):
    PERCENTAGE   = "percentage"
    FLAT         = "flat"
    FREE_SERVICE = "free_service"
 
 
class CouponStatus(str, PyEnum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    EXPIRED   = "expired"
    EXHAUSTED = "exhausted"
 
 
class CouponType(str, PyEnum):
    PUBLIC   = "public"
    PRIVATE  = "private"
    REFERRAL = "referral"
 
 
class ApplicableOn(str, PyEnum):
    ALL      = "all"
    HOTEL    = "hotel"
    VEHICLE  = "vehicle"
    DARSHAN  = "darshan"
    PACKAGE  = "package"
    GUIDE    = "guide"
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Coupon
# ─────────────────────────────────────────────────────────────────────────────
 
class Coupon(Base):
    __tablename__ = "coupons"
 
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code           = Column(String,      unique=True, nullable=False, index=True)
    title          = Column(String(200), nullable=True)
    description    = Column(Text,        nullable=True)
    discount_type  = Column(String(50),  nullable=False)
    discount_value = Column(Numeric,     nullable=False)
    min_order_value = Column(Numeric,    default=0.0)
    max_discount   = Column(Numeric,     nullable=True)
    max_uses       = Column(Integer, nullable=True)
    used_count     = Column(Integer, default=0)
 
    # Canonical columns (duplicates removed)
    applicable_on    = Column(String(20),  default="all")    # all|hotel|vehicle|darshan|package|guide
    valid_from       = Column(DateTime,    nullable=False)
    valid_until      = Column(DateTime,    nullable=False)
    usage_limit      = Column(Integer,     nullable=True)    # max total uses across all users
    usage_per_user   = Column(Integer,     default=1)        # max uses per individual user
    used_count       = Column(Integer,     default=0)        # total times used
    coupon_type      = Column(String(20),  default="public") # public|private|referral
 
    assigned_user_id    = Column(UUID(as_uuid=True), nullable=True)
    applicable_user_ids = Column(JSON,               nullable=True)
    referral_user_id    = Column(UUID(as_uuid=True), nullable=True)
    is_active           = Column(Boolean,  default=True)
    created_by          = Column(UUID(as_uuid=True), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    usages = relationship("CouponUsage", back_populates="coupon")
 
@event.listens_for(Coupon, "init")
def strip_datetimes(target, args, kwargs):
    for key, val in kwargs.items():
        if isinstance(val, datetime) and val.tzinfo is not None:
            kwargs[key] = val.replace(tzinfo=None)
 
    # ── Business logic ────────────────────────────────────────────────────────
 
    def is_valid(self) -> bool:
        """Return True if this coupon can currently be applied."""
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if not (self.valid_from <= now <= self.valid_until):
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True
 
    def calculate_discount(self, order_value: float) -> float:
        """Calculate discount amount for a given order value."""
        min_val  = float(self.min_order_value or 0)
        if order_value < min_val:
            return 0.0
        disc_val = float(self.discount_value or 0)
        max_disc = float(self.max_discount   or 0)
        dtype    = str(self.discount_type).lower()
        if "flat" in dtype:
            return min(disc_val, order_value)
        if "percent" in dtype:
            disc = order_value * (disc_val / 100)
            if max_disc:
                disc = min(disc, max_disc)
            return round(disc, 2)
        return 0.0
 
    def __repr__(self) -> str:
        return f"<Coupon {self.code} type={self.coupon_type} active={self.is_active}>"
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Coupon Usage
# ─────────────────────────────────────────────────────────────────────────────
 
class CouponUsage(Base):
    __tablename__ = "coupon_usages"
 
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id      = Column(UUID(as_uuid=True), ForeignKey("coupons.id"), nullable=False, index=True)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    booking_id     = Column(UUID(as_uuid=True), nullable=True)
    transaction_id = Column(UUID(as_uuid=True), nullable=True)
    discount_amount = Column(Float, nullable=False)
    order_value    = Column(Float,  nullable=False)
    used_at        = Column(DateTime, default=datetime.utcnow)
 
    coupon = relationship("Coupon", back_populates="usages")
 
    def __repr__(self) -> str:
        return f"<CouponUsage coupon={self.coupon_id} user={self.user_id}>"
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Referral
# ─────────────────────────────────────────────────────────────────────────────
 
class Referral(Base):
    __tablename__ = "referrals"
 
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    referred_user_id = Column(UUID(as_uuid=True), nullable=True)
    coupon_id        = Column(UUID(as_uuid=True), ForeignKey("coupons.id"), nullable=True)
    referral_code    = Column(String(20), unique=True, nullable=False, index=True)
    referrer_reward  = Column(Float, default=100.0)
    referred_reward  = Column(Float, default=200.0)
    is_redeemed      = Column(Boolean, default=False)
    redeemed_at      = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    def __repr__(self) -> str:
        return f"<Referral code={self.referral_code} redeemed={self.is_redeemed}>"