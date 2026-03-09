# ============================================================
# src/schemas/user.py
# Pydantic Schemas — Module 2: User APIs
# Author: Garige Sai Manvitha (LEV146)
# ============================================================

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, validator, Field


# ----------------------------------------------------------
# Base response wrapper used by every endpoint
# ----------------------------------------------------------

class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data:    Optional[dict] = None


# ----------------------------------------------------------
# User Schemas
# ----------------------------------------------------------

class UserUpdateSchema(BaseModel):
    """PUT /me — update profile fields (all optional)"""
    full_name:     Optional[str]      = Field(None, max_length=200)
    language:      Optional[str]      = None   # TELUGU / HINDI / ENGLISH / TAMIL / KANNADA
    date_of_birth: Optional[datetime] = None
    gender:        Optional[str]      = None   # MALE / FEMALE / OTHER

    @validator("gender")
    def validate_gender(cls, v):
        if v and v not in ("MALE", "FEMALE", "OTHER"):
            raise ValueError("gender must be MALE, FEMALE, or OTHER")
        return v

    @validator("language")
    def validate_language(cls, v):
        allowed = ("TELUGU", "HINDI", "ENGLISH", "TAMIL", "KANNADA")
        if v and v not in allowed:
            raise ValueError(f"language must be one of {allowed}")
        return v


class UserResponseSchema(BaseModel):
    """Response schema for user profile"""
    id:             uuid.UUID
    phone:          str
    email:          Optional[str]
    full_name:      Optional[str]
    gender:         Optional[str]
    date_of_birth:  Optional[datetime]
    language:       str
    avatar_url:     Optional[str]
    role:           str
    phone_verified: bool
    email_verified: bool
    kyc_status:     str
    wallet_balance: float
    preferences:    Optional[dict]
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime

    class Config:
        orm_mode = True


class UserSessionSchema(BaseModel):
    """Represents a logged-in session (stored in Redis)"""
    session_id:  str
    device_info: Optional[str]
    ip_address:  Optional[str]
    last_active: Optional[str]
    created_at:  Optional[str]


# ----------------------------------------------------------
# Address Schemas
# ----------------------------------------------------------

class AddressCreateSchema(BaseModel):
    """POST /me/addresses"""
    label:         str = Field(..., description="HOME / WORK / OTHER")
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city:          str = Field(..., max_length=100)
    state:         str = Field(..., max_length=100)
    pincode:       str = Field(..., min_length=6, max_length=10)

    @validator("label")
    def validate_label(cls, v):
        if v not in ("HOME", "WORK", "OTHER"):
            raise ValueError("label must be HOME, WORK, or OTHER")
        return v

    @validator("pincode")
    def validate_pincode(cls, v):
        if not v.isdigit():
            raise ValueError("pincode must contain only digits")
        return v


class AddressUpdateSchema(BaseModel):
    """PUT /me/addresses/{id} — all fields optional"""
    label:         Optional[str] = None
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city:          Optional[str] = Field(None, max_length=100)
    state:         Optional[str] = Field(None, max_length=100)
    pincode:       Optional[str] = Field(None, min_length=6, max_length=10)


class AddressResponseSchema(BaseModel):
    """Response schema for address"""
    id:            uuid.UUID
    user_id:       uuid.UUID
    label:         str
    address_line1: str
    address_line2: Optional[str]
    city:          str
    state:         str
    pincode:       str
    created_at:    datetime
    updated_at:    datetime

    class Config:
        orm_mode = True


# ----------------------------------------------------------
# Family Member Schemas
# ----------------------------------------------------------

class FamilyMemberCreateSchema(BaseModel):
    """POST /me/family-members"""
    name:            str  = Field(..., max_length=200)
    relation:        str  = Field(..., description="SPOUSE / CHILD / PARENT / SIBLING / OTHER")
    date_of_birth:   Optional[datetime] = None
    gender:          Optional[str]      = None
    id_proof_type:   Optional[str]      = None   # AADHAR / PAN / PASSPORT / VOTER_ID
    id_proof_number: Optional[str]      = Field(None, max_length=100)

    @validator("relation")
    def validate_relation(cls, v):
        allowed = ("SPOUSE", "CHILD", "PARENT", "SIBLING", "OTHER")
        if v not in allowed:
            raise ValueError(f"relation must be one of {allowed}")
        return v

    @validator("id_proof_type")
    def validate_id_proof(cls, v):
        if v and v not in ("AADHAR", "PAN", "PASSPORT", "VOTER_ID"):
            raise ValueError("Invalid id_proof_type")
        return v


class FamilyMemberUpdateSchema(BaseModel):
    """PUT /me/family-members/{id} — all fields optional"""
    name:            Optional[str]      = Field(None, max_length=200)
    relation:        Optional[str]      = None
    date_of_birth:   Optional[datetime] = None
    gender:          Optional[str]      = None
    id_proof_type:   Optional[str]      = None
    id_proof_number: Optional[str]      = Field(None, max_length=100)


class FamilyMemberResponseSchema(BaseModel):
    """Response schema for family member"""
    id:              uuid.UUID
    user_id:         uuid.UUID
    name:            str
    relation:        str
    date_of_birth:   Optional[datetime]
    gender:          Optional[str]
    id_proof_type:   Optional[str]
    id_proof_number: Optional[str]
    created_at:      datetime
    updated_at:      datetime

    class Config:
        orm_mode = True


# ----------------------------------------------------------
# Preferences Schema
# ----------------------------------------------------------

class PreferencesSchema(BaseModel):
    """GET/PUT /me/preferences"""
    dietary:               Optional[str]  = None   # VEG / NON_VEG / JAIN / VEGAN
    language:              Optional[str]  = None
    accessibility_needs:   Optional[str]  = None   # WHEELCHAIR / SENIOR_CITIZEN / NONE
    notification_sms:      Optional[bool] = True
    notification_email:    Optional[bool] = True
    notification_push:     Optional[bool] = True

    @validator("dietary")
    def validate_dietary(cls, v):
        if v and v not in ("VEG", "NON_VEG", "JAIN", "VEGAN"):
            raise ValueError("dietary must be VEG, NON_VEG, JAIN, or VEGAN")
        return v


# ----------------------------------------------------------
# Verification Schemas
# ----------------------------------------------------------

class EmailVerifyRequestSchema(BaseModel):
    """POST /me/verify-email"""
    email: EmailStr


class PhoneVerifyRequestSchema(BaseModel):
    """POST /me/verify-phone — step 1: send OTP"""
    phone: str = Field(..., min_length=10, max_length=15)


class PhoneVerifyOTPSchema(BaseModel):
    """POST /me/verify-phone/confirm — step 2: confirm OTP"""
    phone: str
    otp:   str = Field(..., min_length=4, max_length=6)


# ----------------------------------------------------------
# Avatar Schema
# ----------------------------------------------------------
# Avatar uses UploadFile directly in the router — no Pydantic schema needed
# Response schema:

class AvatarResponseSchema(BaseModel):
    avatar_url: str
    message:    str = "Avatar updated successfully"
