from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── User Schemas ──────────────────────────────────────
class UserUpdateSchema(BaseModel):
    name: Optional[str]
    email: Optional[str]
    language: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    status: str   # ACTIVE | SUSPENDED


class UserRoleUpdate(BaseModel):
    role: str     # USER | ADMIN | SUPPORT


class KYCVerifySchema(BaseModel):
    approved: bool
    rejection_reason: Optional[str]


# ── Partner Schemas ───────────────────────────────────
class PartnerStatusUpdate(BaseModel):
    status: str   # ACTIVE | SUSPENDED


class VerifySchema(BaseModel):
    approved: bool
    rejection_reason: Optional[str]


class CommissionSchema(BaseModel):
    rate: float


# ── Booking Schemas ───────────────────────────────────
class BookingStatusUpdate(BaseModel):
    status: str


class AssignGuideSchema(BaseModel):
    guide_id: int


class AssignDriverSchema(BaseModel):
    driver_id: int


# ── Content Schemas ───────────────────────────────────
class TempleCreateSchema(BaseModel):
    name: str
    deity: str
    district: str
    description: Optional[str]
    is_featured: Optional[bool] = False


class TempleUpdateSchema(BaseModel):
    name: Optional[str]
    deity: Optional[str]
    district: Optional[str]
    description: Optional[str]
    is_featured: Optional[bool]
    is_active: Optional[bool]


class DestinationCreateSchema(BaseModel):
    name: str
    type: str
    district: str
    description: Optional[str]
    is_featured: Optional[bool] = False


class DestinationUpdateSchema(BaseModel):
    name: Optional[str]
    type: Optional[str]
    district: Optional[str]
    description: Optional[str]
    is_featured: Optional[bool]
    is_active: Optional[bool]


class PackageCreateSchema(BaseModel):
    name: str
    duration_days: int
    type: str
    budget_category: str
    price: float
    itinerary: Optional[dict]
    is_featured: Optional[bool] = False


class PackageUpdateSchema(BaseModel):
    name: Optional[str]
    duration_days: Optional[int]
    type: Optional[str]
    budget_category: Optional[str]
    price: Optional[float]
    itinerary: Optional[dict]
    is_featured: Optional[bool]
    is_active: Optional[bool]


# ── Support Schemas ───────────────────────────────────
class AssignAgentSchema(BaseModel):
    agent_id: int


# ── FAQ Schemas ───────────────────────────────────────
class FAQCreateSchema(BaseModel):
    question: str
    answer: str
    category: str


class FAQUpdateSchema(BaseModel):
    question: Optional[str]
    answer: Optional[str]
    category: Optional[str]
    is_active: Optional[bool]


# ── Coupon Schemas ────────────────────────────────────
class CouponCreateSchema(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    min_order: Optional[float] = 0
    max_uses: Optional[int]
    expires_at: Optional[datetime]


class CouponUpdateSchema(BaseModel):
    discount_type: Optional[str]
    discount_value: Optional[float]
    min_order: Optional[float]
    max_uses: Optional[int]
    is_active: Optional[bool]
    expires_at: Optional[datetime]


# ── Banner Schemas ────────────────────────────────────
class BannerCreateSchema(BaseModel):
    title: str
    image_url: str
    link: Optional[str]
    is_active: Optional[bool] = True


class BannerUpdateSchema(BaseModel):
    title: Optional[str]
    image_url: Optional[str]
    link: Optional[str]
    is_active: Optional[bool]


# ── Settings Schema ───────────────────────────────────
class SettingUpdateSchema(BaseModel):
    value: str
