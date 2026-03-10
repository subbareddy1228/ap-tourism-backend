
"""
api/v1/endpoints/users.py
M2 — User APIs  |  25 endpoints  |  /api/v1/users

Self-Service (15):
  GET    /users/me                              → Get my profile
  PUT    /users/me/profile                      → Update profile
  POST   /users/me/avatar                       → Upload avatar
  DELETE /users/me/avatar                       → Remove avatar
  POST   /users/me/change-phone                 → Change phone (OTP)
  POST   /users/me/verify-email                 → Verify email (OTP)
  DELETE /users/me/account                      → Delete own account
  GET    /users/me/addresses                    → List addresses
  POST   /users/me/addresses                    → Add address
  PUT    /users/me/addresses/{id}               → Update address
  DELETE /users/me/addresses/{id}               → Delete address
  PUT    /users/me/addresses/{id}/default       → Set default address
  GET    /users/me/family                       → List family members
  POST   /users/me/family                       → Add family member
  PUT    /users/me/family/{id}                  → Update family member
  DELETE /users/me/family/{id}                  → Delete family member
  GET    /users/me/saved                        → Saved items (wishlist)
  POST   /users/me/saved                        → Save an item
  DELETE /users/me/saved/{item_id}              → Remove saved item
  GET    /users/me/loyalty                      → Loyalty points & tier
  PUT    /users/me/fcm-token                    → Update FCM push token

Admin (4):
  GET    /users                                 → List all users (admin)
  GET    /users/{user_id}                       → Get any user (admin)
  PUT    /users/{user_id}                       → Update any user (admin)
  DELETE /users/{user_id}                       → Delete any user (admin)
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_verified_user, get_admin_user
from src.models.user import User
from src.schemas.user import (
    ProfileUpdate, AddressCreate, AddressUpdate,
    FamilyMemberCreate, FamilyMemberUpdate,
    SaveItemRequest, UpdatePhoneRequest, UpdateEmailRequest,
    UpdateFCMTokenRequest, AdminUpdateUserRequest,
    ProfileResponse, AddressResponse, FamilyMemberResponse,
    SavedItemResponse, LoyaltyResponse, AdminUserListResponse,
    PaginatedResponse,
)
from src.common.responses import APIResponse
from src.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

# ── Avatar size / type guards ─────────────────────────────────
MAX_AVATAR_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — PROFILE
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/me",
    response_model=APIResponse,
    summary="Get my profile"
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full profile for the authenticated user.
    Merges **users** + **user_profiles** tables.
    Auto-creates a profile if first access.
    """
    data = await user_service.get_my_profile(current_user, db)
    return APIResponse.success(data=data)


@router.put(
    "/me/profile",
    response_model=APIResponse,
    summary="Update my profile"
)
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Partial update — only send fields you want to change.
    Updates **users** table (full_name, email) and **user_profiles** (everything else).
    Also recalculates `is_profile_complete` automatically.
    """
    try:
        data = await user_service.update_my_profile(current_user, payload, db)
        return APIResponse.success(message="Profile updated successfully", data=data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/me/avatar",
    response_model=APIResponse,
    summary="Upload profile avatar"
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a profile photo. Accepted formats: JPEG, PNG, WebP. Max size: 5 MB.
    Returns the new `avatar_url` (S3 URL).
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images allowed")

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_AVATAR_SIZE_MB}MB")

    data = await user_service.upload_avatar(current_user, content, file.content_type, db)
    return APIResponse.success(message="Avatar uploaded", data=data)


@router.delete(
    "/me/avatar",
    response_model=APIResponse,
    summary="Remove profile avatar"
)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes the avatar from S3 and clears avatar_url."""
    data = await user_service.delete_avatar(current_user, db)
    return APIResponse.success(message=data["message"])


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — PHONE / EMAIL
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/me/change-phone",
    response_model=APIResponse,
    summary="Change phone number (OTP verified)"
)
async def change_phone(
    payload: UpdatePhoneRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the phone number tied to this account.
    **Pre-requisite:** Call `/auth/send-otp` with `purpose=change_phone` for the new number.
    Then submit the new_phone + OTP here.
    """
    try:
        data = await user_service.change_phone(current_user, payload, db)
        return APIResponse.success(message=data["message"], data=data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/me/verify-email",
    response_model=APIResponse,
    summary="Verify and save email address"
)
async def verify_email(
    payload: UpdateEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email with OTP. Sets `is_email_verified=true`.
    **Pre-requisite:** Send OTP to the email first (via `/auth/send-otp` or email flow).
    """
    try:
        data = await user_service.verify_email(current_user, payload, db)
        return APIResponse.success(message=data["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/me/account",
    response_model=APIResponse,
    summary="Delete my account (soft delete)"
)
async def delete_my_account(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-deletes the authenticated user's account.
    Sets `deleted_at` and `status=deleted`. Data is retained for 30 days.
    """
    await user_service.admin_delete_user(current_user.id, db)
    return APIResponse.success(message="Account deleted successfully")


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — ADDRESSES
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/me/addresses",
    response_model=APIResponse,
    summary="List my saved addresses"
)
async def get_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addresses = await user_service.get_addresses(current_user, db)
    return APIResponse.success(data=[AddressResponse.model_validate(a).model_dump() for a in addresses])


@router.post(
    "/me/addresses",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new address"
)
async def add_address(
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a saved address. Max 10 addresses per user."""
    address = await user_service.add_address(current_user, payload, db)
    return APIResponse.success(
        message="Address added",
        data=AddressResponse.model_validate(address).model_dump()
    )


@router.put(
    "/me/addresses/{address_id}",
    response_model=APIResponse,
    summary="Update an address"
)
async def update_address(
    address_id: UUID,
    payload: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        address = await user_service.update_address(current_user, address_id, payload, db)
        return APIResponse.success(data=AddressResponse.model_validate(address).model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/me/addresses/{address_id}",
    response_model=APIResponse,
    summary="Delete an address"
)
async def delete_address(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await user_service.delete_address(current_user, address_id, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/me/addresses/{address_id}/default",
    response_model=APIResponse,
    summary="Set address as default"
)
async def set_default_address(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        address = await user_service.set_default_address(current_user, address_id, db)
        return APIResponse.success(
            message="Default address updated",
            data=AddressResponse.model_validate(address).model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — FAMILY MEMBERS
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/me/family",
    response_model=APIResponse,
    summary="List family members"
)
async def get_family(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Used during group bookings to pre-fill traveler details."""
    members = await user_service.get_family(current_user, db)
    return APIResponse.success(data=[FamilyMemberResponse.model_validate(m).model_dump() for m in members])


@router.post(
    "/me/family",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a family member"
)
async def add_family_member(
    payload: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await user_service.add_family_member(current_user, payload, db)
        return APIResponse.success(
            message="Family member added",
            data=FamilyMemberResponse.model_validate(member).model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/me/family/{member_id}",
    response_model=APIResponse,
    summary="Update a family member"
)
async def update_family_member(
    member_id: UUID,
    payload: FamilyMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await user_service.update_family_member(current_user, member_id, payload, db)
        return APIResponse.success(data=FamilyMemberResponse.model_validate(member).model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/me/family/{member_id}",
    response_model=APIResponse,
    summary="Remove a family member"
)
async def delete_family_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await user_service.delete_family_member(current_user, member_id, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — SAVED ITEMS (WISHLIST)
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/me/saved",
    response_model=APIResponse,
    summary="Get saved/wishlisted items"
)
async def get_saved_items(
    item_type: Optional[str] = Query(None, description="Filter: temple | destination | package | hotel"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await user_service.get_saved_items(current_user, db, item_type, page, limit)
    result["data"] = [SavedItemResponse.model_validate(i).model_dump() for i in result["data"]]
    return APIResponse.success(data=result)


@router.post(
    "/me/saved",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save/wishlist an item"
)
async def save_item(
    payload: SaveItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await user_service.save_item(current_user, payload, db)
        return APIResponse.success(
            message="Item saved to wishlist",
            data=SavedItemResponse.model_validate(item).model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/me/saved/{item_id}",
    response_model=APIResponse,
    summary="Remove item from wishlist"
)
async def unsave_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await user_service.unsave_item(current_user, item_id, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# SELF-SERVICE — LOYALTY & FCM
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/me/loyalty",
    response_model=APIResponse,
    summary="Get loyalty points and tier"
)
async def get_loyalty(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns loyalty points, tier (bronze/silver/gold/platinum),
    total trips, and total amount spent.
    """
    data = await user_service.get_loyalty(current_user, db)
    return APIResponse.success(data=data)


@router.put(
    "/me/fcm-token",
    response_model=APIResponse,
    summary="Update FCM push notification token"
)
async def update_fcm_token(
    payload: UpdateFCMTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Called by the mobile app on every launch to keep the FCM token fresh."""
    data = await user_service.update_fcm_token(current_user, payload.fcm_token, db)
    return APIResponse.success(message=data["message"])


# ═══════════════════════════════════════════════════════════════
# ADMIN — USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get(
    "",
    response_model=APIResponse,
    summary="[Admin] List all users"
)
async def admin_list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None, description="traveler|guide|driver|partner|admin"),
    status: Optional[str] = Query(None, description="active|suspended|deleted"),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await user_service.admin_list_users(db, page, limit, role, status, search)
    result["data"] = [AdminUserListResponse.model_validate(u).model_dump() for u in result["data"]]
    return APIResponse.success(data=result)


@router.get(
    "/{user_id}",
    response_model=APIResponse,
    summary="[Admin] Get any user's full profile"
)
async def admin_get_user(
    user_id: UUID,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await user_service.admin_get_user(user_id, db)
        return APIResponse.success(data=data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{user_id}",
    response_model=APIResponse,
    summary="[Admin] Update any user's role or status"
)
async def admin_update_user(
    user_id: UUID,
    payload: AdminUpdateUserRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await user_service.admin_update_user(user_id, payload, db)
        return APIResponse.success(message="User updated", data=data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{user_id}",
    response_model=APIResponse,
    summary="[Admin] Delete any user (soft delete)"
)
async def admin_delete_user(
    user_id: UUID,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await user_service.admin_delete_user(user_id, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
