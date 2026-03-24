import uuid

from decimal import Decimal

from datetime import datetime

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Text

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship

from src.models.base import Base  # ← correct import
 
 
class Wallet(Base):

    __tablename__ = "wallets"
 
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    balance     = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    status      = Column(String, default="active")

    created_at  = Column(DateTime, default=datetime.utcnow)

    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    user                = relationship("User", back_populates="wallet")

    transactions        = relationship("WalletTransaction", back_populates="wallet")

    withdrawal_requests = relationship("WithdrawalRequest", back_populates="wallet")
 
 
class WalletTransaction(Base):

    __tablename__ = "wallet_transactions"
 
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    wallet_id     = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False, index=True)  # ← index added

    type          = Column(String, nullable=False)

    category      = Column(String, nullable=False)

    amount        = Column(Numeric(12, 2), nullable=False)

    balance_after = Column(Numeric(12, 2), nullable=False)

    description   = Column(Text, nullable=True)

    reference_id  = Column(String, nullable=True)

    status        = Column(String, default="success")

    created_at    = Column(DateTime, default=datetime.utcnow)
 
    wallet = relationship("Wallet", back_populates="transactions")
 
 
class WithdrawalRequest(Base):

    __tablename__ = "withdrawal_requests"
 
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    wallet_id           = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False, index=True)  # ← index added

    amount              = Column(Numeric(12, 2), nullable=False)

    bank_account_number = Column(String, nullable=False)

    bank_ifsc           = Column(String, nullable=False)

    bank_name           = Column(String, nullable=True)

    account_holder_name = Column(String, nullable=True)

    status              = Column(String, default="pending")

    rejection_reason    = Column(Text, nullable=True)

    created_at          = Column(DateTime, default=datetime.utcnow)

    processed_at        = Column(DateTime, nullable=True)
 
    wallet = relationship("Wallet", back_populates="withdrawal_requests")
 