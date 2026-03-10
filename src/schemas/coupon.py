from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from src.models.coupon import CouponApplicableTo, DiscountType

class CouponPublicData(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    min_order_value: Decimal
    max_discount: Optional[Decimal] = None
    applicable_to: str
    valid_until: datetime
    model_config = {"from_attributes": True}

class CouponDetailData(CouponPublicData):
    id: UUID
    valid_from: datetime
    is_active: bool
    max_uses: Optional[int] = None
    current_uses: int
    max_uses_per_user: int
    is_referral: bool
    model_config = {"from_attributes": True}

class CouponListData(BaseModel):
    data: List[CouponPublicData]
    total: int
    page: int
    pages: int
    limit: int

class MyCouponsData(BaseModel):
    data: List[CouponDetailData]
    total: int

class ReferralData(BaseModel):
    referral_code: str
    reward_amount: Decimal
    total_referrals: int
    total_earned: Decimal

class CouponValidateRequest(BaseModel):
    code: str = Field(..., max_length=50)
    cart_amount: Decimal = Field(..., gt=0)
    applicable_to: Optional[str] = None

class CouponValidateData(BaseModel):
    is_valid: bool
    discount_amount: Decimal
    final_amount: Decimal
    error_reason: Optional[str] = None
    coupon: Optional[CouponPublicData] = None

class CouponApplyRequest(BaseModel):
    code: str = Field(..., max_length=50)
    cart_amount: Decimal = Field(..., gt=0)
    booking_id: Optional[UUID] = None

class CouponApplyData(BaseModel):
    applied_coupon_id: UUID
    discount_amount: Decimal
    final_amount: Decimal
