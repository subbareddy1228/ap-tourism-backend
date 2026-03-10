
"""
services/user_service.py
Business logic for all User API operations.
Depends on: user_repo, aws_s3 (avatar), auth OTP flow (phone change).
"""

import math
from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories import user_repo
from src.schemas.user import (
    ProfileUpdate, AddressCreate, AddressUpdate,
    FamilyMemberCreate, FamilyMemberUpdate,
    SaveItemRequest, UpdatePhoneRequest, UpdateEmailRequest,
)
from src.integrations.aws_s3 import upload_avatar, delete_avatar
from src.core.redis import get_redis
import re


# ─── Helpers ──────────────────────────────────────────────────

def _profile_to_dict(user: User, profile) -> dict:
    """Merge User + UserProfile into a single flat dict for ProfileResponse."""
    base = {
        "id":                   str(user.id),
        "phone":                user.phone,
        "email":                user.email,
        "full_name":            user.full_name,
        "role":                 user.role.value if hasattr(user.role, "value") else user.role,
        "status":               user.status.value if hasattr(user.status, "value") else user.status,
        "is_phone_verified":    user.is_phone_verified,
        "is_email_verified":    user.is_email_verified,
        "created_at":           user.created_at,
        "last_login":           user.last_login,
    }
    if profile:
        base.update({
            "avatar_url":                  profile.avatar_url,
            "gender":                      profile.gender,
            "date_of_birth":               profile.date_of_birth,
            "language_pref":               profile.language_pref,
            "bio":                         profile.bio,
            "dietary_preference":          profile.dietary_preference,
            "special_needs":               profile.special_needs,
            "travel_preferences":          profile.travel_preferences,
            "emergency_contact_name":      profile.emergency_contact_name,
            "emergency_contact_phone":     profile.emergency_contact_phone,
            "emergency_contact_relation":  profile.emergency_contact_relation,
            "loyalty_points":              profile.loyalty_points,
            "total_trips":                 profile.total_trips,
            "total_spent":                 profile.total_spent,
            "is_profile_complete":         profile.is_profile_complete,
        })
    else:
        base.update({
            "loyalty_points": 0, "total_trips": 0, "total_spent": 0.0,
            "is_profile_complete": False,
        })
    return base


# ═══════════════════════════════════════════════════════════════
# PROFILE OPERATIONS
# ═══════════════════════════════════════════════════════════════

async def get_my_profile(user: User, db: AsyncSession) -> dict:
    """GET /users/me"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return _profile_to_dict(user, profile)


async def update_my_profile(user: User, data: ProfileUpdate, db: AsyncSession) -> dict:
    """PUT /users/me/profile"""
    update_data = data.model_dump(exclude_none=True)

    # Split fields: some go to User table, rest go to UserProfile
    user_fields    = {}
    profile_fields = {}

    user_table_fields = {"full_name", "email"}

    for key, val in update_data.items():
        if key in user_table_fields:
            user_fields[key] = val
        else:
            profile_fields[key] = val

    # Email uniqueness check
    if "email" in user_fields:
        existing = await user_repo.get_user_by_email(db, user_fields["email"])
        if existing and existing.id != user.id:
            raise ValueError("Email already in use by another account")

    if user_fields:
        await user_repo.update_user_fields(db, user.id, **user_fields)

    profile = await user_repo.get_or_create_profile(db, user.id)

    if profile_fields:
        updated_profile = await user_repo.update_profile_fields(db, user.id, **profile_fields)
    else:
        updated_profile = profile

    # Recheck completeness
    updated_user = await user_repo.get_user_by_id(db, user.id)
    is_complete  = await user_repo.check_profile_completeness(updated_profile, updated_user)
    if is_complete != updated_profile.is_profile_complete:
        await user_repo.update_profile_fields(db, user.id, is_profile_complete=is_complete)
        updated_profile = await user_repo.get_profile_by_user_id(db, user.id)

    return _profile_to_dict(updated_user, updated_profile)


async def upload_avatar(user: User, file_content: bytes, content_type: str, db: AsyncSession) -> dict:
    """POST /users/me/avatar — upload to S3, update avatar_url."""
    profile = await user_repo.get_or_create_profile(db, user.id)

    # Delete old avatar from S3 if exists
    if profile.avatar_url:
        old_key = profile.avatar_url.split("/")[-1]
        await delete_file_from_s3(f"avatars/{old_key}")

    s3_key = f"avatars/{user.id}/{datetime.utcnow().timestamp()}"
    url = await upload_file_to_s3(file_content, s3_key, content_type)

    await user_repo.update_profile_fields(db, user.id, avatar_url=url)
    return {"avatar_url": url}


async def delete_avatar(user: User, db: AsyncSession) -> dict:
    """DELETE /users/me/avatar"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    if profile.avatar_url:
        old_key = "/".join(profile.avatar_url.split("/")[-2:])
        await delete_file_from_s3(f"avatars/{old_key}")
        await user_repo.update_profile_fields(db, user.id, avatar_url=None)
    return {"message": "Avatar removed successfully"}


# ═══════════════════════════════════════════════════════════════
# PHONE / EMAIL CHANGE
# ═══════════════════════════════════════════════════════════════

async def change_phone(user: User, data: UpdatePhoneRequest, db: AsyncSession) -> dict:
    """POST /users/me/change-phone — verify OTP then update phone."""
    redis = await get_redis()
    otp_key = f"otp:change_phone:{data.new_phone}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp or stored_otp.decode() != data.otp:
        raise ValueError("Invalid or expired OTP")

    # Check new phone not taken
    existing = await user_repo.get_user_by_phone(db, data.new_phone)
    if existing and existing.id != user.id:
        raise ValueError("Phone number already registered")

    await user_repo.update_user_fields(db, user.id, phone=data.new_phone, is_phone_verified=True)
    await redis.delete(otp_key)
    return {"message": "Phone number updated successfully", "phone": data.new_phone}


async def verify_email(user: User, data: UpdateEmailRequest, db: AsyncSession) -> dict:
    """POST /users/me/verify-email — verify OTP then mark email verified."""
    redis = await get_redis()
    otp_key = f"otp:verify_email:{user.id}:{data.email}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp or stored_otp.decode() != data.otp:
        raise ValueError("Invalid or expired OTP")

    existing = await user_repo.get_user_by_email(db, data.email)
    if existing and existing.id != user.id:
        raise ValueError("Email already in use")

    await user_repo.update_user_fields(db, user.id, email=data.email, is_email_verified=True)
    await redis.delete(otp_key)
    return {"message": "Email verified successfully"}


# ═══════════════════════════════════════════════════════════════
# ADDRESS OPERATIONS
# ═══════════════════════════════════════════════════════════════

async def get_addresses(user: User, db: AsyncSession) -> list:
    """GET /users/me/addresses"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return await user_repo.get_addresses(db, profile.id)


async def add_address(user: User, data: AddressCreate, db: AsyncSession):
    """POST /users/me/addresses"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return await user_repo.create_address(db, profile.id, data.model_dump())


async def update_address(user: User, address_id: UUID, data: AddressUpdate, db: AsyncSession):
    """PUT /users/me/addresses/{address_id}"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    address = await user_repo.get_address_by_id(db, address_id, profile.id)
    if not address:
        raise ValueError("Address not found")
    return await user_repo.update_address(db, address_id, profile.id, data.model_dump(exclude_none=True))


async def delete_address(user: User, address_id: UUID, db: AsyncSession) -> dict:
    """DELETE /users/me/addresses/{address_id}"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    deleted  = await user_repo.delete_address(db, address_id, profile.id)
    if not deleted:
        raise ValueError("Address not found")
    return {"message": "Address deleted"}


async def set_default_address(user: User, address_id: UUID, db: AsyncSession):
    """PUT /users/me/addresses/{address_id}/default"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    address  = await user_repo.set_default_address(db, address_id, profile.id)
    if not address:
        raise ValueError("Address not found")
    return address


# ═══════════════════════════════════════════════════════════════
# FAMILY MEMBER OPERATIONS
# ═══════════════════════════════════════════════════════════════

async def get_family(user: User, db: AsyncSession) -> list:
    """GET /users/me/family"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return await user_repo.get_family_members(db, profile.id)


async def add_family_member(user: User, data: FamilyMemberCreate, db: AsyncSession):
    """POST /users/me/family"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    members = await user_repo.get_family_members(db, profile.id)
    if len(members) >= 10:
        raise ValueError("Maximum 10 family members allowed")
    return await user_repo.create_family_member(db, profile.id, data.model_dump())


async def update_family_member(user: User, member_id: UUID, data: FamilyMemberUpdate, db: AsyncSession):
    """PUT /users/me/family/{member_id}"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    member   = await user_repo.get_family_member_by_id(db, member_id, profile.id)
    if not member:
        raise ValueError("Family member not found")
    return await user_repo.update_family_member(db, member_id, profile.id, data.model_dump(exclude_none=True))


async def delete_family_member(user: User, member_id: UUID, db: AsyncSession) -> dict:
    """DELETE /users/me/family/{member_id}"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    deleted  = await user_repo.delete_family_member(db, member_id, profile.id)
    if not deleted:
        raise ValueError("Family member not found")
    return {"message": "Family member removed"}


# ═══════════════════════════════════════════════════════════════
# SAVED ITEMS (WISHLIST)
# ═══════════════════════════════════════════════════════════════

async def get_saved_items(user: User, db: AsyncSession, item_type: Optional[str], page: int, limit: int) -> dict:
    """GET /users/me/saved"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    items, total = await user_repo.get_saved_items(db, profile.id, item_type, page, limit)
    return {
        "data":  items,
        "total": total,
        "page":  page,
        "pages": math.ceil(total / limit),
        "limit": limit,
    }


async def save_item(user: User, data: SaveItemRequest, db: AsyncSession):
    """POST /users/me/saved"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return await user_repo.save_item(db, profile.id, data.item_id, data.item_type)


async def unsave_item(user: User, item_id: UUID, db: AsyncSession) -> dict:
    """DELETE /users/me/saved/{item_id}"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    deleted  = await user_repo.unsave_item(db, profile.id, item_id)
    if not deleted:
        raise ValueError("Saved item not found")
    return {"message": "Removed from saved items"}


# ═══════════════════════════════════════════════════════════════
# LOYALTY
# ═══════════════════════════════════════════════════════════════

async def get_loyalty(user: User, db: AsyncSession) -> dict:
    """GET /users/me/loyalty"""
    profile = await user_repo.get_or_create_profile(db, user.id)
    return {
        "loyalty_points": profile.loyalty_points,
        "total_trips":    profile.total_trips,
        "total_spent":    profile.total_spent,
        "tier":           user_repo.get_loyalty_tier(profile.loyalty_points),
    }


# ═══════════════════════════════════════════════════════════════
# FCM TOKEN
# ═══════════════════════════════════════════════════════════════

async def update_fcm_token(user: User, fcm_token: str, db: AsyncSession) -> dict:
    """PUT /users/me/fcm-token"""
    await user_repo.update_profile_fields(db, user.id, fcm_token=fcm_token)
    return {"message": "FCM token updated"}


# ═══════════════════════════════════════════════════════════════
# ADMIN OPERATIONS
# ═══════════════════════════════════════════════════════════════

async def admin_list_users(
    db: AsyncSession,
    page: int, limit: int,
    role: Optional[str], status: Optional[str], search: Optional[str]
) -> dict:
    """GET /users — admin only"""
    users, total = await user_repo.list_users(db, page, limit, role, status, search)
    return {
        "data":  users,
        "total": total,
        "page":  page,
        "pages": math.ceil(total / limit) if total else 0,
        "limit": limit,
    }


async def admin_get_user(user_id: UUID, db: AsyncSession) -> dict:
    """GET /users/{user_id} — admin only"""
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    profile = await user_repo.get_profile_by_user_id(db, user_id)
    return _profile_to_dict(user, profile)


async def admin_update_user(user_id: UUID, data, db: AsyncSession) -> dict:
    """PUT /users/{user_id} — admin only"""
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    update_data = data.model_dump(exclude_none=True)
    await user_repo.update_user_fields(db, user_id, **update_data)
    updated_user = await user_repo.get_user_by_id(db, user_id)
    profile      = await user_repo.get_profile_by_user_id(db, user_id)
    return _profile_to_dict(updated_user, profile)


async def admin_delete_user(user_id: UUID, db: AsyncSession) -> dict:
    """DELETE /users/{user_id} — admin only (soft delete)"""
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    await user_repo.soft_delete_user(db, user_id)
    return {"message": "User deleted successfully"}
