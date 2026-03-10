#DB tables:transactions, refunds, saved_cards
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base

class PaymentStatus(str, PyEnum):
    INITIATED      = "INITIATED"
    PENDING        = "PENDING"
    SUCCESS        = "SUCCESS"
    FAILED         = "FAILED"
    REFUNDED       = "REFUNDED"
    PARTIAL_REFUND = "PARTIAL_REFUND"

class PaymentMethod(str, PyEnum):
    UPI         = "UPI"
    CARD        = "CARD"
    NET_BANKING = "NET_BANKING"
    WALLET      = "WALLET"
    EMI         = "EMI"
    PAY_LATER   = "PAY_LATER"

class RefundStatus(str, PyEnum):
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS    = "SUCCESS"
    FAILED     = "FAILED"

class Transaction(Base):
    __tablename__ = "transactions"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id          = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id             = Column(UUID(as_uuid=True), nullable=False, index=True)
    razorpay_order_id   = Column(String(100), unique=True, nullable=True, index=True)
    razorpay_payment_id = Column(String(100), unique=True, nullable=True)
    razorpay_signature  = Column(String(512), nullable=True)
    amount              = Column(Numeric(10, 2), nullable=False)
    currency            = Column(String(3), nullable=False, default="INR")
    status              = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.INITIATED)
    payment_method      = Column(Enum(PaymentMethod), nullable=True)
    payment_metadata    = Column(Text, nullable=True)
    initiated_at        = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    refunds             = relationship("Refund", back_populates="transaction", lazy="select")

class Refund(Base):
    __tablename__ = "refunds"
    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id            = Column(UUID(as_uuid=True), nullable=False, index=True)
    booking_id         = Column(UUID(as_uuid=True), nullable=False, index=True)
    razorpay_refund_id = Column(String(100), unique=True, nullable=True)
    amount             = Column(Numeric(10, 2), nullable=False)
    status             = Column(Enum(RefundStatus), nullable=False, default=RefundStatus.PENDING)
    reason             = Column(String(255), nullable=True)
    notes              = Column(Text, nullable=True)
    requested_at       = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at       = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at         = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    transaction        = relationship("Transaction", back_populates="refunds")

class SavedCard(Base):
    __tablename__ = "saved_cards"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    razorpay_token = Column(String(200), nullable=False)
    card_network   = Column(String(20),  nullable=True)
    last4          = Column(String(4),   nullable=True)
    card_name      = Column(String(100), nullable=True)
    expiry_month   = Column(Integer,     nullable=True)
    expiry_year    = Column(Integer,     nullable=True)
    is_default     = Column(Boolean,     nullable=False, default=False)
    created_at     = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime,    nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)