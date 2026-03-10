from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from src.models.transaction import PaymentMethod, RefundStatus

class PaymentInitiateRequest(BaseModel):
    booking_id: UUID
    payment_method: Optional[PaymentMethod] = None
    coupon_code: Optional[str] = Field(None, max_length=50)
    model_config = {"use_enum_values": True}

class PaymentInitiateData(BaseModel):
    transaction_id: UUID
    razorpay_order_id: str
    key_id: str
    amount: Decimal
    currency: str
    status: str
    model_config = {"from_attributes": True}

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentVerifyData(BaseModel):
    transaction_id: UUID
    status: str
    booking_id: UUID

class TransactionData(BaseModel):
    id: UUID
    booking_id: UUID
    user_id: UUID
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: str
    payment_method: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class PaymentHistoryItem(BaseModel):
    id: UUID
    booking_id: UUID
    amount: Decimal
    currency: str
    status: str
    payment_method: Optional[str] = None
    initiated_at: datetime
    model_config = {"from_attributes": True}

class PaymentHistoryData(BaseModel):
    data: List[PaymentHistoryItem]
    total: int
    page: int
    pages: int
    limit: int

class RefundRequestSchema(BaseModel):
    booking_id: UUID
    reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class RefundData(BaseModel):
    id: UUID
    transaction_id: UUID
    booking_id: UUID
    razorpay_refund_id: Optional[str] = None
    amount: Decimal
    status: str
    reason: Optional[str] = None
    requested_at: datetime
    processed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class RefundListData(BaseModel):
    data: List[RefundData]
    total: int

class PaymentMethodInfo(BaseModel):
    method: str
    display_name: str
    enabled: bool

class UpiValidateRequest(BaseModel):
    upi_id: str = Field(..., example="user@upi")

class UpiValidateData(BaseModel):
    upi_id: str
    is_valid: bool
    name: Optional[str] = None

class SavedCardData(BaseModel):
    id: UUID
    razorpay_token: str
    card_network: Optional[str] = None
    last4: Optional[str] = None
    card_name: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    is_default: bool
    model_config = {"from_attributes": True}

class SaveCardRequest(BaseModel):
    razorpay_token: str
    card_name: Optional[str] = None
    is_default: bool = False

class PayLaterCheckRequest(BaseModel):
    booking_id: UUID

class PayLaterCheckData(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    deferred_days: int = 14

class PayLaterApplyRequest(BaseModel):
    booking_id: UUID
    deferred_days: int = Field(default=14, ge=7, le=14)

class PayLaterApplyData(BaseModel):
    transaction_id: UUID
    due_date: datetime
    amount: Decimal
