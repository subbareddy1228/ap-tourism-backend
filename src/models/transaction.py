import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), nullable=False)
    booking_id          = Column(UUID(as_uuid=True), nullable=True)
    amount              = Column(Float, nullable=False)
    currency            = Column(String(10), default="INR")
    status              = Column(String(50), default="pending")
    payment_method      = Column(String(50), nullable=True)
    razorpay_order_id   = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_signature  = Column(String(255), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SavedCard(Base):
    __tablename__ = "saved_cards"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False)
    razorpay_token = Column(String(200), nullable=True)
    last4          = Column(String(4), nullable=False)
    card_network   = Column(String(50), nullable=False)
    card_name      = Column(String(100), nullable=True)
    expiry_month   = Column(Float, nullable=False)
    expiry_year    = Column(Float, nullable=False)
    is_default     = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Refund(Base):
    __tablename__ = "refunds"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id     = Column(UUID(as_uuid=True), nullable=False)
    user_id            = Column(UUID(as_uuid=True), nullable=False)
    amount             = Column(Float, nullable=False)
    status             = Column(String(50), default="pending")
    reason             = Column(Text, nullable=True)
    razorpay_refund_id = Column(String(100), nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)