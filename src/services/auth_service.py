"""
services/auth_service.py
Authentication business logic — aligned to Module 1 spec.

Spec compliance vs previous version:
  [FIXED] POST /register       → bcrypt hash + OTP via Twilio + return user_id
  [FIXED] POST /send-otp       → Redis key = otp:{phone}, TTL 5 min
  [FIXED] POST /verify-otp     → mark verified + JWT access + refresh tokens
  [FIXED] POST /resend-otp     → rate limit: max 3 resends per 10 min
  [FIXED] POST /login          → phone OR email + bcrypt verify + token pair + Redis
  [FIXED] POST /login/otp      → send OTP to phone, verify, issue tokens
  [FIXED] POST /refresh-token  → validate JTI in Redis + rotate (invalidate old JTI)
  [FIXED] POST /forgot-password → OTP to registered phone
  [FIXED] POST /reset-password  → validate OTP + update bcrypt hash in DB
  [FIXED] POST /change-password → verify old password + update bcrypt hash
  [FIXED] POST /logout          → blacklist JTI with TTL = token remaining expiry
  [FIXED] POST /logout-all      → blacklist all JTIs for user from Redis
"""

import random
import string
from datetime import datetime
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
    blacklist_jti, is_jti_blacklisted,
    store_refresh_jti, get_refresh_jti,
    delete_refresh_jti, delete_all_refresh_jtis,
    store_refresh_token, delete_refresh_token, delete_all_refresh_tokens
)
from src.core.config import settings
from src.integrations.twilio import send_sms


# ── Helpers ───────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Generate a 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


async def send_sms_otp(phone: str, otp: str) -> None:
    """Send OTP via Twilio or MSG91 (DEBUG mode prints to console)."""
    await send_sms(phone, otp)


# ═══════════════════════════════════════════════════════════════
# 1. REGISTRATION
# POST /register
# Spec: phone+email+password → bcrypt hash → send OTP via Twilio → return user_id
# ═══════════════════════════════════════════════════════════════

async def register_user(data: RegisterRequest, db: AsyncSession) -> dict:
    # Check duplicate phone
    result = await db.execute(select(User).where(User.phone == data.phone))
    if result.scalar_one_or_none():
        raise ValueError("Phone number already registered")

    # Check duplicate email
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

    # Create unverified user — bcrypt hash password
    user = User(
        phone=data.phone,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),   # bcrypt via passlib
        is_phone_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate OTP → store in Redis key: otp:register:{phone}, TTL 5 min
    otp = generate_otp()
    await store_otp(data.phone, otp, purpose="register")
    await send_sms_otp(data.phone, otp)   # send via Twilio

    return {"user_id": str(user.id), "message": "OTP sent to your phone"}


# ═══════════════════════════════════════════════════════════════
# 2. SEND OTP
# POST /send-otp
# Spec: store in Redis key otp:{phone}, TTL 5 min
# ═══════════════════════════════════════════════════════════════

async def send_otp(phone: str, purpose: str) -> dict:
    """Send OTP for any purpose. Redis key: otp:{purpose}:{phone}, TTL 5 min."""
    otp = generate_otp()
    await store_otp(phone, otp, purpose=purpose)   # key = otp:{purpose}:{phone}
    await send_sms_otp(phone, otp)
    return {
        "message":    "OTP sent successfully",
        "phone":      phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }


# ═══════════════════════════════════════════════════════════════
# 3. VERIFY OTP
# POST /verify-otp
# Spec: validate OTP from Redis → mark user verified → JWT access + refresh tokens
# ═══════════════════════════════════════════════════════════════

async def verify_otp_and_login(
    data: VerifyOTPRequest,
    db: AsyncSession,
    device_id: str = "default"
) -> dict:
    # Track failed attempts
    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise ValueError("Too many incorrect attempts. Request a new OTP.")

    # Validate OTP from Redis
    stored_otp = await get_otp(data.phone, purpose=data.purpose)
    if not stored_otp:
        raise ValueError("OTP expired. Please request a new one.")
    if stored_otp != data.otp:
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise ValueError(f"Incorrect OTP. {remaining} attempts remaining.")

    # Clear OTP + attempts from Redis
    await delete_otp(data.phone, purpose=data.purpose)
    await clear_otp_attempts(data.phone)

    # Get user
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # Mark phone verified
    user.is_phone_verified = True
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Generate JWT access + refresh tokens (both include JTI)
    access_token  = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    # Store refresh token JTI in Redis
    refresh_payload = decode_token(refresh_token)
    await store_refresh_jti(str(user.id), device_id, refresh_payload["jti"])

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user":          user,
    }


# ═══════════════════════════════════════════════════════════════
# 4. RESEND OTP
# POST /resend-otp
# Spec: rate limit max 3 resends per 10 min
# ═══════════════════════════════════════════════════════════════

async def resend_otp(phone: str, purpose: str) -> dict:
    """Resend OTP — max 3 resends per 10 minute window."""
    count = await get_resend_count(phone)
    if count >= settings.OTP_RESEND_MAX:
        ttl = await get_resend_ttl(phone)
        mins = round(ttl / 60)
        raise ValueError(
            f"Maximum {settings.OTP_RESEND_MAX} resends reached. "
            f"Try again in {mins} minute(s)."
        )

    await increment_resend_count(phone)
    return await send_otp(phone, purpose)


# ═══════════════════════════════════════════════════════════════
# 5. LOGIN — PASSWORD
# POST /login
# Spec: phone OR email + bcrypt verify + token pair + store refresh in Redis
# ═══════════════════════════════════════════════════════════════

async def login_with_password(data: LoginRequest, db: AsyncSession) -> dict:
    # Allow login with phone OR email
    result = await db.execute(
        select(User).where(
            or_(User.phone == data.phone_or_email, User.email == data.phone_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise ValueError("Invalid credentials")

    # Verify bcrypt hash
    if not verify_password(data.password, user.password_hash):
        raise ValueError("Invalid credentials")

    if not user.is_phone_verified:
        raise ValueError("Phone not verified. Please verify your OTP first.")

    if user.status != "active":
        raise ValueError("Account suspended. Contact support.")

    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate token pair
    access_token  = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    # Store refresh token JTI in Redis
    refresh_payload = decode_token(refresh_token)
    await store_refresh_jti(str(user.id), data.device_id or "default", refresh_payload["jti"])

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user":          user,
    }


# ═══════════════════════════════════════════════════════════════
# 6. LOGIN — OTP (Passwordless)
# POST /login/otp
# Spec: send OTP to phone, verify, issue tokens
# ═══════════════════════════════════════════════════════════════

async def login_with_otp(data: OTPLoginRequest, db: AsyncSession) -> dict:
    verify_data = VerifyOTPRequest(
        phone=data.phone,
        otp=data.otp,
        purpose="login"
    )
    return await verify_otp_and_login(verify_data, db, data.device_id or "default")


# ═══════════════════════════════════════════════════════════════
# 7. REFRESH TOKEN
# POST /refresh-token
# Spec: validate JTI in Redis → issue new pair → invalidate old JTI
# ═══════════════════════════════════════════════════════════════

async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession,
    device_id: str = "default"
) -> dict:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise ValueError("Invalid or expired refresh token")

    jti     = payload.get("jti")
    user_id = payload.get("sub")

    # Validate JTI exists in Redis (not already rotated/revoked)
    stored_jti = await get_refresh_jti(user_id, device_id)
    if stored_jti != jti:
        raise ValueError("Refresh token has been revoked or already used")

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # Invalidate old JTI immediately (rotation)
    await delete_refresh_jti(user_id, device_id)

    # Issue new token pair
    new_access  = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id), user.role)

    # Store new refresh JTI
    new_refresh_payload = decode_token(new_refresh)
    await store_refresh_jti(str(user.id), device_id, new_refresh_payload["jti"])

    return {
        "access_token":  new_access,
        "refresh_token": new_refresh,
        "token_type":    "bearer",
        "user":          user,
    }


# ═══════════════════════════════════════════════════════════════
# 8. FORGOT PASSWORD
# POST /forgot-password
# Spec: send OTP to registered phone
# ═══════════════════════════════════════════════════════════════

async def forgot_password(phone: str, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    # Security: don't reveal if phone exists
    if not user:
        return {"message": "If this number is registered, you will receive an OTP"}

    count = await get_resend_count(phone)
    if count >= settings.OTP_RESEND_MAX:
        ttl = await get_resend_ttl(phone)
        raise ValueError(f"Too many requests. Try again in {round(ttl/60)} minute(s).")

    otp = generate_otp()
    await store_otp(phone, otp, purpose="forgot_password")
    await increment_resend_count(phone)
    await send_sms_otp(phone, otp)

    return {"message": "OTP sent to your registered phone number"}


# ═══════════════════════════════════════════════════════════════
# 9. RESET PASSWORD
# POST /reset-password
# Spec: validate OTP + update new hashed password in DB
# ═══════════════════════════════════════════════════════════════

async def reset_password(data: ResetPasswordRequest, db: AsyncSession) -> dict:
    # Validate OTP
    stored_otp = await get_otp(data.phone, purpose="forgot_password")
    if not stored_otp or stored_otp != data.otp:
        raise ValueError("Invalid or expired OTP")

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # Update bcrypt hash in DB
    user.password_hash = hash_password(data.new_password)
    await db.commit()

    # Cleanup
    await delete_otp(data.phone, purpose="forgot_password")
    await delete_all_refresh_jtis(str(user.id))   # force re-login on all devices

    return {"message": "Password reset successfully. Please login with your new password."}


# ═══════════════════════════════════════════════════════════════
# 10. CHANGE PASSWORD
# POST /change-password
# Spec: authenticated — verify old password, update new bcrypt hash
# ═══════════════════════════════════════════════════════════════

async def change_password(
    data: ChangePasswordRequest,
    current_user: User,
    db: AsyncSession
) -> dict:
    if not current_user.password_hash:
        raise ValueError("This account uses OTP login. Password cannot be changed.")

    # Verify old password (bcrypt)
    if not verify_password(data.current_password, current_user.password_hash):
        raise ValueError("Current password is incorrect")

    # Update new bcrypt hash in DB
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()

    # Logout all other devices for security
    await delete_all_refresh_jtis(str(current_user.id))

    return {"message": "Password changed successfully. Please login again on other devices."}


# ═══════════════════════════════════════════════════════════════
# 11. LOGOUT
# POST /logout
# Spec: blacklist JTI with TTL = token remaining expiry
# ═══════════════════════════════════════════════════════════════

async def logout(user_id: str, access_token: str, device_id: str = "default") -> dict:
    payload = decode_token(access_token)
    if payload:
        jti = payload.get("jti")
        # TTL = remaining seconds until token naturally expires
        expire_in = max(0, int(payload["exp"] - datetime.utcnow().timestamp()))
        # Blacklist JTI (not full token) in Redis with remaining TTL
        await blacklist_jti(jti, expire_in)

    await delete_refresh_jti(user_id, device_id)
    return {"message": "Logged out successfully"}


# ═══════════════════════════════════════════════════════════════
# 12. LOGOUT ALL
# POST /logout-all
# Spec: blacklist all active session JTIs for user from Redis
# ═══════════════════════════════════════════════════════════════

async def logout_all(user_id: str, access_token: str) -> dict:
    payload = decode_token(access_token)
    if payload:
        jti = payload.get("jti")
        expire_in = max(0, int(payload["exp"] - datetime.utcnow().timestamp()))
        await blacklist_jti(jti, expire_in)

    # Delete all refresh JTIs for this user from Redis
    await delete_all_refresh_jtis(user_id)
    return {"message": "Logged out from all devices"}
