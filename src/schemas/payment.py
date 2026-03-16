from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class InitiatePaymentRequest(BaseModel):
    user_id: UUID
    booking_id: UUID
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    payment_method: str = "razorpay"
    coupon_code: Optional[str] = None


class InitiatePaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[UUID] = None
    razorpay_order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    message: str


class VerifyPaymentRequest(BaseModel):
    transaction_id: UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[UUID] = None
    status: str
    message: str


class TransactionOut(BaseModel):
    id: UUID
    user_id: UUID
    booking_id: Optional[UUID] = None
    amount: float
    currency: str = "INR"
    status: str
    payment_method: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaymentHistoryResponse(BaseModel):
    success: bool
    transactions: List[TransactionOut] = []
    total: int = 0


class PaymentMethodItem(BaseModel):
    id: str
    name: str
    type: str
    icon: Optional[str] = None
    is_active: bool = True


class PaymentMethodsResponse(BaseModel):
    success: bool
    methods: List[PaymentMethodItem] = []


class ValidateUPIRequest(BaseModel):
    upi_id: str
    user_id: UUID


class ValidateUPIResponse(BaseModel):
    success: bool
    upi_id: str
    is_valid: bool
    name: Optional[str] = None
    message: str


# SavedCard — field names match DB columns
class SavedCardOut(BaseModel):
    id: UUID
    user_id: UUID
    last4: str
    card_network: str
    card_name: Optional[str] = None
    expiry_month: int
    expiry_year: int
    is_default: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedCardsResponse(BaseModel):
    success: bool
    cards: List[SavedCardOut] = []


class SaveCardRequest(BaseModel):
    user_id: UUID
    razorpay_token: str
    last4: str
    card_network: str
    card_name: Optional[str] = None
    expiry_month: int
    expiry_year: int
    is_default: bool = False


class SaveCardResponse(BaseModel):
    success: bool
    card: Optional[SavedCardOut] = None
    message: str


class DeleteCardResponse(BaseModel):
    success: bool
    message: str


class RefundRequest(BaseModel):
    user_id: UUID
    transaction_id: UUID
    reason: Optional[str] = None
    amount: Optional[float] = None


class RefundOut(BaseModel):
    id: UUID
    transaction_id: UUID
    user_id: UUID
    amount: float
    status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RefundResponse(BaseModel):
    success: bool
    refund: Optional[RefundOut] = None
    message: str


class RefundsListResponse(BaseModel):
    success: bool
    refunds: List[RefundOut] = []
    total: int = 0


class PayLaterCheckRequest(BaseModel):
    user_id: UUID
    amount: float


class PayLaterCheckResponse(BaseModel):
    success: bool
    eligible: bool
    credit_limit: float = 0.0
    available_limit: float = 0.0
    message: str


class PayLaterApplyRequest(BaseModel):
    user_id: UUID
    booking_id: UUID
    amount: float


class PayLaterApplyResponse(BaseModel):
    success: bool
    transaction_id: Optional[UUID] = None
    amount: float
    due_date: Optional[datetime] = None
    message: str


class WebhookPayload(BaseModel):
    event: str
    payload: dict = {}