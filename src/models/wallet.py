

"""
src/models/wallet.py
SQLAlchemy Models for Wallet — Module 3
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from src.core.database import get_db 

from src.core.database import Base  

class TransactionType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT  = "DEBIT"


class WithdrawalStatus(str, enum.Enum):
    PENDING     = "PENDING"
    APPROVED    = "APPROVED"
    TRANSFERRED = "TRANSFERRED"
    REJECTED    = "REJECTED"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    type        = Column(SAEnum(TransactionType), nullable=False)
    amount      = Column(Float, nullable=False)
    reference   = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WalletTransaction id={self.id} type={self.type} amount={self.amount}>"


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id              = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount               = Column(Float, nullable=False)
    bank_account_number  = Column(String(50), nullable=False)
    ifsc_code            = Column(String(20), nullable=False)
    account_holder_name  = Column(String(200), nullable=False)
    status               = Column(SAEnum(WithdrawalStatus), default=WithdrawalStatus.PENDING, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<WithdrawalRequest id={self.id} amount={self.amount} status={self.status}>"
