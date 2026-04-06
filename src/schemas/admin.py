"""
schemas/admin.py
Admin module schemas — fixed for LEV146 (Pydantic v2).

Changes:
  - Added HotelReviewRequest  — body schema for PUT /admin/hotels/{id}/review
  - Added HotelAdminResponse  — typed response for admin hotel detail / review result
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── USER ──────────────────────────────────────────────
class UserStatusUpdate(BaseModel):
    status: str  # ACTIVE | SUSPENDED

    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"active", "suspended"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class UserRoleUpdate(BaseModel):
    role: str  # traveler | partner | admin

    @field_validator("role")
    def validate_role(cls, v):
        allowed = {"traveler", "partner", "admin"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


# ── PARTNER ───────────────────────────────────────────
class PartnerStatusUpdate(BaseModel):
    status: str  # ACTIVE | SUSPENDED

    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"active", "suspended"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class VerifySchema(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


class CommissionSchema(BaseModel):
    rate: float


# ── BOOKING ───────────────────────────────────────────
class BookingStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"pending", "confirmed", "cancelled", "refunded"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


# ── TEMPLE ────────────────────────────────────────────
class TempleCreateSchema(BaseModel):
    name: str
    deity: Optional[str] = None
    district: str
    description: Optional[str] = None
    is_featured: Optional[bool] = False


class TempleUpdateSchema(BaseModel):
    name: Optional[str] = None
    deity: Optional[str] = None
    district: Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


# ── DESTINATION ───────────────────────────────────────
class DestinationCreateSchema(BaseModel):
    name: str
    slug: str
    type: str
    district: str
    tagline: str
    description: str
    is_featured: Optional[bool] = False


class DestinationUpdateSchema(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    district: Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


# ── PACKAGE ───────────────────────────────────────────
class PackageCreateSchema(BaseModel):
    name: str
    duration_days: int
    type: str
    price: float
    is_featured: Optional[bool] = False


class PackageUpdateSchema(BaseModel):
    name: Optional[str] = None
    duration_days: Optional[int] = None
    type: Optional[str] = None
    price: Optional[float] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


# ── SUPPORT ───────────────────────────────────────────
class AssignAgentSchema(BaseModel):
    agent_id: UUID


# ── COUPON ────────────────────────────────────────────
class CouponCreateSchema(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    valid_from: datetime
    valid_until: datetime
    min_order_value: Optional[float] = 0
    max_uses: Optional[int] = None
    is_active: Optional[bool] = True


class CouponUpdateSchema(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None
    valid_until: Optional[datetime] = None


# ── SETTINGS ──────────────────────────────────────────
class SettingUpdateSchema(BaseModel):
    value: str


# ── GENERIC STATUS UPDATE ─────────────────────────────
class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None

    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"active", "inactive", "approved", "rejected"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


# ── WALLET WITHDRAWAL ─────────────────────────────────
class WithdrawalProcessRequest(BaseModel):
    status: str

    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"completed", "rejected"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


# ══════════════════════════════════════════════════════
# HOTEL ADMIN REVIEW  (new — hotel approval workflow)
# ══════════════════════════════════════════════════════

class HotelReviewRequest(BaseModel):
    """
    Request body for PUT /admin/hotels/{hotel_id}/review.

    Fields:
      approved         — True → ACTIVE, False → REJECTED
      rejection_reason — required when approved=False; surfaced to the partner
      admin_note       — optional internal note for the admin team (not shown to partner)
    """
    approved: bool
    rejection_reason: Optional[str] = None
    admin_note: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def reason_required_on_rejection(cls, v, info):
        # info.data contains already-validated fields
        if info.data.get("approved") is False and not v:
            raise ValueError("rejection_reason is required when approved=False")
        return v


class HotelRoomAdminResponse(BaseModel):
    id: str
    room_type: str
    name: Optional[str]
    max_occupancy: int
    total_rooms: int
    price_per_night: float
    is_active: bool


class HotelAdminResponse(BaseModel):
    """
    Full hotel detail as seen by an admin — includes review-tracking fields
    that are hidden from public / partner responses.
    """
    id: str
    partner_id: str
    name: str
    description: Optional[str]
    star_rating: int
    hotel_type: str
    address: str
    city: str
    state: str
    pincode: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    website: Optional[str]
    check_in_time: str
    check_out_time: str
    cancellation_policy: Optional[str]
    pet_policy: str
    meal_options: Optional[List[str]]
    is_active: bool
    is_featured: bool
    status: str                         # PENDING | ACTIVE | INACTIVE | REJECTED
    base_price: Optional[float]
    rating: Optional[float]
    total_reviews: int

    # Admin-only review fields
    rejection_reason: Optional[str]
    admin_note: Optional[str]
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]          # admin user UUID as string

    rooms: List[HotelRoomAdminResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True