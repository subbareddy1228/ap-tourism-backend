from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Any
from datetime import datetime
from src.models.partner import PartnerType, PartnerStatus, DocumentType, PayoutStatus


# ─── Partner Schemas ──────────────────────────────────────────────────────────

class PartnerRegisterSchema(BaseModel):
    partner_type: PartnerType
    business_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None

    @validator("gstin")
    def validate_gstin(cls, v):
        if v and len(v) != 15:
            raise ValueError("GSTIN must be 15 characters")
        return v

    @validator("pan")
    def validate_pan(cls, v):
        if v and len(v) != 10:
            raise ValueError("PAN must be 10 characters")
        return v


class PartnerUpdateSchema(BaseModel):
    business_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None


class PartnerResponseSchema(BaseModel):
    id: int
    user_id: int
    partner_type: PartnerType
    business_name: str
    gstin: Optional[str]
    pan: Optional[str]
    verification_status: PartnerStatus
    is_active: bool
    commission_rate: float
    total_earnings: float
    wallet_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStatsSchema(BaseModel):
    todays_bookings: int
    this_month_earnings: float
    pending_payouts: float
    active_listings: int


# ─── Bookings ─────────────────────────────────────────────────────────────────

class BookingItemSchema(BaseModel):
    id: int
    booking_type: str
    status: str
    travel_date: Optional[datetime]
    amount: float
    traveler_name: Optional[str]
    special_requirements: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class BookingRejectSchema(BaseModel):
    reason: str


# ─── Earnings ─────────────────────────────────────────────────────────────────

class EarningsSummarySchema(BaseModel):
    total_earned: float
    this_month: float
    pending_payout: float
    commission_rate: float


# ─── Payouts ──────────────────────────────────────────────────────────────────

class PayoutResponseSchema(BaseModel):
    id: int
    amount: float
    status: PayoutStatus
    bank_account: Optional[str]
    transfer_date: Optional[datetime]
    reference_id: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# ─── Bank Details ─────────────────────────────────────────────────────────────

class BankDetailsSchema(BaseModel):
    account_number: str
    ifsc: str
    account_holder_name: str

    @validator("ifsc")
    def validate_ifsc(cls, v):
        if len(v) != 11:
            raise ValueError("IFSC must be 11 characters")
        return v.upper()


# ─── Documents ────────────────────────────────────────────────────────────────

class DocumentResponseSchema(BaseModel):
    id: int
    document_type: DocumentType
    file_url: str
    is_verified: bool
    verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True


# ─── Settings ─────────────────────────────────────────────────────────────────

class AvailabilityUpdateSchema(BaseModel):
    unavailable_dates: List[str]   # List of date strings "YYYY-MM-DD"


class PartnerSettingsSchema(BaseModel):
    auto_accept_bookings: Optional[bool] = None
    notification_preferences: Optional[dict] = None


# ─── Reviews ──────────────────────────────────────────────────────────────────

class ReviewReplySchema(BaseModel):
    reply: str


# ─── Standard Response ────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: str = ""


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: int