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
    SECRET_KEY: str = "ap-tourism-9x8y7z6w5v4u3t2s1r0q-secret-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:1225@localhost:5432/ap_tourism"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    OTP_EXPIRE_SECONDS: int = 300
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_MAX: int = 3
    OTP_RESEND_WINDOW_SECONDS: int = 600

    # ── Redis — Search Module ─────────────────────────────────  ← ADDED
    REDIS_SUGGESTIONS_TTL: int = 300         # 5 minutes cache for suggestions
    REDIS_RECENT_SEARCHES_TTL: int = 604800  # 7 days for recent searches
    REDIS_RECENT_SEARCHES_MAX: int = 10      # keep last 10 searches per user

    # ── Elasticsearch ─────────────────────────────────────────  ← ADDED
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_MAX_RETRIES: int = 5
    ELASTICSEARCH_RETRY_DELAY: int = 3

    # ── CORS ──────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── SMS (MSG91 / Twilio) ──────────────────────────────────
    SMS_PROVIDER: str = "msg91"
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

    # ── Gmail SMTP ────────────────────────────────────────────
    GMAIL_SENDER:       str = ""
    GMAIL_APP_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()