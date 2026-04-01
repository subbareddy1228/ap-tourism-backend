"""
schemas/admin.py
Admin module schemas — fixed for LEV146 (Pydantic v2).
"""

from pydantic import BaseModel, field_validator
from typing import Optional
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