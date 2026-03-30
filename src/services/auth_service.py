"""
services/auth_service.py
Authentication business logic — aligned to Module 1 spec.
"""

import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from src.models.user import User
from src.models.user_profile import UserProfile                    # ← ADDED
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
    delete_refresh_jti, delete_all_refresh_jtis,
    store_email_otp, get_email_otp, delete_email_otp,
    increment_email_otp_attempts, clear_email_otp_attempts,
    increment_email_resend_count, get_email_resend_count,
)

from src.common.utils import generate_otp
from src.common.enums import UserStatus
from src.core.config import settings
from src.integrations.twilio import send_sms
from src.integrations.email import send_email_otp

logger = logging.getLogger(__name__)


# ───────────────── Helpers ─────────────────

async def send_sms_otp(phone: str, otp: str) -> None:
    """Send OTP using configured SMS provider."""
    await send_sms(phone, otp)


# ═════════════════ REGISTER ═════════════════

async def register_user(data: RegisterRequest, db: AsyncSession) -> dict:

    logger.info("Registration attempt phone=%s", data.phone)

    # ───────── Check if user exists (phone or email) ─────────
    result = await db.execute(
        select(User).where(
            or_(
                User.phone == data.phone,
                User.email == data.email
            )
        )
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:

        # ───── Restore deleted user ─────
        if existing_user.deleted_at is not None:

            logger.info("Reactivating deleted user phone=%s", data.phone)

            existing_user.deleted_at = None
            existing_user.status = UserStatus.ACTIVE
            existing_user.full_name = data.full_name
            existing_user.password_hash = hash_password(data.password)
            existing_user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(existing_user)

            otp = generate_otp()
            await store_otp(data.phone, otp, purpose="register")

            await send_sms_otp(data.phone, otp)

            return {
                "user_id": str(existing_user.id),
                "message": "Account reactivated. OTP sent."
            }

        # ───── Active user exists ─────
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    # ───────── Generate OTP ─────────
    otp = generate_otp()
    await store_otp(data.phone, otp, purpose="register")

    await send_sms_otp(data.phone, otp)

    # ───────── Create new user ─────────
    user = User(
        phone=data.phone,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        is_phone_verified=False,
        role="TRAVELER",
        status=UserStatus.ACTIVE
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        preferences={},
        language="en",
        kyc_status="pending"
    )

    db.add(profile)
    await db.commit()

    return {
        "user_id": str(user.id),
        "message": "OTP sent to your phone"
    }

# ═════════════════ SEND OTP ═════════════════
async def send_otp(phone: str, purpose: str) -> dict:
    otp = generate_otp()
    await store_otp(phone, otp, purpose=purpose)
    await send_sms_otp(phone, otp)

    return {
        "phone": phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }
# ═════════════════ RESEND OTP ═════════════════

async def resend_otp(phone: str, purpose: str) -> dict:

    resend_count = await get_resend_count(phone)

    if resend_count >= settings.OTP_RESEND_MAX:
        ttl = await get_resend_ttl(phone)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many resend attempts. Try again in {ttl} seconds."
        )

    await increment_resend_count(phone)

    otp = generate_otp()

    await store_otp(phone, otp, purpose=purpose)
    await send_sms_otp(phone, otp)

    return {
        "message": "OTP resent successfully",
        "phone": phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }


# ═════════════════ VERIFY OTP ═════════════════

async def verify_otp_and_login(
    data: VerifyOTPRequest,
    db: AsyncSession,
    device_id: str = "default"
) -> dict:

    attempts = await increment_otp_attempts(data.phone)

    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Request a new OTP."
        )

    stored_otp = await get_otp(data.phone, purpose=data.purpose)

    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired. Please request a new one."
        )

    if stored_otp != data.otp:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    user.is_phone_verified = True
    user.last_login = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)

    refresh_payload = decode_token(refresh_token)

    await store_refresh_jti(
        str(user.id),
        device_id,
        refresh_payload["jti"]
    )

    user_data = {
        "id": str(user.id),
        "phone": user.phone,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "is_phone_verified": user.is_phone_verified,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_data,
    }


# ═════════════════ LOGIN PASSWORD ═════════════════

async def login_with_password(data: LoginRequest, db: AsyncSession) -> dict:

    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )

    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone not verified"
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    user.last_login = datetime.utcnow()

    await db.commit()

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)

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
        "user": {
            "id": str(user.id),
            "phone": user.phone,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "status": user.status.value,
            "is_phone_verified": user.is_phone_verified,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
    }


# ═════════════════ LOGIN OTP (Passwordless) ═════════════════

async def login_with_otp(data: OTPLoginRequest, db: AsyncSession) -> dict:

    logger.info("OTP login attempt phone=%s", data.phone)

    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new OTP."
        )

    stored_otp = await get_otp(data.phone, purpose="login")
    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired. Please request a new one."
        )

    if stored_otp != data.otp:
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect OTP. {remaining} attempts remaining."
        )

    await delete_otp(data.phone, purpose="login")
    await clear_otp_attempts(data.phone)

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    refresh_payload = decode_token(refresh_token)
    await store_refresh_jti(str(user.id), data.device_id or "default", refresh_payload["jti"])

    logger.info("OTP login success user_id=%s", user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "phone": user.phone,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "status": user.status.value,
            "is_phone_verified": user.is_phone_verified,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
    }


# ═════════════════ FORGOT PASSWORD ═════════════════

async def forgot_password(phone: str, db: AsyncSession) -> dict:

    logger.info("Forgot password request phone=%s", phone)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if user exists — return generic message
        return {"message": "If the number is registered, an OTP has been sent."}

    otp = generate_otp()
    await store_otp(phone, otp, purpose="forgot_password")
    await send_sms_otp(phone, otp)

    logger.info("Forgot password OTP sent phone=%s", phone)
    return {"message": "OTP sent to your registered phone number."}


# ═════════════════ RESET PASSWORD ═════════════════

async def reset_password(data: ResetPasswordRequest, db: AsyncSession) -> dict:
 
    logger.info("Password reset attempt phone=%s", data.phone)
 
    # ── Brute-force protection ────────────────────────────────
    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        logger.warning("Too many reset attempts phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please request a new OTP."
        )
 
    stored_otp = await get_otp(data.phone, purpose="forgot_password")
 
    if not stored_otp or stored_otp != data.otp:
        logger.warning("Invalid reset OTP phone=%s", data.phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
 
    # ── OTP verified — clear attempts and proceed ─────────────
    await clear_otp_attempts(data.phone)
 
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
 
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
 
    user.password_hash = hash_password(data.new_password)
    db.add(user)
 
    await db.commit()
 
    await delete_otp(data.phone, purpose="forgot_password")
    await delete_all_refresh_jtis(str(user.id))
 
    logger.info("Password reset success user_id=%s", user.id)
    return {"message": "Password reset successfully. Please login again."}


# ═════════════════ REFRESH TOKEN ═════════════════

async def refresh_access_token(refresh_token: str, db: AsyncSession) -> dict:

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    device_id = payload.get("device_id", "default")
    jti = payload.get("jti")

    stored_jti = await get_refresh_jti(user_id, device_id)
    if not stored_jti or stored_jti != jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_access = create_access_token(str(user.id), user.role.value)
    new_refresh = create_refresh_token(str(user.id), user.role.value)
    new_payload = decode_token(new_refresh)
    await store_refresh_jti(str(user.id), device_id, new_payload["jti"])

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


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


# ═════════════════ SEND EMAIL VERIFICATION OTP ═════════════════

async def send_email_verification_otp(user: User) -> dict:
    """
    Generate a 6-digit OTP, store it in Redis (10 min TTL),
    and email it to the user's registered address.

    Rate-limited to OTP_RESEND_MAX sends per OTP_RESEND_WINDOW_SECONDS.
    """
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address on your account. Add one in profile settings first."
        )

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified."
        )

    # ── Rate limit ────────────────────────────────────────────
    resend_count = await get_email_resend_count(user.email)
    if resend_count >= settings.OTP_RESEND_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before requesting another OTP."
        )
    await increment_email_resend_count(user.email)

    # ── Generate + store + send ───────────────────────────────
    otp = generate_otp()
    await store_email_otp(user.email, otp, purpose="verify_email")

    sent = await send_email_otp(user.email, otp, purpose="verify_email")
    if not sent:
        logger.error("Failed to send email OTP to=%s user_id=%s", user.email, user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send email. Please check your address or try again later."
        )

    logger.info("Email verification OTP sent user_id=%s email=%s", user.id, user.email)
    return {
        "message": "OTP sent to your email address.",
        "email":   _mask_email(user.email),
        "expires_in": 600,
    }


# ═════════════════ VERIFY EMAIL OTP ═════════════════

async def verify_email_otp(otp: str, user: User, db: AsyncSession) -> dict:
    """
    Validate the OTP the user received by email and mark is_email_verified = True.
    Brute-force: max OTP_MAX_ATTEMPTS attempts before the OTP is invalidated.
    """
    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified."
        )

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address on your account."
        )

    # ── Brute-force guard ─────────────────────────────────────
    attempts = await increment_email_otp_attempts(user.email)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        await delete_email_otp(user.email, purpose="verify_email")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new OTP."
        )

    # ── Fetch stored OTP ──────────────────────────────────────
    stored_otp = await get_email_otp(user.email, purpose="verify_email")
    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired or not found. Please request a new one."
        )

    if stored_otp != otp:
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect OTP. {remaining} attempt(s) remaining."
        )

    # ── Mark verified ─────────────────────────────────────────
    await delete_email_otp(user.email, purpose="verify_email")
    await clear_email_otp_attempts(user.email)

    user.is_email_verified = True
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    logger.info("Email verified user_id=%s email=%s", user.id, user.email)
    return {"message": "Email verified successfully."}


# ── Internal helper ───────────────────────────────────────────

def _mask_email(email: str) -> str:
    """Return a masked email like  j***@gmail.com for display."""
    try:
        local, domain = email.split("@", 1)
        visible = local[:1] if len(local) <= 3 else local[:2]
        return f"{visible}***@{domain}"
    except Exception:
        return "***"


# ═════════════════ CHANGE PASSWORD ═════════════════

async def change_password(data: ChangePasswordRequest, current_user: User, db: AsyncSession) -> dict:

    logger.info("Change password user_id=%s", current_user.id)

    if not current_user.password_hash or not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.password_hash = hash_password(data.new_password)
    await db.commit()

    await delete_all_refresh_jtis(str(current_user.id))

    logger.info("Password changed user_id=%s", current_user.id)
    return {"message": "Password changed successfully. Please login again."}