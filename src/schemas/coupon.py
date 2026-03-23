from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from src.models.coupon import DiscountType, CouponStatus, CouponType, ApplicableOn
class CouponOut(BaseModel):
    id: UUID
    code: str
    title: Optional[str] = None
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    max_discount: Optional[float] = None
    min_order_value: float = 0.0
    valid_from: datetime
    valid_until: datetime
    coupon_type: Optional[str] = "public"
    applicable_on: Optional[str] = "all"
    usage_per_user: int = 1

    class Config:
        from_attributes = True


class ValidateCouponRequest(BaseModel):
    user_id: UUID
    code: str = Field(..., min_length=3, max_length=50)
    order_value: float = Field(..., gt=0)
    booking_type: Optional[str] = None

    @field_validator("code")
    @classmethod
    def upper(cls, v): return v.strip().upper()


class ValidateCouponResponse(BaseModel):
    success: bool = True
    is_valid: bool
    code: str
    discount_amount: float = 0.0
    final_amount: float = 0.0
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    message: str
    coupon: Optional[CouponOut] = None


class ApplyCouponRequest(BaseModel):
    user_id: UUID
    code: str = Field(..., min_length=3, max_length=50)
    booking_id: UUID
    order_value: float = Field(..., gt=0)

    @field_validator("code")
    @classmethod
    def upper(cls, v): return v.strip().upper()


class ApplyCouponResponse(BaseModel):
    success: bool
    code: str
    discount_amount: float
    final_amount: float
    message: str
    coupon: Optional[CouponOut] = None


class RemoveCouponRequest(BaseModel):
    user_id: UUID
    booking_id: UUID


class RemoveCouponResponse(BaseModel):
    success: bool
    message: str
    refunded_amount: float = 0.0


class MyCouponItem(BaseModel):
    coupon: CouponOut
    is_used: bool
    used_at: Optional[datetime] = None
    discount_applied: Optional[float] = None
    is_applicable: bool = True


class MyCouponsResponse(BaseModel):
    success: bool = True
    available: List[MyCouponItem]
    used: List[MyCouponItem]
    total_savings: float = 0.0


class ReferralResponse(BaseModel):
    success: bool = True
    referral_code: str
    referral_link: str
    referrer_reward: float
    referred_reward: float
    total_referrals: int = 0
    successful_referrals: int = 0
    total_earned: float = 0.0


class ActiveCouponsResponse(BaseModel):
    success: bool = True
    coupons: List[CouponOut]
    total: int
    page: int
    per_page: int


class CreateCouponRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    discount_type: str
    discount_value: float = Field(..., gt=0)
    max_discount: Optional[float] = None
    min_order_value: float = 0.0
    valid_from: datetime
    valid_until: datetime
    usage_limit: Optional[int] = None
    usage_per_user: int = 1
    coupon_type: str = "public"
    applicable_on: str = "all"

    @field_validator("code")
    @classmethod
    def upper(cls, v): return v.strip().upper()


class UpdateCouponRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount: Optional[float] = None
    min_order_value: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None
    applicable_on: Optional[str] = None


class AdminCouponOut(CouponOut):
    usage_limit: Optional[int] = None
    used_count: int = 0
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    success: bool = True
    message: str