
"""
schemas/user.py
Pydantic schemas for all User API endpoints (M2 — 25 endpoints).
Follows same pattern as schemas/auth.py.
"""

import re
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ── Shared Validators ─────────────────────────────────────────

def validate_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    if not re.match(r"^[6-9]\d{9}$", phone):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return phone

def validate_pincode(v: str) -> str:
    if not re.match(r"^\d{6}$", v):
        raise ValueError("Pincode must be 6 digits")
    return v


# ═══════════════════════════════════════════════════════════════
# ADDRESS SCHEMAS
# ═══════════════════════════════════════════════════════════════

class AddressCreate(BaseModel):
    """POST /users/me/addresses"""
    label: str                          # home | work | other
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"
    is_default: bool = False

    @field_validator("label")
    def label_valid(cls, v):
        allowed = {"home", "work", "other"}
        if v.lower() not in allowed:
            raise ValueError(f"Label must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("pincode")
    def pincode_valid(cls, v): return validate_pincode(v)


class AddressUpdate(BaseModel):
    """PUT /users/me/addresses/{address_id}"""
    label: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None

    @field_validator("pincode")
    def pincode_valid(cls, v):
        if v: return validate_pincode(v)
        return v


class AddressResponse(BaseModel):
    id: UUID
    label: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    pincode: str
    country: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# FAMILY MEMBER SCHEMAS
# ═══════════════════════════════════════════════════════════════

class FamilyMemberCreate(BaseModel):
    """POST /users/me/family"""
    name: str
    relation: str                       # spouse|child|parent|sibling|other
    age: Optional[int] = None
    gender: Optional[str] = None
    is_senior: bool = False
    special_needs: Optional[str] = None

    @field_validator("relation")
    def relation_valid(cls, v):
        allowed = {"spouse", "child", "parent", "sibling", "other"}
        if v.lower() not in allowed:
            raise ValueError(f"Relation must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("age")
    def age_valid(cls, v):
        if v is not None and (v < 0 or v > 120):
            raise ValueError("Age must be between 0 and 120")
        return v


class FamilyMemberUpdate(BaseModel):
    """PUT /users/me/family/{member_id}"""
    name: Optional[str] = None
    relation: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    is_senior: Optional[bool] = None
    special_needs: Optional[str] = None


class FamilyMemberResponse(BaseModel):
    id: UUID
    name: str
    relation: str
    age: Optional[int]
    gender: Optional[str]
    is_senior: bool
    special_needs: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# PROFILE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class ProfileUpdate(BaseModel):
    """PUT /users/me/profile — partial update"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    language_pref: Optional[str] = None
    bio: Optional[str] = None
    dietary_preference: Optional[str] = None
    special_needs: Optional[str] = None
    travel_preferences: Optional[Dict[str, Any]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None

    @field_validator("gender")
    def gender_valid(cls, v):
        if v:
            allowed = {"male", "female", "other", "prefer_not_to_say"}
            if v.lower() not in allowed:
                raise ValueError(f"Gender must be one of: {', '.join(allowed)}")
            return v.lower()
        return v

    @field_validator("language_pref")
    def lang_valid(cls, v):
        if v:
            allowed = {"en", "te", "hi"}
            if v.lower() not in allowed:
                raise ValueError(f"Language must be one of: {', '.join(allowed)}")
            return v.lower()
        return v

    @field_validator("dietary_preference")
    def diet_valid(cls, v):
        if v:
            allowed = {"vegetarian", "non_veg", "vegan", "jain"}
            if v.lower() not in allowed:
                raise ValueError(f"Dietary preference must be one of: {', '.join(allowed)}")
            return v.lower()
        return v

    @field_validator("emergency_contact_phone")
    def emergency_phone_valid(cls, v):
        if v: return validate_phone(v)
        return v


class ProfileResponse(BaseModel):
    """Full profile returned in GET /users/me"""
    id: str
    phone: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    status: str
    is_phone_verified: bool
    is_email_verified: bool
    is_profile_complete: bool

    # Profile details
    avatar_url: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    language_pref: str = "en"
    bio: Optional[str] = None
    dietary_preference: Optional[str] = None
    special_needs: Optional[str] = None
    travel_preferences: Optional[Dict[str, Any]] = None

    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None

    # Stats
    loyalty_points: int = 0
    total_trips: int = 0
    total_spent: float = 0.0

    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)

    @field_validator("role", "status", mode="before")
    @classmethod
    def normalize_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)


# ═══════════════════════════════════════════════════════════════
# SAVED ITEMS SCHEMAS
# ═══════════════════════════════════════════════════════════════

class SaveItemRequest(BaseModel):
    """POST /users/me/saved"""
    item_id: UUID
    item_type: str      # temple | destination | package | hotel

    @field_validator("item_type")
    def type_valid(cls, v):
        allowed = {"temple", "destination", "package", "hotel"}
        if v.lower() not in allowed:
            raise ValueError(f"item_type must be one of: {', '.join(allowed)}")
        return v.lower()


class SavedItemResponse(BaseModel):
    id: UUID
    item_id: UUID
    item_type: str
    saved_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# AVATAR / PHONE CHANGE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class UpdatePhoneRequest(BaseModel):
    """POST /users/me/change-phone"""
    new_phone: str
    otp: str

    @field_validator("new_phone")
    def phone_valid(cls, v): return validate_phone(v)

    @field_validator("otp")
    def otp_valid(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number")
        return v


class UpdateEmailRequest(BaseModel):
    """POST /users/me/verify-email"""
    email: EmailStr
    otp: str

    @field_validator("otp")
    def otp_valid(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number")
        return v


class UpdateFCMTokenRequest(BaseModel):
    """PUT /users/me/fcm-token"""
    fcm_token: str


# ═══════════════════════════════════════════════════════════════
# ADMIN USER SCHEMAS
# ═══════════════════════════════════════════════════════════════

class AdminUserListResponse(BaseModel):
    """GET /users (admin)"""
    id: str
    phone: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    status: str
    is_phone_verified: bool
    total_trips: int
    loyalty_points: int
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)

    @field_validator("role", "status", mode="before")
    @classmethod
    def normalize_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)


class AdminUpdateUserRequest(BaseModel):
    """PUT /users/{user_id} (admin)"""
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("role")
    def role_valid(cls, v):
        if v:
            allowed = {"traveler", "guide", "driver", "partner", "admin"}
            if v.lower() not in allowed:
                raise ValueError(f"Role must be one of: {', '.join(allowed)}")
            return v.lower()
        return v

    @field_validator("status")
    def status_valid(cls, v):
        if v:
            allowed = {"active", "suspended", "deleted"}
            if v.lower() not in allowed:
                raise ValueError(f"Status must be one of: {', '.join(allowed)}")
            return v.lower()
        return v


# ═══════════════════════════════════════════════════════════════
# BOOKING HISTORY / LOYALTY RESPONSE
# ═══════════════════════════════════════════════════════════════

class LoyaltyResponse(BaseModel):
    loyalty_points: int
    total_trips: int
    total_spent: float
    tier: str           # bronze | silver | gold | platinum

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    data: List[Any]
    total: int
    page: int
    pages: int
    limit: int
