"""

schemas/partner.py

Pydantic schemas for all Partners module endpoints.

"""
 
from typing import Optional, List

from datetime import datetime, date

from decimal import Decimal

from pydantic import BaseModel, EmailStr, field_validator
 
 
VALID_BUSINESS_TYPES = ["HOTEL", "VEHICLE", "GUIDE"]

VALID_DOC_TYPES = ["GSTIN", "PAN", "BANK_PROOF", "PROPERTY_DOC", "OTHER"]
 
 
# ══════════════════ REGISTER / PROFILE ══════════════════
 
class PartnerRegisterRequest(BaseModel):

    business_name:  str

    business_type:  str     # HOTEL | VEHICLE | GUIDE

    gstin:          Optional[str] = None

    pan:            Optional[str] = None

    description:    Optional[str] = None

    contact_phone:  Optional[str] = None

    contact_email:  Optional[EmailStr] = None

    website:        Optional[str] = None

    address:        Optional[str] = None

    city:           Optional[str] = None

    state:          Optional[str] = None

    pincode:        Optional[str] = None

    latitude:       Optional[float] = None

    longitude:      Optional[float] = None
 
    @field_validator("business_type")

    @classmethod

    def type_valid(cls, v):

        if v.upper() not in VALID_BUSINESS_TYPES:

            raise ValueError(f"business_type must be one of: {', '.join(VALID_BUSINESS_TYPES)}")

        return v.upper()
 
    @field_validator("gstin")

    @classmethod

    def gstin_valid(cls, v):

        if v and len(v) != 15:

            raise ValueError("GSTIN must be 15 characters")

        return v
 
    @field_validator("pan")

    @classmethod

    def pan_valid(cls, v):

        if v and len(v) != 10:

            raise ValueError("PAN must be 10 characters")

        return v.upper() if v else v
 
 
class PartnerUpdateRequest(BaseModel):

    business_name:  Optional[str] = None

    description:    Optional[str] = None

    contact_phone:  Optional[str] = None

    contact_email:  Optional[EmailStr] = None

    website:        Optional[str] = None

    address:        Optional[str] = None

    city:           Optional[str] = None

    state:          Optional[str] = None

    pincode:        Optional[str] = None

    latitude:       Optional[float] = None

    longitude:      Optional[float] = None
 
 
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

    total_reviews:       Optional[str]

    auto_accept:         bool

    created_at:          datetime
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ DASHBOARD ══════════════════
 
class DashboardResponse(BaseModel):

    today_bookings:     int

    this_month_earnings: float

    pending_payout:     float

    active_listings:    int

    total_bookings:     int

    this_month_bookings: int

    average_rating:     float
 
 
# ══════════════════ BOOKINGS ══════════════════
 
class PartnerBookingResponse(BaseModel):

    id:                 str

    booking_type:       str

    status:             str

    traveler_name:      str

    traveler_phone:     str

    check_in:           Optional[str]

    check_out:          Optional[str]

    guests:             Optional[int]

    amount:             float

    special_requirements: Optional[str]

    created_at:         datetime
 
 
class BookingActionRequest(BaseModel):

    reason: Optional[str] = None  # required for reject
 
 
# ══════════════════ EARNINGS ══════════════════
 
class EarningsSummaryResponse(BaseModel):

    total_earned:       float

    this_month:         float

    pending_payout:     float

    commission_rate:    float

    last_payout_date:   Optional[datetime]

    last_payout_amount: Optional[float]
 
 
# ══════════════════ PAYOUTS ══════════════════
 
class PayoutResponse(BaseModel):

    id:             str

    amount:         float

    status:         str

    bank_account:   Optional[str]

    ifsc_code:      Optional[str]

    transfer_ref:   Optional[str]

    transfer_date:  Optional[datetime]

    notes:          Optional[str]

    created_at:     datetime
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ BANK DETAILS ══════════════════
 
class BankDetailsRequest(BaseModel):

    account_number:       str

    ifsc_code:            str

    account_holder_name:  str

    bank_name:            Optional[str] = None

    branch_name:          Optional[str] = None
 
    @field_validator("ifsc_code")

    @classmethod

    def ifsc_valid(cls, v):

        if len(v) != 11:

            raise ValueError("IFSC code must be 11 characters")

        return v.upper()
 
 
class BankDetailsResponse(BaseModel):

    id:                   str

    account_number:       str

    ifsc_code:            str

    account_holder_name:  str

    bank_name:            Optional[str]

    branch_name:          Optional[str]

    is_verified:          bool

    updated_at:           Optional[datetime]
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ DOCUMENTS ══════════════════
 
class DocumentResponse(BaseModel):

    id:          str

    doc_type:    str

    file_url:    str

    file_name:   Optional[str]

    is_verified: bool

    verified_at: Optional[datetime]

    created_at:  datetime
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ AVAILABILITY ══════════════════
 
class AvailabilityRequest(BaseModel):

    unavailable_dates: List[str]

    # ["2024-12-25", "2024-12-26"]
 
 
# ══════════════════ SETTINGS ══════════════════
 
class SettingsRequest(BaseModel):

    auto_accept:         Optional[bool] = None

    notification_prefs:  Optional[dict] = None

    # { "booking_requests": true, "payment_received": true }
 
 
# ══════════════════ REVIEWS ══════════════════
 
class ReviewReplyRequest(BaseModel):

    reply: str
 
 
class ReviewResponse(BaseModel):

    id:           str

    traveler_name: str

    rating:       int

    comment:      Optional[str]

    reply:        Optional[str]

    created_at:   datetime
 
 