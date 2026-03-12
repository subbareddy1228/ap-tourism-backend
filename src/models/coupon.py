import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base
# Enums for use in schemas/services
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


class Coupon(Base):
    __tablename__ = "coupons"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                = Column(String, unique=True, nullable=False, index=True)
    title               = Column(String(200), nullable=True)
    description         = Column(Text, nullable=True)
    discount_type       = Column(String(50), nullable=False)
    discount_value      = Column(Numeric, nullable=False)
    min_order_value     = Column(Numeric, default=0.0)
    max_discount        = Column(Numeric, nullable=True)
    applicable_to       = Column(String, nullable=True)   # original DB col
    applicable_on       = Column(String(20), default="all")  # added col
    valid_from          = Column(DateTime, nullable=False)
    valid_until         = Column(DateTime, nullable=False)
    max_uses            = Column(Integer, nullable=True)   # original DB col
    max_uses_per_user   = Column(Integer, default=1)       # original DB col
    usage_limit         = Column(Integer, nullable=True)   # added col
    usage_per_user      = Column(Integer, default=1)       # added col
    current_uses        = Column(Integer, default=0)       # original DB col
    used_count          = Column(Integer, default=0)       # added col
    is_public           = Column(Boolean, default=True)    # original DB col
    is_referral         = Column(Boolean, default=False)   # original DB col
    coupon_type         = Column(String(20), default="public")  # added col
    assigned_user_id    = Column(UUID(as_uuid=True), nullable=True)
    applicable_user_ids = Column(JSON, nullable=True)
    referral_user_id    = Column(UUID(as_uuid=True), nullable=True)
    is_active           = Column(Boolean, default=True)
    created_by          = Column(UUID(as_uuid=True), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usages = relationship("CouponUsage", back_populates="coupon")

    def is_valid(self) -> bool:
        now   = datetime.utcnow()
        if not self.is_active:
            return False
        if not (self.valid_from <= now <= self.valid_until):
            return False
        limit = self.usage_limit or self.max_uses
        uses  = self.used_count or self.current_uses or 0
        if limit and uses >= limit:
            return False
        return True

    def calculate_discount(self, order_value: float) -> float:
        min_val  = float(self.min_order_value or 0)
        if order_value < min_val:
            return 0.0
        disc_val = float(self.discount_value or 0)
        max_disc = float(self.max_discount or 0)
        dtype    = str(self.discount_type).lower()
        if "flat" in dtype:
            return min(disc_val, order_value)
        elif "percent" in dtype:
            disc = order_value * (disc_val / 100)
            if max_disc:
                disc = min(disc, max_disc)
            return round(disc, 2)
        return 0.0


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id        = Column(UUID(as_uuid=True), ForeignKey("coupons.id"), nullable=False, index=True)
    user_id          = Column(UUID(as_uuid=True), nullable=False, index=True)
    booking_id       = Column(UUID(as_uuid=True), nullable=True)
    transaction_id   = Column(UUID(as_uuid=True), nullable=True)
    discount_applied = Column(Float, nullable=False)
    order_value      = Column(Float, nullable=False)
    used_at          = Column(DateTime, default=datetime.utcnow)

    coupon = relationship("Coupon", back_populates="usages")


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