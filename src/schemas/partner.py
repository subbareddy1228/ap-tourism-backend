"""
schemas/partner.py  —  Partner Module Pydantic Schemas
Pydantic v2 — all class Config replaced with model_config.

Fixes applied:
  DocumentResponse.id — was declared as `str` but the PartnerDocument model
    stores id as UUID(as_uuid=True). model_validate() received a UUID object
    and Pydantic v2 raised a ValidationError, causing a 500 on every
    POST /partners/me/documents and GET /partners/me/documents response.
    Fixed: @field_validator("id", mode="before") added to convert UUID → str,
    matching the same pattern already present in BankDetailsResponse.

  PayoutResponse.id — same UUID → str issue for GET /partners/me/payouts
    and GET /partners/me/payouts/{id}. Same fix applied.

  PartnerProfileResponse.total_reviews — was Optional[str], fixed to
    Optional[int] to match model Integer column.

  All class Config: from_attributes = True replaced with
    model_config = {"from_attributes": True}  (Pydantic v2 standard).
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


VALID_BUSINESS_TYPES = ["HOTEL", "VEHICLE", "GUIDE"]
VALID_DOC_TYPES      = ["GSTIN", "PAN", "BANK_PROOF", "PROPERTY_DOC", "OTHER"]


# ── Register / Profile ────────────────────────────────────────────────────────

class PartnerRegisterRequest(BaseModel):
    business_name: str
    business_type: str
    gstin:         Optional[str]      = None
    pan:           Optional[str]      = None
    description:   Optional[str]      = None
    contact_phone: Optional[str]      = None
    contact_email: Optional[EmailStr] = None
    website:       Optional[str]      = None
    address:       Optional[str]      = None
    city:          Optional[str]      = None
    state:         Optional[str]      = None
    pincode:       Optional[str]      = None
    latitude:      Optional[float]    = None
    longitude:     Optional[float]    = None

    @field_validator("business_type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v.upper() not in VALID_BUSINESS_TYPES:
            raise ValueError(f"business_type must be one of: {', '.join(VALID_BUSINESS_TYPES)}")
        return v.upper()

    @field_validator("gstin")
    @classmethod
    def gstin_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 15:
            raise ValueError("GSTIN must be 15 characters")
        return v

    @field_validator("pan")
    @classmethod
    def pan_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 10:
            raise ValueError("PAN must be 10 characters")
        return v.upper() if v else v


class PartnerUpdateRequest(BaseModel):
    business_name: Optional[str]      = None
    description:   Optional[str]      = None
    contact_phone: Optional[str]      = None
    contact_email: Optional[EmailStr] = None
    website:       Optional[str]      = None
    address:       Optional[str]      = None
    city:          Optional[str]      = None
    state:         Optional[str]      = None
    pincode:       Optional[str]      = None
    latitude:      Optional[float]    = None
    longitude:     Optional[float]    = None


class PartnerProfileResponse(BaseModel):
    id:                  str
    user_id:             str
    business_name:       str
    business_type:       str
    gstin:               Optional[str]
    pan:                 Optional[str]
    description:         Optional[str]
    logo_url:            Optional[str]
    contact_phone:       Optional[str]
    contact_email:       Optional[str]
    website:             Optional[str]
    address:             Optional[str]
    city:                Optional[str]
    state:               Optional[str]
    verification_status: str
    commission_rate:     float
    total_earnings:      float
    pending_payout:      float
    rating:              Optional[float]
    total_reviews:       Optional[int]   # Fixed: was Optional[str]
    auto_accept:         bool
    created_at:          datetime

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    today_bookings:      int
    this_month_earnings: float
    pending_payout:      float
    active_listings:     int
    total_bookings:      int
    this_month_bookings: int
    average_rating:      float


# ── Bookings ──────────────────────────────────────────────────────────────────

class PartnerBookingResponse(BaseModel):
    id:                   str
    booking_type:         str
    status:               str
    traveler_name:        str
    traveler_phone:       str
    check_in:             Optional[str]
    check_out:            Optional[str]
    guests:               Optional[int]
    amount:               float
    special_requirements: Optional[str]
    created_at:           datetime


class BookingActionRequest(BaseModel):
    reason: Optional[str] = None


# ── Earnings ──────────────────────────────────────────────────────────────────

class EarningsSummaryResponse(BaseModel):
    total_earned:       float
    this_month:         float
    pending_payout:     float
    commission_rate:    float
    last_payout_date:   Optional[datetime]
    last_payout_amount: Optional[float]


# ── Payouts ───────────────────────────────────────────────────────────────────

class PayoutResponse(BaseModel):
    id:            str
    amount:        float
    status:        str
    bank_account:  Optional[str]
    ifsc_code:     Optional[str]
    transfer_ref:  Optional[str]
    transfer_date: Optional[datetime]
    notes:         Optional[str]
    created_at:    datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v) -> str:
        """
        PartnerPayout.id is UUID(as_uuid=True). Pydantic v2 will not
        coerce UUID → str automatically when using model_validate(orm_obj).
        Convert here to prevent ValidationError on serialization.
        """
        return str(v)


# ── Bank Details ──────────────────────────────────────────────────────────────

class BankDetailsRequest(BaseModel):
    account_number:      str
    ifsc_code:           str
    account_holder_name: str
    bank_name:           Optional[str] = None
    branch_name:         Optional[str] = None

    @field_validator("ifsc_code")
    @classmethod
    def ifsc_valid(cls, v: str) -> str:
        if len(v) != 11:
            raise ValueError("IFSC code must be 11 characters")
        return v.upper()


class BankDetailsResponse(BaseModel):
    id:                  str
    account_number:      str
    ifsc_code:           str
    account_holder_name: str
    bank_name:           Optional[str]
    branch_name:         Optional[str]
    is_verified:         bool
    updated_at:          Optional[datetime]

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v) -> str:
        return str(v)


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id:          str
    doc_type:    str
    file_url:    str
    file_name:   Optional[str]
    is_verified: bool
    verified_at: Optional[datetime]
    created_at:  datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v) -> str:
        """
        PartnerDocument.id is UUID(as_uuid=True). Without this validator,
        model_validate(doc) raises ValidationError because Pydantic v2 will
        not implicitly coerce a UUID object to str.
        This is the same fix already present in BankDetailsResponse.
        """
        return str(v)


# ── Availability ──────────────────────────────────────────────────────────────

class AvailabilityRequest(BaseModel):
    unavailable_dates: List[str]


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsRequest(BaseModel):
    auto_accept:        Optional[bool] = None
    notification_prefs: Optional[dict] = None


# ── Reviews ───────────────────────────────────────────────────────────────────

class ReviewReplyRequest(BaseModel):
    reply: str


class ReviewResponse(BaseModel):
    id:            str
    traveler_name: str
    rating:        int
    comment:       Optional[str]
    reply:         Optional[str]
    created_at:    datetime