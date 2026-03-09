"""
schemas/wallet.py
Pydantic schemas for all Wallet API request & response bodies.
"""

from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
from uuid import UUID


# ═══════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════

class TopupInitiateRequest(BaseModel):
    """POST /wallet/topup — initiate Razorpay order"""
    amount: Decimal   # amount in INR e.g. 500.00

    @field_validator("amount")
    def amount_valid(cls, v):
        if v < Decimal("10.00"):
            raise ValueError("Minimum topup amount is ₹10")
        if v > Decimal("100000.00"):
            raise ValueError("Maximum topup amount is ₹1,00,000")
        return v


class TopupVerifyRequest(BaseModel):
    """POST /wallet/topup/verify — verify Razorpay payment"""
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str


class WithdrawRequest(BaseModel):
    """POST /wallet/withdraw — request withdrawal to bank"""
    amount:              Decimal
    bank_account_number: str
    bank_ifsc:           str
    bank_name:           Optional[str] = None
    account_holder_name: Optional[str] = None

    @field_validator("amount")
    def amount_valid(cls, v):
        if v < Decimal("100.00"):
            raise ValueError("Minimum withdrawal amount is ₹100")
        return v

    @field_validator("bank_ifsc")
    def ifsc_valid(cls, v):
        v = v.upper().strip()
        if len(v) != 11:
            raise ValueError("IFSC code must be 11 characters")
        return v

    @field_validator("bank_account_number")
    def account_valid(cls, v):
        v = v.strip()
        if not v.isdigit() or not (9 <= len(v) <= 18):
            raise ValueError("Enter a valid bank account number")
        return v


# ═══════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class WalletBalanceResponse(BaseModel):
    """GET /wallet/balance"""
    wallet_id: UUID
    balance:   Decimal
    status:    str
    currency:  str = "INR"

    class Config:
        from_attributes = True


class TopupInitiateResponse(BaseModel):
    """Response after initiating topup — send to Razorpay SDK"""
    order_id:   str        # Razorpay order ID
    amount:     int        # amount in paise (multiply by 100)
    currency:   str = "INR"
    key_id:     str        # Razorpay key — needed by frontend SDK


class TransactionResponse(BaseModel):
    """Single transaction record"""
    id:            UUID
    type:          str     # credit / debit
    category:      str     # topup / booking_payment / refund / withdrawal
    amount:        Decimal
    balance_after: Decimal
    description:   Optional[str]
    reference_id:  Optional[str]
    status:        str
    created_at:    datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """GET /wallet/transactions"""
    transactions: List[TransactionResponse]
    total:        int
    page:         int
    per_page:     int


class WithdrawalResponse(BaseModel):
    """Single withdrawal request record"""
    id:                  UUID
    amount:              Decimal
    bank_account_number: str
    bank_ifsc:           str
    bank_name:           Optional[str]
    account_holder_name: Optional[str]
    status:              str
    rejection_reason:    Optional[str]
    created_at:          datetime
    processed_at:        Optional[datetime]

    class Config:
        from_attributes = True


class WithdrawalListResponse(BaseModel):
    """GET /wallet/withdraw/requests"""
    requests: List[WithdrawalResponse]
    total:    int
