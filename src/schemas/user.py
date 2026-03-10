"""
schemas/user.py
Pydantic schemas for Users Module — all request/response bodies.
Owner: Dev 2
"""

import re
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID


# ══════════════════ PROFILE SCHEMAS ══════════════════

class UpdateProfileRequest(BaseModel):
    """PUT /me — update basic profile info"""
    full_name:     Optional[str]  = None
    date_of_birth: Optional[date] = None
    gender:        Optional[str]  = None   # male | female | other
    language:      Optional[str]  = None   # en | te | hi

    @field_validator("gender")
    @classmethod
    def gender_valid(cls, v):
        if v and v not in ["male", "female", "other"]:
            raise ValueError("gender must be male, female, or other")
        return v

    @field_validator("language")
    @classmethod
    def language_valid(cls, v):
        if v and v not in ["en", "te", "hi", "ta", "kn"]:
            raise ValueError("Unsupported language code")
        return v


class ProfileResponse(BaseModel):
    """Response for GET /me"""
    id:                str
    phone:             str
    email:             Optional[str]
    full_name:         Optional[str]
    role:              str
    is_phone_verified: bool
    is_email_verified: bool
    date_of_birth:     Optional[date]
    gender:            Optional[str]
    language:          Optional[str]
    avatar_url:        Optional[str]
    kyc_status:        Optional[str]
    preferences:       Optional[dict]

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v):
        if hasattr(v, "value"): return v.value
        return str(v).lower()


# ══════════════════ AVATAR SCHEMAS ══════════════════

class AvatarResponse(BaseModel):
    """Response for PATCH /me/avatar"""
    avatar_url: str
    message:    str = "Avatar uploaded successfully"


# ══════════════════ ADDRESS SCHEMAS ══════════════════

class AddressRequest(BaseModel):
    """POST /me/addresses and PUT /me/addresses/{id}"""
    label:         str
    address_line1: str
    address_line2: Optional[str] = None
    city:          str
    state:         str
    pincode:       str
    country:       Optional[str] = "India"
    is_default:    Optional[bool] = False

    @field_validator("pincode")
    @classmethod
    def pincode_valid(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Pincode must be 6 digits")
        return v

    @field_validator("label")
    @classmethod
    def label_valid(cls, v):
        if v.lower() not in ["home", "work", "other"]:
            raise ValueError("Label must be home, work, or other")
        return v.lower()


class AddressResponse(BaseModel):
    """Response for address endpoints"""
    id:            str
    user_id:       str
    label:         str
    address_line1: str
    address_line2: Optional[str]
    city:          str
    state:         str
    pincode:       str
    country:       str
    is_default:    bool
    created_at:    datetime
    updated_at:    Optional[datetime]

    class Config:
        from_attributes = True

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)


# ══════════════════ FAMILY MEMBER SCHEMAS ══════════════════

class FamilyMemberRequest(BaseModel):
    """POST /me/family-members and PUT /me/family-members/{id}"""
    name:            str
    relation:        str
    date_of_birth:   Optional[date] = None
    gender:          Optional[str]  = None
    id_proof_type:   Optional[str]  = None
    id_proof_number: Optional[str]  = None

    @field_validator("relation")
    @classmethod
    def relation_valid(cls, v):
        valid = ["spouse", "child", "parent", "sibling", "other"]
        if v.lower() not in valid:
            raise ValueError(f"relation must be one of: {', '.join(valid)}")
        return v.lower()

    @field_validator("id_proof_type")
    @classmethod
    def proof_type_valid(cls, v):
        if v and v.lower() not in ["aadhaar", "passport", "pan"]:
            raise ValueError("id_proof_type must be aadhaar, passport, or pan")
        return v.lower() if v else v


class FamilyMemberResponse(BaseModel):
    """Response for family member endpoints"""
    id:              str
    user_id:         str
    name:            str
    relation:        str
    date_of_birth:   Optional[date]
    gender:          Optional[str]
    id_proof_type:   Optional[str]
    id_proof_number: Optional[str]
    created_at:      datetime

    class Config:
        from_attributes = True

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)


# ══════════════════ VERIFICATION SCHEMAS ══════════════════

class VerifyPhoneRequest(BaseModel):
    """POST /me/verify-phone/confirm"""
    otp: str

    @field_validator("otp")
    @classmethod
    def otp_valid(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be 6 digits")
        return v


# ══════════════════ PREFERENCES SCHEMAS ══════════════════

class NotificationPreferences(BaseModel):
    email: Optional[bool] = True
    sms:   Optional[bool] = True
    push:  Optional[bool] = True


class PreferencesRequest(BaseModel):
    """PUT /me/preferences"""
    dietary:       Optional[str]                       = None
    language:      Optional[str]                       = None
    accessibility: Optional[str]                       = None
    notifications: Optional[NotificationPreferences]   = None


class PreferencesResponse(BaseModel):
    """Response for GET /me/preferences"""
    dietary:       Optional[str]
    language:      Optional[str]
    accessibility: Optional[str]
    notifications: Optional[dict]


# ══════════════════ SESSION SCHEMAS ══════════════════

class SessionResponse(BaseModel):
    """Response for GET /me/sessions"""
    id:          str
    device_info: Optional[str]
    ip_address:  Optional[str]
    last_active: datetime
    created_at:  datetime
    is_active:   bool

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v): return str(v)