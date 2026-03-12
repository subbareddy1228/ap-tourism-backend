"""
services/user_service.py
Users Module business logic — all 18 endpoint functions.
Owner: Dev 2
"""

import logging
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User
from src.models.user_profile import UserProfile, Address, FamilyMember, UserSession

from src.schemas.user import (
    UpdateProfileRequest, AddressRequest,
    FamilyMemberRequest, VerifyPhoneRequest, PreferencesRequest
)

from src.core.redis import (
    store_otp, get_otp, delete_otp,
    increment_otp_attempts, clear_otp_attempts,
    blacklist_jti, delete_all_refresh_jtis
)

from src.common.utils import generate_otp
from src.core.config import settings
from src.integrations.twilio import send_sms
from src.integrations.aws_s3 import upload_avatar, delete_avatar
from src.common.enums import UserStatus

logger = logging.getLogger(__name__)

AVATAR_MAX_SIZE = 5 * 1024 * 1024
AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"]


# ───────────────── Helpers ─────────────────

async def get_or_create_profile(user_id: str, db: AsyncSession) -> UserProfile:

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

    profile = await get_or_create_profile(str(current_user.id), db)

    return {
        "id": str(current_user.id),
        "phone": current_user.phone,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_phone_verified": current_user.is_phone_verified,
        "is_email_verified": current_user.is_email_verified,
        "date_of_birth": profile.date_of_birth,
        "gender": profile.gender,
        "language": profile.language,
        "avatar_url": profile.avatar_url,
        "kyc_status": profile.kyc_status,
        "preferences": profile.preferences or {},
    }


async def update_profile(data: UpdateProfileRequest, current_user: User, db: AsyncSession) -> dict:

    if data.full_name is not None:
        current_user.full_name = data.full_name

    profile = await get_or_create_profile(str(current_user.id), db)

    if data.date_of_birth is not None:
        profile.date_of_birth = data.date_of_birth

    if data.gender is not None:
        profile.gender = data.gender

    if data.language is not None:
        profile.language = data.language

    profile.updated_at = datetime.utcnow()

    await db.commit()

    return await get_full_profile(current_user, db)


async def upload_user_avatar(file: UploadFile, current_user: User, db: AsyncSession) -> dict:

    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type"
        )

    file_bytes = await file.read()

    if len(file_bytes) > AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 5MB)"
        )

    profile = await get_or_create_profile(str(current_user.id), db)

    if profile.avatar_url:
        await delete_avatar(profile.avatar_url)

    avatar_url = await upload_avatar(
        file_bytes,
        file.content_type,
        str(current_user.id)
    )

    profile.avatar_url = avatar_url
    profile.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "avatar_url": avatar_url,
        "message": "Avatar uploaded successfully"
    }


async def delete_account(current_user: User, db: AsyncSession) -> dict:

    current_user.status = UserStatus.DELETED
    current_user.deleted_at = datetime.utcnow()

    await db.commit()

    await delete_all_refresh_jtis(str(current_user.id))

    return {
        "message": "Account deleted. Personal data will be removed after 30 days."
    }


# ══════════════════ ADDRESSES ══════════════════

async def list_addresses(current_user: User, db: AsyncSession):

    result = await db.execute(
        select(Address).where(Address.user_id == current_user.id)
    )

    return result.scalars().all()


async def add_address(data: AddressRequest, current_user: User, db: AsyncSession):

    if data.is_default:

        existing = (
            await db.execute(
                select(Address).where(Address.user_id == current_user.id)
            )
        ).scalars().all()

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


async def update_address(address_id: str, data: AddressRequest, current_user: User, db: AsyncSession):

    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id
        )
    )

    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    address.label = data.label
    address.address_line1 = data.address_line1
    address.address_line2 = data.address_line2
    address.city = data.city
    address.state = data.state
    address.pincode = data.pincode
    address.country = data.country or "India"
    address.is_default = data.is_default or False
    address.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(address)

    return address


async def delete_address(address_id: str, current_user: User, db: AsyncSession):

    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id
        )
    )

    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    await db.delete(address)
    await db.commit()

    return {"message": "Address deleted successfully"}


# ══════════════════ FAMILY MEMBERS ══════════════════

async def list_family_members(current_user: User, db: AsyncSession):

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.user_id == current_user.id
        )
    )

    return result.scalars().all()


async def add_family_member(data: FamilyMemberRequest, current_user: User, db: AsyncSession):

    member = FamilyMember(
        user_id=current_user.id,
        name=data.name,
        relation=data.relation,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        id_proof_type=data.id_proof_type,
        id_proof_number=data.id_proof_number
    )

    db.add(member)
    await db.commit()
    await db.refresh(member)

    return member


async def update_family_member(member_id: str, data: FamilyMemberRequest, current_user: User, db: AsyncSession):

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )

    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    member.name = data.name
    member.relation = data.relation
    member.date_of_birth = data.date_of_birth
    member.gender = data.gender
    member.id_proof_type = data.id_proof_type
    member.id_proof_number = data.id_proof_number
    member.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(member)

    return member


async def delete_family_member(member_id: str, current_user: User, db: AsyncSession):

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )

    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    await db.delete(member)
    await db.commit()

    return {"message": "Family member removed successfully"}


# ══════════════════ PHONE VERIFICATION ══════════════════

async def send_phone_verification_otp(current_user: User):

    if current_user.is_phone_verified:
        raise HTTPException(
            status_code=400,
            detail="Phone is already verified"
        )

    otp = generate_otp()

    await store_otp(current_user.phone, otp, purpose="verify_phone")

    await send_sms(current_user.phone, otp)

    return {
        "message": "OTP sent to your phone",
        "expires_in": settings.OTP_EXPIRE_SECONDS
    }


async def verify_phone_otp(data: VerifyPhoneRequest, current_user: User, db: AsyncSession):

    attempts = await increment_otp_attempts(current_user.phone)

    if attempts > settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts"
        )

    stored = await get_otp(current_user.phone, purpose="verify_phone")

    if not stored:
        raise HTTPException(status_code=400, detail="OTP expired")

    if stored != data.otp:
        raise HTTPException(status_code=401, detail="Incorrect OTP")

    await delete_otp(current_user.phone, purpose="verify_phone")
    await clear_otp_attempts(current_user.phone)

    current_user.is_phone_verified = True
    await db.commit()

    return {"message": "Phone verified successfully"}