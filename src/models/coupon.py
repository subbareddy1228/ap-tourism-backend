import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base

class DiscountType(str, PyEnum):
    PERCENTAGE = "PERCENTAGE"
    FLAT       = "FLAT"

class CouponApplicableTo(str, PyEnum):
    ALL     = "ALL"
    HOTEL   = "HOTEL"
    PACKAGE = "PACKAGE"
    VEHICLE = "VEHICLE"
    TEMPLE  = "TEMPLE"
    GUIDE   = "GUIDE"

class Coupon(Base):
    __tablename__ = "coupons"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code              = Column(String(50),  nullable=False, unique=True, index=True)
    description       = Column(Text,        nullable=True)
    discount_type     = Column(Enum(DiscountType),       nullable=False)
    discount_value    = Column(Numeric(10, 2),            nullable=False)
    min_order_value   = Column(Numeric(10, 2),            nullable=False, default=0)
    max_discount      = Column(Numeric(10, 2),            nullable=True)
    applicable_to     = Column(Enum(CouponApplicableTo), nullable=False, default=CouponApplicableTo.ALL)
    valid_from        = Column(DateTime,    nullable=False, default=datetime.utcnow)
    valid_until       = Column(DateTime,    nullable=False)
    max_uses          = Column(Integer,     nullable=True)
    max_uses_per_user = Column(Integer,     nullable=False, default=1)
    current_uses      = Column(Integer,     nullable=False, default=0)
    is_public         = Column(Boolean,     nullable=False, default=True)
    is_referral       = Column(Boolean,     nullable=False, default=False)
    assigned_user_id  = Column(UUID(as_uuid=True), nullable=True)
    is_active         = Column(Boolean,     nullable=False, default=True)
    created_by        = Column(UUID(as_uuid=True), nullable=True)
    created_at        = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at        = Column(DateTime,    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    usages            = relationship("CouponUsage", back_populates="coupon", lazy="select")

    def is_valid_now(self):
        now = datetime.utcnow()
        return self.is_active and self.valid_from <= now <= self.valid_until and (self.max_uses is None or self.current_uses < self.max_uses)

class CouponUsage(Base):
    __tablename__ = "coupon_usages"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id         = Column(UUID(as_uuid=True), nullable=False, index=True)
    booking_id      = Column(UUID(as_uuid=True), nullable=True)
    discount_amount = Column(Numeric(10, 2),     nullable=False)
    used_at         = Column(DateTime,           nullable=False, default=datetime.utcnow)
    coupon          = relationship("Coupon",     back_populates="usages")