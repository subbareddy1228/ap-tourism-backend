
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_verified_user
from src.models.user import User
from src.schemas.user import (
    FCMTokenRequest, FCMTokenRequest, UpdateProfileRequest, ProfileResponse,
    AddressRequest, AddressResponse,
    FamilyMemberRequest, FamilyMemberResponse,
    VerifyPhoneRequest,
    PreferencesRequest, PreferencesResponse,
    SessionResponse, AvatarResponse
)
from src.common.responses import APIResponse
from src.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


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

# ══════════════════ KYC ══════════════════
@router.get(
    "/me/kyc",
    response_model=APIResponse,
    summary="Get KYC status"
)
async def get_kyc_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get KYC verification status for the current user."""
    profile = await user_service.get_or_create_profile(str(current_user.id), db)
    return APIResponse.success(
        message="KYC status fetched",
        data={
            "kyc_status": profile.kyc_status,
            "user_id": str(current_user.id),
        }
    )

# ══════════════════ wallet ══════════════════
@router.get(
    "/me/wallet",
    response_model=APIResponse,
    summary="Get wallet summary from user profile"
)
async def get_wallet_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns wallet balance linked to the current user."""
    from src.services import wallet_service
    wallet = await wallet_service.get_balance(current_user, db)
    return APIResponse.success(
        message="Wallet summary fetched",
        data={
            "wallet_id": str(wallet.id),
            "balance": str(wallet.balance),
            "currency": "INR",
            "status": wallet.status,
        }
    )
# ══════════════════ bookings ══════════════════
@router.get(
    "/me/bookings",
    response_model=APIResponse,
    summary="Get current user's bookings"
)
async def get_my_bookings(
    page: int =  Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    status:  Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all bookings for the current user. Shortcut to /bookings/?user context."""
    from src.services import booking_service
    result = await booking_service.list_bookings(
        user=current_user, db=db,
        page=page, per_page=per_page, status_filter=status
    )
    return APIResponse.success(message="Bookings fetched", data=result)

# ══════════════════ reviews ══════════════════
@router.get(
    "/me/reviews",
    response_model=APIResponse,
    summary="Get reviews submitted by current user"
)
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all reviews the current user has submitted."""
    from src.services import review_service
    reviews = await review_service.get_user_reviews(str(current_user.id), db)
    return APIResponse.success(message="Reviews fetched", data=reviews)

# ══════════════════ notifications ══════════════════
@router.get(
    "/me/notifications",
    response_model=APIResponse,
    summary="Get user notifications"
)
async def get_my_notifications(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List notifications for the current user."""
    from src.services import notification_service
    result = await notification_service.get_user_notifications(
        user_id=str(current_user.id), db=db,
        page=page, per_page=per_page, unread_only=unread_only
    )
    return APIResponse.success(message="Notifications fetched", data=result)

# ══════════════════ fmc token ══════════════════
@router.put(
    "/me/fcm-token",
    response_model=APIResponse,
    summary="Register FCM device token for push notifications"
)
async def update_fcm_token(
    data:  FCMTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register or update the device FCM token.
    Called on every app launch to keep push notifications working.
    """
    result = await user_service.update_fcm_token(data.fcm_token, current_user, db)
    return APIResponse.success(message=result["message"])