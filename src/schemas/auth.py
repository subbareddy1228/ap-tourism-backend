"""
schemas/auth.py
Pydantic schemas for all Authentication API request & response bodies.
"""

import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ── Validators ────────────────────────────────────────────────

def validate_phone(phone: str) -> str:
    """Ensure phone is a valid 10-digit Indian mobile number."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    if not re.match(r"^[6-9]\d{9}$", phone):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return phone


def validate_password(password: str) -> str:
    """Ensure password meets minimum strength requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


# ═══════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """POST /auth/register"""
    phone: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)

    @field_validator("password")
    def password_valid(cls, v): return validate_password(v)


class SendOTPRequest(BaseModel):
    """POST /auth/send-otp"""
    phone: str
    purpose: str = "register"   # register | login | forgot_password

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)


class VerifyOTPRequest(BaseModel):
    """POST /auth/verify-otp"""
    phone: str
    otp: str
    purpose: str = "register"

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)

    @field_validator("otp")
    def otp_valid(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number")
        return v


class ResendOTPRequest(BaseModel):
    """POST /auth/resend-otp"""
    phone: str
    purpose: str = "register"

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)


class LoginRequest(BaseModel):
    """POST /auth/login — phone OR email + password"""
    """POST /auth/login — password-based login"""
    phone: str
    password: str
    device_id: Optional[str] = "default"   # for multi-device session tracking

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)


class OTPLoginRequest(BaseModel):
    """POST /auth/login/otp — passwordless OTP login"""
    phone: str
    otp: str
    device_id: Optional[str] = "default"

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)


class RefreshTokenRequest(BaseModel):
    """POST /auth/refresh-token"""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password"""
    phone: str

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password"""
    phone: str
    otp: str
    new_password: str

    @field_validator("phone")
    def phone_valid(cls, v): return validate_phone(v)

    @field_validator("new_password")
    def password_valid(cls, v): return validate_password(v)


class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password — requires auth"""
    current_password: str
    new_password: str

    @field_validator("new_password")
    def password_valid(cls, v): return validate_password(v)


# ═══════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class UserResponse(BaseModel):
    """Minimal user info returned in auth responses."""
    id: str
    phone: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_phone_verified: bool
    is_email_verified: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Returned after successful login / verify-otp."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class OTPSentResponse(BaseModel):
    """Returned after sending OTP."""
    message: str
    phone: str
    expires_in: int = 300   # seconds
