"""
services/user_service.py
Users Module business logic — all 18 endpoint functions.
Owner: Dev 2

Uses from Auth Module (Dev 1):
- src.models.user.User
- src.core.redis (blacklist_jti, delete_refresh_jti)
- src.core.security (decode_token)
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.models.user import User
from src.models.user_profile import UserProfile, Address, FamilyMember, UserSession
from src.schemas.user import (
    UpdateProfileRequest, AddressRequest,
    FamilyMemberRequest, VerifyPhoneRequest, PreferencesRequest
)
from src.core.redis import (
    store_otp, get_otp, delete_otp,
    increment_otp_attempts, clear_otp_attempts,
    blacklist_jti, delete_refresh_jti, delete_all_refresh_jtis
)
from src.core.security import decode_token
from src.core.config import settings
from src.integrations.twilio import send_sms
from src.integrations.aws_s3 import upload_avatar, delete_avatar
import random
import string

logger = logging.getLogger(__name__)

AVATAR_MAX_SIZE = 5 * 1024 * 1024   # 5MB
AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"]


# ── Helper ───────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def get_or_create_profile(user_id: str, db: AsyncSession) -> UserProfile:
    """Get user profile or create empty one if not exists."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user_id, preferences={})
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


# ══════════════════ PROFILE ══════════════════

async def get_full_profile(current_user: User, db: AsyncSession) -> dict:
    """GET /me — full profile with preferences, kyc, avatar."""

    logger.info("Get profile user_id=%s", current_user.id)

    profile = await get_or_create_profile(str(current_user.id), db)

    return {
        "id":                str(current_user.id),
        "phone":             current_user.phone,
        "email":             current_user.email,
        "full_name":         current_user.full_name,
        "role":              current_user.role.value if hasattr(current_user.role, "value") else current_user.role,
        "is_phone_verified": current_user.is_phone_verified,
        "is_email_verified": current_user.is_email_verified,
        "date_of_birth":     profile.date_of_birth,
        "gender":            profile.gender,
        "language":          profile.language,
        "avatar_url":        profile.avatar_url,
        "kyc_status":        profile.kyc_status,
        "preferences":       profile.preferences or {},
    }


async def update_profile(
    data: UpdateProfileRequest,
    current_user: User,
    db: AsyncSession
) -> dict:
    """PUT /me — update name, DOB, gender, language."""

    logger.info("Update profile user_id=%s", current_user.id)

    # Update User table fields
    if data.full_name is not None:
        current_user.full_name = data.full_name

    # Update UserProfile fields
    profile = await get_or_create_profile(str(current_user.id), db)

    if data.date_of_birth is not None:
        profile.date_of_birth = data.date_of_birth
    if data.gender is not None:
        profile.gender = data.gender
    if data.language is not None:
        profile.language = data.language

    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    await db.refresh(profile)

    logger.info("Profile updated user_id=%s", current_user.id)
    return await get_full_profile(current_user, db)


async def upload_user_avatar(
    file: UploadFile,
    current_user: User,
    db: AsyncSession
) -> dict:
    """PATCH /me/avatar — upload avatar to S3."""

    logger.info("Avatar upload user_id=%s filename=%s", current_user.id, file.filename)

    # Validate file type
    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: jpeg, png, webp"
        )

    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB"
        )

    profile = await get_or_create_profile(str(current_user.id), db)

    # Delete old avatar from S3 if exists
    if profile.avatar_url:
        await delete_avatar(profile.avatar_url)

    # Upload new avatar
    avatar_url = await upload_avatar(file_bytes, file.content_type, str(current_user.id))

    profile.avatar_url = avatar_url
    profile.updated_at = datetime.utcnow()
    await db.commit()

    logger.info("Avatar uploaded user_id=%s url=%s", current_user.id, avatar_url)
    return {"avatar_url": avatar_url, "message": "Avatar uploaded successfully"}


async def delete_account(current_user: User, db: AsyncSession) -> dict:
    """DELETE /me — soft delete account."""

    logger.info("Account deletion request user_id=%s", current_user.id)

    from src.common.responses import UserStatus
    current_user.status = UserStatus.DELETED
    current_user.deleted_at = datetime.utcnow()

    await db.commit()

    # Logout all devices
    await delete_all_refresh_jtis(str(current_user.id))

    logger.info("Account deleted user_id=%s", current_user.id)
    return {"message": "Account deleted. Personal data will be removed after 30 days."}


# ══════════════════ ADDRESSES ══════════════════

async def list_addresses(current_user: User, db: AsyncSession) -> list:
    """GET /me/addresses"""

    result = await db.execute(
        select(Address).where(Address.user_id == current_user.id)
    )
    return result.scalars().all()


async def add_address(
    data: AddressRequest,
    current_user: User,
    db: AsyncSession
) -> Address:
    """POST /me/addresses"""

    logger.info("Add address user_id=%s label=%s", current_user.id, data.label)

    # If is_default, unset all others
    if data.is_default:
        await db.execute(
            select(Address).where(Address.user_id == current_user.id)
        )
        existing = (await db.execute(
            select(Address).where(Address.user_id == current_user.id)
        )).scalars().all()
        for addr in existing:
            addr.is_default = False

    address = Address(
        user_id=current_user.id,
        label=data.label,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        country=data.country or "India",
        is_default=data.is_default or False,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


async def update_address(
    address_id: str,
    data: AddressRequest,
    current_user: User,
    db: AsyncSession
) -> Address:
    """PUT /me/addresses/{id}"""

    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    # If setting as default, unset others
    if data.is_default:
        existing = (await db.execute(
            select(Address).where(Address.user_id == current_user.id)
        )).scalars().all()
        for addr in existing:
            addr.is_default = False

    address.label         = data.label
    address.address_line1 = data.address_line1
    address.address_line2 = data.address_line2
    address.city          = data.city
    address.state         = data.state
    address.pincode       = data.pincode
    address.country       = data.country or "India"
    address.is_default    = data.is_default or False
    address.updated_at    = datetime.utcnow()

    await db.commit()
    await db.refresh(address)
    return address


async def delete_address(
    address_id: str,
    current_user: User,
    db: AsyncSession
) -> dict:
    """DELETE /me/addresses/{id}"""

    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    await db.delete(address)
    await db.commit()

    logger.info("Address deleted id=%s user_id=%s", address_id, current_user.id)
    return {"message": "Address deleted successfully"}


# ══════════════════ FAMILY MEMBERS ══════════════════

async def list_family_members(current_user: User, db: AsyncSession) -> list:
    """GET /me/family-members"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    return result.scalars().all()


async def add_family_member(
    data: FamilyMemberRequest,
    current_user: User,
    db: AsyncSession
) -> FamilyMember:
    """POST /me/family-members"""

    member = FamilyMember(
        user_id=current_user.id,
        name=data.name,
        relation=data.relation,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        id_proof_type=data.id_proof_type,
        id_proof_number=data.id_proof_number,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    logger.info("Family member added user_id=%s name=%s", current_user.id, data.name)
    return member


async def update_family_member(
    member_id: str,
    data: FamilyMemberRequest,
    current_user: User,
    db: AsyncSession
) -> FamilyMember:
    """PUT /me/family-members/{id}"""

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family member not found")

    member.name            = data.name
    member.relation        = data.relation
    member.date_of_birth   = data.date_of_birth
    member.gender          = data.gender
    member.id_proof_type   = data.id_proof_type
    member.id_proof_number = data.id_proof_number
    member.updated_at      = datetime.utcnow()

    await db.commit()
    await db.refresh(member)
    return member


async def delete_family_member(
    member_id: str,
    current_user: User,
    db: AsyncSession
) -> dict:
    """DELETE /me/family-members/{id}"""

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family member not found")

    await db.delete(member)
    await db.commit()

    logger.info("Family member deleted id=%s user_id=%s", member_id, current_user.id)
    return {"message": "Family member removed successfully"}


# ══════════════════ VERIFICATION ══════════════════

async def send_phone_verification_otp(current_user: User) -> dict:
    """POST /me/verify-phone — Step 1: send OTP"""

    if current_user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone is already verified"
        )

    otp = generate_otp()
    await store_otp(current_user.phone, otp, purpose="verify_phone")

    # Send SMS
    from src.integrations.twilio import send_sms
    await send_sms(current_user.phone, otp)

    logger.info("Phone verification OTP sent user_id=%s", current_user.id)
    return {
        "message": "OTP sent to your phone",
        "phone": current_user.phone,
        "expires_in": settings.OTP_EXPIRE_SECONDS
    }


async def verify_phone_otp(
    data: VerifyPhoneRequest,
    current_user: User,
    db: AsyncSession
) -> dict:
    """POST /me/verify-phone — Step 2: verify OTP"""

    attempts = await increment_otp_attempts(current_user.phone)
    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new OTP."
        )

    stored_otp = await get_otp(current_user.phone, purpose="verify_phone")
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

    await delete_otp(current_user.phone, purpose="verify_phone")
    await clear_otp_attempts(current_user.phone)

    current_user.is_phone_verified = True
    await db.commit()

    logger.info("Phone verified user_id=%s", current_user.id)
    return {"message": "Phone verified successfully"}


# ══════════════════ PREFERENCES ══════════════════

async def get_preferences(current_user: User, db: AsyncSession) -> dict:
    """GET /me/preferences"""

    profile = await get_or_create_profile(str(current_user.id), db)
    prefs = profile.preferences or {}
    return {
        "dietary":       prefs.get("dietary"),
        "language":      prefs.get("language", profile.language),
        "accessibility": prefs.get("accessibility"),
        "notifications": prefs.get("notifications", {"email": True, "sms": True, "push": True}),
    }


async def update_preferences(
    data: PreferencesRequest,
    current_user: User,
    db: AsyncSession
) -> dict:
    """PUT /me/preferences"""

    profile = await get_or_create_profile(str(current_user.id), db)
    prefs = dict(profile.preferences or {})

    if data.dietary is not None:
        prefs["dietary"] = data.dietary
    if data.language is not None:
        prefs["language"] = data.language
        profile.language = data.language
    if data.accessibility is not None:
        prefs["accessibility"] = data.accessibility
    if data.notifications is not None:
        prefs["notifications"] = data.notifications.model_dump()

    profile.preferences = prefs
    profile.updated_at = datetime.utcnow()
    await db.commit()

    logger.info("Preferences updated user_id=%s", current_user.id)
    return prefs


# ══════════════════ SESSIONS ══════════════════

async def list_sessions(current_user: User, db: AsyncSession) -> list:
    """GET /me/sessions — list all active sessions from PostgreSQL"""

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).order_by(UserSession.last_active.desc())
    )
    return result.scalars().all()


async def revoke_session(
    session_id: str,
    current_user: User,
    db: AsyncSession
) -> dict:
    """DELETE /me/sessions/{id} — revoke specific session"""

    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Blacklist the JTI in Redis (from Auth module)
    await blacklist_jti(session.jti, 60 * 60 * 24 * 7)  # 7 days

    # Mark as inactive in DB
    session.is_active = False
    await db.commit()

    logger.info("Session revoked session_id=%s user_id=%s", session_id, current_user.id)
    return {"message": "Session revoked successfully"}
