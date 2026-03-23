
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_verified_user
from src.models.user import User
from src.schemas.user import (
    UpdateProfileRequest, ProfileResponse,
    AddressRequest, AddressResponse,
    FamilyMemberRequest, FamilyMemberResponse,
    VerifyPhoneRequest,
    PreferencesRequest, PreferencesResponse,
    SessionResponse, AvatarResponse
)
from src.common.responses import APIResponse
from src.services import user_service

router = APIRouter(prefix="/user", tags=["Users"])


# ══════════════════ PROFILE ══════════════════

@router.get(
    "/me",
    response_model=APIResponse,
    summary="Get full profile"
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete profile of logged-in user.
    Includes: wallet balance, kyc status, preferences, avatar.
    """
    result = await user_service.get_full_profile(current_user, db)
    return APIResponse.success(message="Profile fetched successfully", data=result)


@router.put(
    "/me",
    response_model=APIResponse,
    summary="Update profile"
)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update basic profile information.
    Updatable fields: full_name, date_of_birth, gender, language.
    """
    result = await user_service.update_profile(data, current_user, db)
    return APIResponse.success(message="Profile updated successfully", data=result)


@router.patch(
    "/me/avatar",
    response_model=APIResponse,
    summary="Upload profile avatar"
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload profile photo to AWS S3.
    - Allowed types: jpeg, png, webp
    - Max size: 5MB
    - Old avatar is automatically deleted from S3
    """
    result = await user_service.upload_user_avatar(file, current_user, db)
    return APIResponse.success(message=result["message"], data=result)


@router.delete(
    "/me",
    response_model=APIResponse,
    summary="Delete account (soft delete)"
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete the account.
    - Sets status to DELETED, records deleted_at timestamp
    - Anonymizes personal data after 30 days
    - Logs out all devices immediately
    """
    result = await user_service.delete_account(current_user, db)
    return APIResponse.success(message=result["message"])


# ══════════════════ ADDRESSES ══════════════════

@router.get(
    "/me/addresses",
    response_model=APIResponse,
    summary="List all addresses"
)
async def list_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all saved addresses for the user."""
    addresses = await user_service.list_addresses(current_user, db)
    data = [AddressResponse.model_validate(a).model_dump() for a in addresses]
    return APIResponse.success(message="Addresses fetched", data=data)


@router.post(
    "/me/addresses",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new address"
)
async def add_address(
    data: AddressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new address.
    Labels: home | work | other
    If is_default=true, all other addresses are unset as default.
    """
    address = await user_service.add_address(data, current_user, db)
    return APIResponse.success(
        message="Address added successfully",
        data=AddressResponse.model_validate(address).model_dump()
    )


@router.put(
    "/me/addresses/{address_id}",
    response_model=APIResponse,
    summary="Update address"
)
async def update_address(
    address_id: str,
    data: AddressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing address. Verifies ownership before updating."""
    address = await user_service.update_address(address_id, data, current_user, db)
    return APIResponse.success(
        message="Address updated successfully",
        data=AddressResponse.model_validate(address).model_dump()
    )


@router.delete(
    "/me/addresses/{address_id}",
    response_model=APIResponse,
    summary="Delete address"
)
async def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an address. Verifies ownership before deleting."""
    result = await user_service.delete_address(address_id, current_user, db)
    return APIResponse.success(message=result["message"])


# ══════════════════ FAMILY MEMBERS ══════════════════

@router.get(
    "/me/family-members",
    response_model=APIResponse,
    summary="List family members"
)
async def list_family_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all family members linked to the account."""
    members = await user_service.list_family_members(current_user, db)
    data = [FamilyMemberResponse.model_validate(m).model_dump() for m in members]
    return APIResponse.success(message="Family members fetched", data=data)


@router.post(
    "/me/family-members",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add family member"
)
async def add_family_member(
    data: FamilyMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a family member.
    Relations: spouse | child | parent | sibling | other
    ID proof: aadhaar | passport | pan
    """
    member = await user_service.add_family_member(data, current_user, db)
    return APIResponse.success(
        message="Family member added",
        data=FamilyMemberResponse.model_validate(member).model_dump()
    )


@router.put(
    "/me/family-members/{member_id}",
    response_model=APIResponse,
    summary="Update family member"
)
async def update_family_member(
    member_id: str,
    data: FamilyMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update family member details."""
    member = await user_service.update_family_member(member_id, data, current_user, db)
    return APIResponse.success(
        message="Family member updated",
        data=FamilyMemberResponse.model_validate(member).model_dump()
    )


@router.delete(
    "/me/family-members/{member_id}",
    response_model=APIResponse,
    summary="Remove family member"
)
async def delete_family_member(
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a family member from the account."""
    result = await user_service.delete_family_member(member_id, current_user, db)
    return APIResponse.success(message=result["message"])


# ══════════════════ VERIFICATION ══════════════════

@router.post(
    "/me/verify-phone",
    response_model=APIResponse,
    summary="Send phone verification OTP"
)
async def verify_phone_send(
    current_user: User = Depends(get_current_user),
):
    """
    Send OTP to phone for verification.
    Use POST /auth/verify-otp to complete verification.
    """
    result = await user_service.send_phone_verification_otp(current_user)
    return APIResponse.success(message=result["message"], data=result)


@router.post(
    "/me/verify-phone/confirm",
    response_model=APIResponse,
    summary="Confirm phone verification OTP"
)
async def verify_phone_confirm(
    data: VerifyPhoneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify the OTP sent to phone and mark phone as verified."""
    result = await user_service.verify_phone_otp(data, current_user, db)
    return APIResponse.success(message=result["message"])


# ══════════════════ PREFERENCES ══════════════════

@router.get(
    "/me/preferences",
    response_model=APIResponse,
    summary="Get travel preferences"
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get travel preferences.
    Includes: dietary, language, accessibility, notification settings.
    """
    result = await user_service.get_preferences(current_user, db)
    return APIResponse.success(message="Preferences fetched", data=result)


@router.put(
    "/me/preferences",
    response_model=APIResponse,
    summary="Update preferences"
)
async def update_preferences(
    data: PreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update travel preferences.
    Stored as JSONB in user_profiles table.
    """
    result = await user_service.update_preferences(data, current_user, db)
    return APIResponse.success(message="Preferences updated", data=result)


# ══════════════════ SESSIONS ══════════════════

@router.get(
    "/me/sessions",
    response_model=APIResponse,
    summary="List active sessions"
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active login sessions.
    Shows device info, IP address, last active time.
    """
    sessions = await user_service.list_sessions(current_user, db)
    data = [SessionResponse.model_validate(s).model_dump() for s in sessions]
    return APIResponse.success(message="Sessions fetched", data=data)


@router.delete(
    "/me/sessions/{session_id}",
    response_model=APIResponse,
    summary="Revoke a session"
)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke a specific session by ID.
    Blacklists the JWT token in Redis immediately.
    """
    result = await user_service.revoke_session(session_id, current_user, db)
    return APIResponse.success(message=result["message"])
