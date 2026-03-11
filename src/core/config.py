
"""
core/config.py
All environment variables and app settings loaded from .env
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "AP Tourism Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/ap_tourism"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    OTP_EXPIRE_SECONDS: int = 300          # 5 minutes
    OTP_RESEND_COOLDOWN_SECONDS: int = 60  # 1 minute
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_MAX: int = 3                 # max 3 resends per window
    OTP_RESEND_WINDOW_SECONDS: int = 600   # 10 minute window

    # ── CORS ──────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── SMS (MSG91 / Twilio) ──────────────────────────────────
    SMS_PROVIDER: str = "msg91"           # msg91 or twilio
    MSG91_API_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── AWS S3 ────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "ap-tourism-media"
    AWS_REGION: str = "ap-south-1"

    # ── Razorpay ──────────────────────────────────────────────
    RAZORPAY_KEY_ID:     str = ""
    RAZORPAY_KEY_SECRET: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# This will be appended — add these inside the Settings class manually:
# RAZORPAY_KEY_ID: str = ""
# RAZORPAY_KEY_SECRET: str = ""
