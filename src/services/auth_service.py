"""
services/auth_service.py
Authentication business logic — with full email verification flow.

Registration Flow:
  1. POST /auth/register         → creates user, sends phone OTP + email OTP
  2. POST /auth/verify-otp       → verify phone OTP → get JWT tokens
  3. POST /auth/verify-email     → verify email OTP → is_email_verified = True

Email OTP endpoints (for already logged-in users):
  POST /auth/send-email-otp      → send fresh email OTP
  POST /auth/resend-email-otp    → resend with rate limiting
"""

import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from src.common.email_templates import otp_email_template
from src.models import user
from src.models.user import User
from src.models.user_profile import UserProfile, UserSession
from src.schemas.auth import (
    RegisterRequest, VerifyOTPRequest, LoginRequest,
    OTPLoginRequest, ResetPasswordRequest, ChangePasswordRequest,
    VerifyEmailRequest,
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
from src.common.enums import LanguageEnum, UserStatus, UserRole
from src.core.config import settings
from src.integrations.msg91 import send_sms
from src.integrations.email import send_email_otp
from src.core.redis import store_register_data, get_register_data, delete_register_data

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

async def _send_phone_otp(phone: str, otp: str) -> None:
    """Send OTP via SMS (Twilio / MSG91)."""

    # ✅ ADD THIS LINE
    logger.info(f"DEV OTP (PHONE): {otp} for phone={phone}")

    await send_sms(phone, otp)
    

# ═══════════════════════════════════════════════
# SEND PHONE OTP
# ═══════════════════════════════════════════════

async def send_otp(phone: str, purpose: str = "login") -> dict:
    """
    Send OTP to phone for login / verification.
    """

    # Generate OTP
    otp = generate_otp()

    # Store in Redis
    await store_otp(phone, otp, purpose=purpose)

    # Send via SMS
    await _send_phone_otp(phone, otp)

    logger.info("OTP sent phone=%s purpose=%s", phone, purpose)

    return {
        "message": "OTP sent successfully",
        "phone": phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }

async def _send_email_otp_helper(email: str, otp: str, purpose: str = "verify_email") -> None:
    """Send OTP via email. Logs warning if email not configured, never crashes."""
    try:
        sent = await send_email_otp(email, otp, purpose)
        if not sent:
            logger.warning("Email OTP not sent (not configured) to=%s", email)
    except Exception as e:
        logger.error("Email OTP send failed email=%s error=%s", email, str(e))

async def _create_session(user: User, db: AsyncSession, device_id: str = "default") -> None:
    """Create a UserSession record on every login."""
    session = UserSession(
        user_id=user.id,
        jti=device_id,
        device_info=device_id,
        is_active=True,
        last_active=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    
def _user_dict(user: User) -> dict:
    return {
        "id":                str(user.id),
        "phone":             user.phone,
        "email":             user.email,
        "full_name":         user.full_name,
        "role":              user.role.value if hasattr(user.role, "value") else str(user.role),
        "status":            user.status.value if hasattr(user.status, "value") else str(user.status),
        "is_phone_verified": user.is_phone_verified,
        "is_email_verified": user.is_email_verified,
        "created_at":        user.created_at,
        "last_login":        user.last_login,
    }


def _mask_email(email: str) -> str:
    try:
        local, domain = email.split("@", 1)
        return local[0] + "***@" + domain
    except Exception:
        return email


# ═══════════════════════════════════════════════════════════════
# 1. REGISTER
# ═══════════════════════════════════════════════════════════════

async def register_user(data: RegisterRequest, db: AsyncSession) -> dict:
    """
    Register a new user.
    - Sends phone OTP via SMS
    - If email provided: also sends email verification OTP
    """
    logger.info("Registration attempt phone=%s email=%s", data.phone, data.email)

    # Check uniqueness
    if data.email:
        query = select(User).where(or_(User.phone == data.phone, User.email == data.email))
    else:
        query = select(User).where(User.phone == data.phone)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.deleted_at is not None:
            # Restore soft-deleted account
            existing.deleted_at    = None
            existing.status        = UserStatus.ACTIVE
            existing.full_name     = data.full_name
            existing.password_hash = hash_password(data.password)
            existing.updated_at    = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)

            phone_otp = generate_otp()
            await store_otp(data.phone, phone_otp, purpose="register")
            await _send_phone_otp(data.phone, phone_otp)

            email_otp_sent = False
            if data.email:
                email_otp = generate_otp()
                await store_email_otp(data.email, email_otp, purpose="verify_email")
                await send_email_otp(data.email, email_otp, purpose="verify_email")
                email_otp_sent = True

            return {
                "user_id": str(existing.id),
                "message": "Account reactivated. OTP sent to your phone.",
                "email_otp_sent": email_otp_sent,
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account already exists with this phone or email."
        )

    # Store user data temporarily in Redis
    await store_register_data(data.phone, {
        "phone": data.phone,
        "email": data.email,
        "full_name": data.full_name,
        "password_hash": hash_password(data.password),
        "role": data.role                              
})

    # Send phone OTP
    phone_otp = generate_otp()
    await store_otp(data.phone, phone_otp, purpose="register")
    await _send_phone_otp(data.phone, phone_otp)

    # Send email OTP if email provided
    email_otp_sent = False
    if data.email:
        email_otp = generate_otp()
        await store_email_otp(data.email, email_otp, purpose="verify_email")
        await send_email_otp(data.email, email_otp, purpose="verify_email")

        email_otp_sent = True
        logger.info("Email OTP sent phone=%s email=%s", data.phone, data.email)

    logger.info("Registration OTP sent phone=%s", data.phone)

    return {
    "message": "OTP sent to your phone. Please verify to complete registration.",
    "phone": data.phone,
    "email_otp_sent": email_otp_sent
}


# ═══════════════════════════════════════════════════════════════
# 2. SEND EMAIL VERIFICATION OTP
# ═══════════════════════════════════════════════════════════════

async def send_email_verification_otp(user: User) -> dict:
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address on your account. Add one in profile settings first."
        )
    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your email is already verified."
        )

    resend_count = await get_email_resend_count(user.email)
    if resend_count >= settings.OTP_RESEND_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many email OTP requests. Please wait before trying again."
        )

    await increment_email_resend_count(user.email)
    otp = generate_otp()
    await store_email_otp(user.email, otp, purpose="verify_email")

    # ✅ Direct async call — no Celery needed
    sent = await send_email_otp(user.email, otp, purpose="verify_email")
    if not sent:
        logger.warning("Email OTP not delivered to=%s", user.email)

    logger.info("Email verification OTP sent user_id=%s email=%s", user.id, user.email)
    return {
        "message":    "Verification OTP sent to your email address.",
        "email":      _mask_email(user.email),
        "expires_in": settings.OTP_EXPIRE_SECONDS,
    }

# ═══════════════════════════════════════════════════════════════
# 3. VERIFY EMAIL OTP
# ═══════════════════════════════════════════════════════════════

async def verify_email_otp(data: VerifyEmailRequest, user: User, db: AsyncSession) -> dict:
    """
    Verify email OTP and mark is_email_verified = True.
    Called by POST /auth/verify-email.
    """
    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="Your email is already verified.")

    if not user.email:
        raise HTTPException(status_code=400, detail="No email address on your account.")

    if user.email.lower() != str(data.email).lower():
        raise HTTPException(status_code=400, detail="Email does not match your registered email.")

    attempts = await increment_email_otp_attempts(user.email)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new OTP.")

    stored_otp = await get_email_otp(user.email, purpose="verify_email")
    if not stored_otp:
        raise HTTPException(
            status_code=400,
            detail="OTP expired. Request a new one via POST /auth/send-email-otp."
        )

    if stored_otp != data.otp:
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(status_code=401, detail=f"Incorrect OTP. {remaining} attempts remaining.")

    # Mark verified
    await delete_email_otp(user.email, purpose="verify_email")
    await clear_email_otp_attempts(user.email)

    user.is_email_verified = True
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    logger.info("Email verified user_id=%s email=%s", user.id, user.email)
    return {
        "message":          "Email verified successfully.",
        "email":            user.email,
        "is_email_verified": True,
    }


# ═══════════════════════════════════════════════════════════════
# 4. RESEND EMAIL OTP
# ═══════════════════════════════════════════════════════════════

async def resend_email_otp(user: User) -> dict:
    """Resend email OTP. Delegates to send_email_verification_otp."""
    return await send_email_verification_otp(user)


# ═══════════════════════════════════════════════════════════════
# 5. RESEND PHONE OTP
# ═══════════════════════════════════════════════════════════════

async def resend_otp(phone: str, purpose: str) -> dict:
    resend_count = await get_resend_count(phone)
    if resend_count >= settings.OTP_RESEND_MAX:
        ttl = await get_resend_ttl(phone)
        raise HTTPException(status_code=429, detail=f"Too many resend attempts. Try again in {ttl} seconds.")

    await increment_resend_count(phone)
    otp = generate_otp()
    logger.info(f"DEV OTP (RESEND): {otp} for phone={phone}")
    await store_otp(phone, otp, purpose=purpose)
    await _send_phone_otp(phone, otp)

    return {"message": "OTP resent successfully", "phone": phone, "expires_in": settings.OTP_EXPIRE_SECONDS}


# ═══════════════════════════════════════════════════════════════
# 6. VERIFY PHONE OTP → LOGIN
# ═══════════════════════════════════════════════════════════════

async def verify_otp_and_login(data: VerifyOTPRequest, db: AsyncSession, device_id: str = "default") -> dict:
    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new OTP.")

    stored_otp = await get_otp(data.phone, purpose=data.purpose)
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    if stored_otp != data.otp:
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(status_code=401, detail=f"Incorrect OTP. {remaining} attempts remaining.")

    await delete_otp(data.phone, purpose=data.purpose)
    await clear_otp_attempts(data.phone)

    # Check if user exists
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    # If NOT exist → create from Redis
    if not user:
        reg_data = await get_register_data(data.phone)

        if not reg_data:
            raise HTTPException(status_code=400, detail="Registration data expired. Please register again.")

        _role_str = reg_data.get("role", "TRAVELER").upper()
        _role = UserRole[_role_str] if _role_str in UserRole.__members__ else UserRole.TRAVELER

        user = User(
            phone=reg_data["phone"],
            email=reg_data.get("email"),
            full_name=reg_data["full_name"],
            password_hash=reg_data["password_hash"],
            is_phone_verified=True,
            is_email_verified=False,
            role=_role,                                   
            status=UserStatus.ACTIVE,
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create profile
        db.add(UserProfile(
            user_id=user.id,
            preferences={},
            language=LanguageEnum.ENGLISH,
            kyc_status="pending"
        ))
        await db.commit()

    # Delete temp Redis data
    await delete_register_data(data.phone)


    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account suspended")

    user.is_phone_verified = True
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    access_token  = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    jti = decode_token(refresh_token)["jti"]
    await store_refresh_jti(str(user.id), device_id, jti)
    await _create_session(user, db, device_id=jti)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": _user_dict(user)}


# ═══════════════════════════════════════════════════════════════
# 7. LOGIN WITH PASSWORD
# ═══════════════════════════════════════════════════════════════

async def login_with_password(data: LoginRequest, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_phone_verified:
        raise HTTPException(status_code=403, detail="Phone not verified")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account suspended")

    user.last_login = datetime.utcnow()
    await db.commit()

    access_token  = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    jti = decode_token(refresh_token)["jti"]
    await store_refresh_jti(str(user.id), data.device_id or "default", jti)
    await _create_session(user, db, device_id=jti)

    logger.info("Login success user_id=%s", user.id)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": _user_dict(user)}


# ═══════════════════════════════════════════════════════════════
# 8. LOGIN WITH OTP (Passwordless)
# ═══════════════════════════════════════════════════════════════

async def login_with_otp(data: OTPLoginRequest, db: AsyncSession) -> dict:
    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts.")

    stored_otp = await get_otp(data.phone, purpose="login")
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired.")
    if stored_otp != data.otp:
        raise HTTPException(status_code=401, detail=f"Incorrect OTP. {settings.OTP_MAX_ATTEMPTS - attempts} attempts remaining.")

    await delete_otp(data.phone, purpose="login")
    await clear_otp_attempts(data.phone)

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account suspended")

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    access_token  = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    jti = decode_token(refresh_token)["jti"]
    await store_refresh_jti(str(user.id), data.device_id or "default", jti)
    await _create_session(user, db, device_id=jti)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": _user_dict(user)}

# ═══════════════════════════════════════════════════════════════
# 9. FORGOT / RESET PASSWORD
# ═══════════════════════════════════════════════════════════════

async def forgot_password(phone: str, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If the number is registered, an OTP has been sent."}
    otp = generate_otp()
    await store_otp(phone, otp, purpose="forgot_password")
    await _send_phone_otp(phone, otp)
    return {"message": "OTP sent to your registered phone number."}


async def reset_password(data: ResetPasswordRequest, db: AsyncSession) -> dict:
    attempts = await increment_otp_attempts(data.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts.")

    stored_otp = await get_otp(data.phone, purpose="forgot_password")
    if not stored_otp or stored_otp != data.otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    await clear_otp_attempts(data.phone)

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    db.add(user)
    await db.commit()
    await delete_otp(data.phone, purpose="forgot_password")
    await delete_all_refresh_jtis(str(user.id))
    return {"message": "Password reset successfully. Please login again."}


# ═══════════════════════════════════════════════════════════════
# 10. REFRESH / LOGOUT / CHANGE PASSWORD
# ═══════════════════════════════════════════════════════════════

async def refresh_access_token(refresh_token: str, db: AsyncSession) -> dict:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored_jti = await get_refresh_jti(payload["sub"], payload.get("device_id", "default"))
    if not stored_jti or stored_jti != payload["jti"]:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access  = create_access_token(str(user.id), user.role.value)
    new_refresh = create_refresh_token(str(user.id), user.role.value)
    await store_refresh_jti(str(user.id), payload.get("device_id", "default"), decode_token(new_refresh)["jti"])
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


async def logout(user_id: str, access_token: str, device_id: str = "default") -> dict:
    payload = decode_token(access_token)
    if payload:
        expire_in = max(0, int(payload["exp"] - int(datetime.utcnow().timestamp())))
        await blacklist_jti(payload["jti"], expire_in)
    await delete_refresh_jti(user_id, device_id)
    return {"message": "Logged out successfully"}


async def logout_all(user_id: str, access_token: str) -> dict:
    payload = decode_token(access_token)
    if payload:
        expire_in = max(0, int(payload["exp"] - int(datetime.utcnow().timestamp())))
        await blacklist_jti(payload["jti"], expire_in)
    await delete_all_refresh_jtis(user_id)
    return {"message": "Logged out from all devices"}


async def change_password(data: ChangePasswordRequest, current_user: User, db: AsyncSession) -> dict:
    if not current_user.password_hash or not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    await delete_all_refresh_jtis(str(current_user.id))
    return {"message": "Password changed successfully. Please login again."}