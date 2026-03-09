# """
# core/config.py
# All environment variables and app settings loaded from .env
# """

# from pydantic_settings import BaseSettings
# from typing import List


# class Settings(BaseSettings):
#     # ── App ───────────────────────────────────────────────────
#     APP_NAME: str = "AP Tourism Backend"
#     APP_VERSION: str = "1.0.0"
#     DEBUG: bool = False
#     ENVIRONMENT: str = "development"

#     # ── Security ──────────────────────────────────────────────
#     SECRET_KEY: str = "your-super-secret-key-change-in-production"
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
#     REFRESH_TOKEN_EXPIRE_DAYS: int = 7

#     # ── Database ──────────────────────────────────────────────
#     DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/ap_tourism"

#     # ── Redis ─────────────────────────────────────────────────
#     REDIS_URL: str = "redis://localhost:6379/0"
#     OTP_EXPIRE_SECONDS: int = 300          # 5 minutes
#     OTP_RESEND_COOLDOWN_SECONDS: int = 60  # 1 minute
#     OTP_MAX_ATTEMPTS: int = 5
#     OTP_RESEND_MAX: int = 3                 # max 3 resends per window
#     OTP_RESEND_WINDOW_SECONDS: int = 600   # 10 minute window

#     # ── CORS ──────────────────────────────────────────────────
#     ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

#     # ── SMS (MSG91 / Twilio) ──────────────────────────────────
#     SMS_PROVIDER: str = "msg91"           # msg91 or twilio
#     MSG91_API_KEY: str = ""
#     MSG91_TEMPLATE_ID: str = ""
#     TWILIO_ACCOUNT_SID: str = ""
#     TWILIO_AUTH_TOKEN: str = ""
#     TWILIO_FROM_NUMBER: str = ""

#     # ── AWS S3 ────────────────────────────────────────────────
#     AWS_ACCESS_KEY_ID: str = ""
#     AWS_SECRET_ACCESS_KEY: str = ""
#     AWS_BUCKET_NAME: str = "ap-tourism-media"
#     AWS_REGION: str = "ap-south-1"

#     # ── Razorpay ──────────────────────────────────────────────
#     RAZORPAY_KEY_ID:     str = ""
#     RAZORPAY_KEY_SECRET: str = ""

#     class Config:
#         env_file = ".env"
#         case_sensitive = True


# settings = Settings()

# # This will be appended — add these inside the Settings class manually:
# # RAZORPAY_KEY_ID: str = ""
# # RAZORPAY_KEY_SECRET: str = ""




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
