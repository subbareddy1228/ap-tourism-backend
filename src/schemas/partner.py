from pydantic import BaseModel, validator
from typing import Optional, List, Any
from datetime import datetime
from src.models.partner import PartnerType, PartnerStatus, DocumentType, PayoutStatus


# ─── Register / Update ────────────────────────────────────────────────────────

class PartnerRegisterSchema(BaseModel):
    partner_type: PartnerType
    business_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None


class PartnerUpdateSchema(BaseModel):
    business_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    auto_accept_bookings: Optional[bool] = None
    notification_preferences: Optional[dict] = None


class BankDetailsSchema(BaseModel):
    account_number: str
    ifsc: str
    holder_name: str


class AvailabilityUpdateSchema(BaseModel):
    unavailable_dates: List[str]  # ["YYYY-MM-DD"]


class SettingsUpdateSchema(BaseModel):
    auto_accept_bookings: Optional[bool] = None
    notification_preferences: Optional[dict] = None


# ─── Response Schemas ─────────────────────────────────────────────────────────

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
    bank_account_number: Optional[str]
    bank_ifsc: Optional[str]
    bank_account_holder: Optional[str]
    auto_accept_bookings: bool
    unavailable_dates: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponseSchema(BaseModel):
    id: int
    document_type: DocumentType
    file_url: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PayoutResponseSchema(BaseModel):
    id: int
    amount: float
    status: PayoutStatus
    reference_number: Optional[str]
    remarks: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Standard Response ────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: str = ""
