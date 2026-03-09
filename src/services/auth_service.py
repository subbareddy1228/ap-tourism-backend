"""
services/auth_service.py
Authentication business logic — aligned to Module 1 spec.
"""

import random
import string
import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from src.models.user import User
from src.schemas.auth import (
    RegisterRequest, VerifyOTPRequest, LoginRequest,
    OTPLoginRequest, ResetPasswordRequest, ChangePasswordRequest
)
from src.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from src.core.redis import (
    store_otp, get_otp, delete_otp,
    increment_resend_count, get_resend_count, get_resend_ttl,
    increment_otp_attempts, clear_otp_attempts,
    blacklist_jti, store_refresh_jti, get_refresh_jti,
    delete_refresh_jti, delete_all_refresh_jtis
)
from src.core.config import settings
from src.integrations.twilio import send_sms

logger = logging.getLogger(__name__)


# ───────────────── Helpers ─────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def send_sms_otp(phone: str, otp: str) -> None:
    await send_sms(phone, otp)


# ═════════════════ REGISTER ═════════════════

async def register_user(data: RegisterRequest, db: AsyncSession) -> dict:

    logger.info("Registration attempt phone=%s", data.phone)

    result = await db.execute(
        select(User).where(
            or_(User.phone == data.phone, User.email == data.email)
        )
    )

    if result.scalar_one_or_none():
        logger.warning("Duplicate registration attempt phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone or email already registered"
        )

    user = User(
        phone=data.phone,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        is_phone_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    otp = generate_otp()

    await store_otp(data.phone, otp, purpose="register")
    await send_sms_otp(data.phone, otp)

    logger.info("User registered successfully user_id=%s", user.id)

    return {"user_id": str(user.id), "message": "OTP sent to your phone"}


# ═════════════════ SEND OTP ═════════════════

async def send_otp(phone: str, purpose: str) -> dict:

    logger.info("Sending OTP phone=%s purpose=%s", phone, purpose)

    otp = generate_otp()

    await store_otp(phone, otp, purpose=purpose)
    await send_sms_otp(phone, otp)

    return {
        "message": "OTP sent successfully",
        "phone": phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }


# ═════════════════ VERIFY OTP ═════════════════

async def verify_otp_and_login(
    data: VerifyOTPRequest,
    db: AsyncSession,
    device_id: str = "default"
) -> dict:

    logger.info("OTP verification attempt phone=%s", data.phone)

    attempts = await increment_otp_attempts(data.phone)

    if attempts > settings.OTP_MAX_ATTEMPTS:
        logger.warning("Too many OTP attempts phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Request a new OTP."
        )

    stored_otp = await get_otp(data.phone, purpose=data.purpose)

    if not stored_otp:
        logger.warning("Expired OTP phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired. Please request a new one."
        )

    if stored_otp != data.otp:
        logger.warning("Invalid OTP entered phone=%s", data.phone)
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect OTP. {remaining} attempts remaining."
        )

    await delete_otp(data.phone, purpose=data.purpose)
    await clear_otp_attempts(data.phone)

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user:
        logger.error("User not found during OTP verification phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_phone_verified = True
    user.last_login = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    refresh_payload = decode_token(refresh_token)

    await store_refresh_jti(str(user.id), device_id, refresh_payload["jti"])

    logger.info("OTP login success user_id=%s", user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


# ═════════════════ LOGIN PASSWORD ═════════════════

async def login_with_password(data: LoginRequest, db: AsyncSession) -> dict:

    logger.info("Login attempt identifier=%s", data.phone_or_email)

    identifier = data.phone_or_email.strip().lower()

    result = await db.execute(
        select(User).where(
            or_(User.phone == identifier, User.email == identifier)
        )
    )

    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        logger.warning("Invalid login attempt identifier=%s", identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not verify_password(data.password, user.password_hash):
        logger.warning("Invalid password identifier=%s", identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone not verified"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    user.last_login = datetime.utcnow()

    await db.commit()

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    refresh_payload = decode_token(refresh_token)

    await store_refresh_jti(
        str(user.id),
        data.device_id or "default",
        refresh_payload["jti"]
    )

    logger.info("Login success user_id=%s", user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


# ═════════════════ RESET PASSWORD ═════════════════

async def reset_password(data: ResetPasswordRequest, db: AsyncSession) -> dict:

    logger.info("Password reset attempt phone=%s", data.phone)

    stored_otp = await get_otp(data.phone, purpose="forgot_password")

    if not stored_otp or stored_otp != data.otp:
        logger.warning("Invalid reset OTP phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.password_hash = hash_password(data.new_password)
    user.last_password_change = datetime.utcnow()

    await db.commit()

    await delete_otp(data.phone, purpose="forgot_password")
    await delete_all_refresh_jtis(str(user.id))

    logger.info("Password reset success user_id=%s", user.id)

    return {"message": "Password reset successfully. Please login again."}


# ═════════════════ LOGOUT ═════════════════

async def logout(user_id: str, access_token: str, device_id: str = "default") -> dict:

    logger.info("Logout attempt user_id=%s device_id=%s", user_id, device_id)

    payload = decode_token(access_token)

    if payload:
        jti = payload.get("jti")
        expire_in = max(0, int(payload["exp"] - int(datetime.utcnow().timestamp())))
        await blacklist_jti(jti, expire_in)

    await delete_refresh_jti(user_id, device_id)

    logger.info("Logout success user_id=%s", user_id)

    return {"message": "Logged out successfully"}


# ═════════════════ LOGOUT ALL ═════════════════

async def logout_all(user_id: str, access_token: str) -> dict:

    logger.info("Logout all devices user_id=%s", user_id)

    payload = decode_token(access_token)

    if payload:
        jti = payload.get("jti")
        expire_in = max(0, int(payload["exp"] - int(datetime.utcnow().timestamp())))
        await blacklist_jti(jti, expire_in)

    await delete_all_refresh_jtis(user_id)

    return {"message": "Logged out from all devices"}