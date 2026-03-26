"""
schemas/admin.py
Admin module schemas — fixed for LEV146 (Pydantic v2).
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── User ──────────────────────────────────────────────
class UserStatusUpdate(BaseModel):
    status: str   # ACTIVE | SUSPENDED


class UserRoleUpdate(BaseModel):
    role: str     # traveler | partner | admin


# ── Partner ───────────────────────────────────────────
class PartnerStatusUpdate(BaseModel):
    status: str   # ACTIVE | SUSPENDED


class VerifySchema(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


class CommissionSchema(BaseModel):
    rate: float


# ── Booking ───────────────────────────────────────────
class BookingStatusUpdate(BaseModel):
    status: str


# ── Temple ────────────────────────────────────────────
class TempleCreateSchema(BaseModel):
    name:        str
    deity:       Optional[str] = None
    district:    str
    description: Optional[str] = None
    is_featured: Optional[bool] = False


class TempleUpdateSchema(BaseModel):
    name:        Optional[str] = None
    deity:       Optional[str] = None
    district:    Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active:   Optional[bool] = None


# ── Destination ───────────────────────────────────────
class DestinationCreateSchema(BaseModel):
    name:        str
    slug:        str
    type:        str
    district:    str
    tagline:     str
    description: str
    is_featured: Optional[bool] = False


class DestinationUpdateSchema(BaseModel):
    name:        Optional[str] = None
    type:        Optional[str] = None
    district:    Optional[str] = None
    description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active:   Optional[bool] = None


# ── Package ───────────────────────────────────────────
class PackageCreateSchema(BaseModel):
    name:            str
    duration_days:   int
    type:            str
    price:           float
    is_featured:     Optional[bool] = False


class PackageUpdateSchema(BaseModel):
    name:            Optional[str]   = None
    duration_days:   Optional[int]   = None
    type:            Optional[str]   = None
    price:           Optional[float] = None
    is_featured:     Optional[bool]  = None
    is_active:       Optional[bool]  = None


# ── Support ───────────────────────────────────────────
class AssignAgentSchema(BaseModel):
    agent_id: UUID


# ── Coupon ────────────────────────────────────────────
class CouponCreateSchema(BaseModel):
    code:           str
    discount_type:  str
    discount_value: float
    valid_from:     datetime
    valid_until:    datetime
    min_order_value: Optional[float] = 0
    max_uses:        Optional[int]   = None
    is_active:       Optional[bool]  = True


class CouponUpdateSchema(BaseModel):
    discount_type:  Optional[str]   = None
    discount_value: Optional[float] = None
    min_order_value: Optional[float] = None
    max_uses:        Optional[int]  = None
    is_active:       Optional[bool] = None
    valid_until:     Optional[datetime] = None


# ── Settings ──────────────────────────────────────────
class SettingUpdateSchema(BaseModel):
    value: str