"""
<<<<<<< HEAD
schemas/partner.py
Pydantic schemas for all Partners module endpoints.
"""
 
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
=======

schemas/partner.py

Pydantic schemas for all Partners module endpoints.

"""
 
from typing import Optional, List

from datetime import datetime, date

from decimal import Decimal

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
from pydantic import BaseModel, EmailStr, field_validator
 
 
VALID_BUSINESS_TYPES = ["HOTEL", "VEHICLE", "GUIDE"]
<<<<<<< HEAD
=======

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
VALID_DOC_TYPES = ["GSTIN", "PAN", "BANK_PROOF", "PROPERTY_DOC", "OTHER"]
 
 
# ══════════════════ REGISTER / PROFILE ══════════════════
 
class PartnerRegisterRequest(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
        return v.upper() if v else v
 
 
class PartnerUpdateRequest(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    longitude:      Optional[float] = None
 
 
class PartnerProfileResponse(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    created_at:          datetime
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ DASHBOARD ══════════════════
 
class DashboardResponse(BaseModel):
<<<<<<< HEAD
    today_bookings:     int
    this_month_earnings: float
    pending_payout:     float
    active_listings:    int
    total_bookings:     int
    this_month_bookings: int
=======

    today_bookings:     int

    this_month_earnings: float

    pending_payout:     float

    active_listings:    int

    total_bookings:     int

    this_month_bookings: int

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    average_rating:     float
 
 
# ══════════════════ BOOKINGS ══════════════════
 
class PartnerBookingResponse(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    created_at:         datetime
 
 
class BookingActionRequest(BaseModel):
<<<<<<< HEAD
=======

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    reason: Optional[str] = None  # required for reject
 
 
# ══════════════════ EARNINGS ══════════════════
 
class EarningsSummaryResponse(BaseModel):
<<<<<<< HEAD
    total_earned:       float
    this_month:         float
    pending_payout:     float
    commission_rate:    float
    last_payout_date:   Optional[datetime]
=======

    total_earned:       float

    this_month:         float

    pending_payout:     float

    commission_rate:    float

    last_payout_date:   Optional[datetime]

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    last_payout_amount: Optional[float]
 
 
# ══════════════════ PAYOUTS ══════════════════
 
class PayoutResponse(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
        from_attributes = True
 
 
# ══════════════════ BANK DETAILS ══════════════════
 
class BankDetailsRequest(BaseModel):
<<<<<<< HEAD
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
=======

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

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
        return v.upper()
 
 
class BankDetailsResponse(BaseModel):
<<<<<<< HEAD
    id:                   str
    account_number:       str
    ifsc_code:            str
    account_holder_name:  str
    bank_name:            Optional[str]
    branch_name:          Optional[str]
    is_verified:          bool
    updated_at:           Optional[datetime]
 
    class Config:
=======

    id:                   str

    account_number:       str

    ifsc_code:            str

    account_holder_name:  str

    bank_name:            Optional[str]

    branch_name:          Optional[str]

    is_verified:          bool

    updated_at:           Optional[datetime]
 
    class Config:

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
        from_attributes = True
 
 
# ══════════════════ DOCUMENTS ══════════════════
 
class DocumentResponse(BaseModel):
<<<<<<< HEAD
    id:          str
    doc_type:    str
    file_url:    str
    file_name:   Optional[str]
    is_verified: bool
    verified_at: Optional[datetime]
=======

    id:          str

    doc_type:    str

    file_url:    str

    file_name:   Optional[str]

    is_verified: bool

    verified_at: Optional[datetime]

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    created_at:  datetime
 
    class Config:

        from_attributes = True
 
 
# ══════════════════ AVAILABILITY ══════════════════
 
class AvailabilityRequest(BaseModel):
<<<<<<< HEAD
    unavailable_dates: List[str]
=======

    unavailable_dates: List[str]

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    # ["2024-12-25", "2024-12-26"]
 
 
# ══════════════════ SETTINGS ══════════════════
 
class SettingsRequest(BaseModel):
<<<<<<< HEAD
    auto_accept:         Optional[bool] = None
    notification_prefs:  Optional[dict] = None
=======

    auto_accept:         Optional[bool] = None

    notification_prefs:  Optional[dict] = None

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    # { "booking_requests": true, "payment_received": true }
 
 
# ══════════════════ REVIEWS ══════════════════
 
class ReviewReplyRequest(BaseModel):
<<<<<<< HEAD
=======

>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
    reply: str
 
 
class ReviewResponse(BaseModel):
<<<<<<< HEAD
    id:           str
    traveler_name: str
    rating:       int
    comment:      Optional[str]
    reply:        Optional[str]
    created_at:   datetime
=======

    id:           str

    traveler_name: str

    rating:       int

    comment:      Optional[str]

    reply:        Optional[str]

    created_at:   datetime
 
 
>>>>>>> 3a7e8ab547e7b788e3eca1112338d3b7a457650e
