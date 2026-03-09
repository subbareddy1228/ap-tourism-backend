# # ============================================================
# # app/routers/users.py
# # Module 2: User APIs — ALL 25 Endpoints
# # Base URL: /api/v1/users
# # Author: Garige Sai Manvitha (LEV146)
# # ============================================================




# import logging
# import uuid
# from datetime import datetime
# from typing import List

# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
# from fastapi.responses import JSONResponse
# from sqlalchemy.orm import Session

# from src.core.database import get_db
# from src.dependencies import get_current_user
# from src.models.user import User, Address, FamilyMember
# from src.schemas.user import (
#     UserUpdateSchema,
#     UserResponseSchema,
#     AddressCreateSchema,
#     AddressUpdateSchema,
#     AddressResponseSchema,
#     FamilyMemberCreateSchema,
#     FamilyMemberUpdateSchema,
#     FamilyMemberResponseSchema,
#     PreferencesSchema,
#     EmailVerifyRequestSchema,
#     PhoneVerifyOTPSchema,
#     UserSessionSchema,
# )
# from src.utils.s3 import upload_avatar, delete_s3_file
# from src.utils.cache import get_all_sessions, delete_session

# # --- Logger (never log passwords or tokens) ---
# logger = logging.getLogger(__name__)

# router = APIRouter(
#     prefix="/api/v1/users",
#     tags=["users"],
# )


# # ============================================================
# # SECTION 1: PROFILE ENDPOINTS  (4 endpoints)
# # ============================================================

# @router.get(
#     "/me",
#     response_model=UserResponseSchema,
#     summary="Get my profile",
#     description="Returns full profile of the currently logged-in user including wallet balance, KYC status and preferences."
# )
# def get_my_profile(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     GET /api/v1/users/me
#     Returns the complete profile of the logged-in user.
#     Protected: requires valid JWT token.
#     """
#     logger.info(f"GET /me called by user_id={current_user.id}")
#     return current_user


# # -------------------------------------------------------

# @router.put(
#     "/me",
#     response_model=UserResponseSchema,
#     summary="Update my profile",
#     description="Update name, language, date_of_birth, gender. Only provided fields are updated."
# )
# def update_my_profile(
#     data:         UserUpdateSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     PUT /api/v1/users/me
#     Updates only the fields provided (partial update supported).
#     """
#     logger.info(f"PUT /me called by user_id={current_user.id}")

#     update_data = data.dict(exclude_none=True)

#     if not update_data:
#         raise HTTPException(status_code=400, detail="No fields provided to update")

#     for field, value in update_data.items():
#         setattr(current_user, field, value)

#     current_user.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(current_user)

#     logger.info(f"Profile updated for user_id={current_user.id} fields={list(update_data.keys())}")
#     return current_user


# # -------------------------------------------------------

# @router.patch(
#     "/me/avatar",
#     summary="Upload profile photo",
#     description="Upload a profile photo. Accepts jpg/png/webp, max 5MB. Stored on S3, returns CloudFront URL."
# )
# async def upload_profile_avatar(
#     background_tasks: BackgroundTasks,
#     file:         UploadFile = File(...),
#     current_user: User       = Depends(get_current_user),
#     db:           Session    = Depends(get_db)
# ):
#     """
#     PATCH /api/v1/users/me/avatar
#     - Validates file type (jpg, png, webp only) and size (<= 5MB)
#     - Uploads new image to S3 under avatars/{user_id}/
#     - Deletes old avatar from S3 in background
#     - Updates avatar_url in DB
#     - Returns new CloudFront URL
#     """
#     logger.info(f"PATCH /me/avatar called by user_id={current_user.id}")

#     old_avatar_url = current_user.avatar_url

#     # Upload new avatar to S3
#     new_url = await upload_avatar(file, str(current_user.id))

#     # Update DB
#     current_user.avatar_url = new_url
#     current_user.updated_at = datetime.utcnow()
#     db.commit()

#     # Delete old avatar in background (non-blocking)
#     if old_avatar_url:
#         background_tasks.add_task(delete_s3_file, old_avatar_url)

#     logger.info(f"Avatar updated for user_id={current_user.id}")
#     return {
#         "success": True,
#         "message": "Avatar updated successfully",
#         "data": {"avatar_url": new_url}
#     }


# # -------------------------------------------------------

# @router.delete(
#     "/me",
#     summary="Delete my account",
#     description="Soft-deletes the account by setting deleted_at timestamp. Personal data anonymized after 30 days."
# )
# def delete_my_account(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     DELETE /api/v1/users/me
#     SOFT DELETE — never hard deletes from DB.
#     - Sets deleted_at = now
#     - Anonymizes phone and email immediately
#     - Deactivates account
#     Full data anonymization runs as a scheduled job after 30 days.
#     """
#     logger.info(f"DELETE /me called by user_id={current_user.id}")

#     current_user.deleted_at  = datetime.utcnow()
#     current_user.is_active   = False
#     current_user.phone       = f"DELETED_{current_user.id}"  # Prevent phone reuse
#     current_user.email       = None
#     current_user.full_name   = "Deleted User"
#     current_user.avatar_url  = None
#     current_user.updated_at  = datetime.utcnow()

#     db.commit()

#     logger.info(f"Account soft-deleted for user_id={current_user.id}")
#     return {
#         "success": True,
#         "message": "Your account has been deleted. Data will be fully anonymized within 30 days."
#     }


# # ============================================================
# # SECTION 2: ADDRESS ENDPOINTS  (4 endpoints)
# # ============================================================

# @router.get(
#     "/me/addresses",
#     response_model=List[AddressResponseSchema],
#     summary="Get all my addresses",
# )
# def get_addresses(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     GET /api/v1/users/me/addresses
#     Returns all saved addresses belonging to the logged-in user.
#     """
#     addresses = (
#         db.query(Address)
#         .filter(Address.user_id == current_user.id)
#         .order_by(Address.created_at.asc())
#         .all()
#     )
#     return addresses


# # -------------------------------------------------------

# @router.post(
#     "/me/addresses",
#     response_model=AddressResponseSchema,
#     status_code=201,
#     summary="Add a new address",
# )
# def add_address(
#     data:         AddressCreateSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     POST /api/v1/users/me/addresses
#     Creates a new address for the logged-in user.
#     """
#     address = Address(
#         user_id=current_user.id,
#         **data.dict()
#     )
#     db.add(address)
#     db.commit()
#     db.refresh(address)

#     logger.info(f"Address added for user_id={current_user.id} address_id={address.id}")
#     return address


# # -------------------------------------------------------

# @router.put(
#     "/me/addresses/{address_id}",
#     response_model=AddressResponseSchema,
#     summary="Update an address",
# )
# def update_address(
#     address_id:   uuid.UUID,
#     data:         AddressUpdateSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     PUT /api/v1/users/me/addresses/{address_id}
#     Updates an address. Verifies ownership — user can only edit their own addresses.
#     Raises 404 if address not found or doesn't belong to this user.
#     """
#     address = (
#         db.query(Address)
#         .filter(Address.id == address_id, Address.user_id == current_user.id)
#         .first()
#     )

#     if not address:
#         raise HTTPException(status_code=404, detail="Address not found")

#     update_data = data.dict(exclude_none=True)
#     if not update_data:
#         raise HTTPException(status_code=400, detail="No fields provided to update")

#     for field, value in update_data.items():
#         setattr(address, field, value)

#     address.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(address)

#     return address


# # -------------------------------------------------------

# @router.delete(
#     "/me/addresses/{address_id}",
#     summary="Delete an address",
# )
# def delete_address(
#     address_id:   uuid.UUID,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     DELETE /api/v1/users/me/addresses/{address_id}
#     Permanently deletes an address. Verifies ownership before delete.
#     Raises 404 if address not found or doesn't belong to this user.
#     """
#     address = (
#         db.query(Address)
#         .filter(Address.id == address_id, Address.user_id == current_user.id)
#         .first()
#     )

#     if not address:
#         raise HTTPException(status_code=404, detail="Address not found")

#     db.delete(address)
#     db.commit()

#     logger.info(f"Address deleted: address_id={address_id} by user_id={current_user.id}")
#     return {"success": True, "message": "Address deleted successfully"}


# # ============================================================
# # SECTION 3: FAMILY MEMBERS ENDPOINTS  (4 endpoints)
# # ============================================================

# @router.get(
#     "/me/family-members",
#     response_model=List[FamilyMemberResponseSchema],
#     summary="Get all family members",
# )
# def get_family_members(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     GET /api/v1/users/me/family-members
#     Returns all family members linked to the logged-in user's account.
#     Used for group bookings and darshan slot registration.
#     """
#     members = (
#         db.query(FamilyMember)
#         .filter(FamilyMember.user_id == current_user.id)
#         .order_by(FamilyMember.created_at.asc())
#         .all()
#     )
#     return members


# # -------------------------------------------------------

# @router.post(
#     "/me/family-members",
#     response_model=FamilyMemberResponseSchema,
#     status_code=201,
#     summary="Add a family member",
# )
# def add_family_member(
#     data:         FamilyMemberCreateSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     POST /api/v1/users/me/family-members
#     Adds a family member to the user's account.
#     Family members can be included in darshan bookings and package bookings.
#     """
#     member = FamilyMember(
#         user_id=current_user.id,
#         **data.dict()
#     )
#     db.add(member)
#     db.commit()
#     db.refresh(member)

#     logger.info(f"Family member added: member_id={member.id} by user_id={current_user.id}")
#     return member


# # -------------------------------------------------------

# @router.put(
#     "/me/family-members/{member_id}",
#     response_model=FamilyMemberResponseSchema,
#     summary="Update a family member",
# )
# def update_family_member(
#     member_id:    uuid.UUID,
#     data:         FamilyMemberUpdateSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     PUT /api/v1/users/me/family-members/{member_id}
#     Updates family member details. Verifies ownership.
#     Raises 404 if not found or doesn't belong to this user.
#     """
#     member = (
#         db.query(FamilyMember)
#         .filter(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
#         .first()
#     )

#     if not member:
#         raise HTTPException(status_code=404, detail="Family member not found")

#     update_data = data.dict(exclude_none=True)
#     if not update_data:
#         raise HTTPException(status_code=400, detail="No fields provided to update")

#     for field, value in update_data.items():
#         setattr(member, field, value)

#     member.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(member)

#     return member


# # -------------------------------------------------------

# @router.delete(
#     "/me/family-members/{member_id}",
#     summary="Remove a family member",
# )
# def delete_family_member(
#     member_id:    uuid.UUID,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     DELETE /api/v1/users/me/family-members/{member_id}
#     Removes a family member from the account. Verifies ownership.
#     Raises 404 if not found or doesn't belong to this user.
#     """
#     member = (
#         db.query(FamilyMember)
#         .filter(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
#         .first()
#     )

#     if not member:
#         raise HTTPException(status_code=404, detail="Family member not found")

#     db.delete(member)
#     db.commit()

#     logger.info(f"Family member deleted: member_id={member_id} by user_id={current_user.id}")
#     return {"success": True, "message": "Family member removed successfully"}


# # ============================================================
# # SECTION 4: VERIFICATION ENDPOINTS  (2 endpoints)
# # ============================================================

# @router.post(
#     "/me/verify-email",
#     summary="Send email verification link",
#     description="Sends a verification link to the user's email address."
# )
# def verify_email(
#     data:         EmailVerifyRequestSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     POST /api/v1/users/me/verify-email
#     Step 1: User provides their email → system sends verification link.
#     The link contains a signed JWT token that expires in 24 hours.
#     When user clicks the link: call POST /api/v1/users/me/verify-email/confirm
#     (that endpoint is handled by Auth team LEV148)

#     Here we:
#     - Save the email to the user's record
#     - Mark email_verified = False (until they click the link)
#     - Trigger an email (stubbed here — real email via SES/SendGrid)
#     """
#     # Check if email is already used by someone else
#     existing = db.query(User).filter(
#         User.email == str(data.email),
#         User.id    != current_user.id
#     ).first()

#     if existing:
#         raise HTTPException(
#             status_code=409,
#             detail="This email is already registered to another account"
#         )

#     current_user.email          = str(data.email)
#     current_user.email_verified = False
#     current_user.updated_at     = datetime.utcnow()
#     db.commit()

#     # TODO: Send email via AWS SES or SendGrid
#     # send_verification_email(email=data.email, user_id=str(current_user.id))

#     logger.info(f"Email verification requested by user_id={current_user.id} email=***")
#     return {
#         "success": True,
#         "message": f"Verification link sent to your email. Link expires in 24 hours."
#     }


# # -------------------------------------------------------

# @router.post(
#     "/me/verify-phone",
#     summary="Send phone OTP for verification",
#     description="Sends OTP to the user's registered phone number for verification."
# )
# def verify_phone_send_otp(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     POST /api/v1/users/me/verify-phone
#     Step 1: Sends OTP to the user's registered phone number.
#     OTP is stored in Redis with key otp:verify:{user_id} and TTL = 5 minutes.
#     Rate limit: max 3 OTP requests per 10 minutes per user.

#     Step 2 (confirm OTP) is handled by Auth team endpoint.
#     When OTP is confirmed: phone_verified is set to True.
#     """
#     from src.utils.cache import get_cache, set_cache

#     if current_user.phone_verified:
#         return {
#             "success": True,
#             "message": "Your phone number is already verified."
#         }

#     # Rate limiting check
#     rate_key    = f"otp_rate:{current_user.id}"
#     otp_count   = get_cache(rate_key) or 0

#     if int(otp_count) >= 3:
#         raise HTTPException(
#             status_code=429,
#             detail="Too many OTP requests. Please wait 10 minutes before trying again."
#         )

#     # Generate OTP (6-digit)
#     import random
#     otp = str(random.randint(100000, 999999))

#     # Store OTP in Redis — expires in 5 minutes
#     otp_key = f"otp:verify:{current_user.id}"
#     set_cache(otp_key, otp, ttl=300)

#     # Update rate limiter — expires in 10 minutes
#     set_cache(rate_key, int(otp_count) + 1, ttl=600)

#     # TODO: Send OTP via Twilio SMS
#     # send_sms(phone=current_user.phone, message=f"Your AP Tourism OTP is {otp}. Valid for 5 minutes.")

#     logger.info(f"Phone verification OTP sent to user_id={current_user.id}")

#     return {
#         "success": True,
#         "message": f"OTP sent to your registered phone number ending in ...{current_user.phone[-4:]}. Valid for 5 minutes."
#     }


# # ============================================================
# # SECTION 5: PREFERENCES ENDPOINTS  (2 endpoints)
# # ============================================================

# @router.get(
#     "/me/preferences",
#     response_model=PreferencesSchema,
#     summary="Get travel preferences",
# )
# def get_preferences(
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     GET /api/v1/users/me/preferences
#     Returns user's travel preferences stored as JSONB.
#     Includes: dietary, language, accessibility_needs, notification settings.
#     """
#     prefs = current_user.preferences or {}
#     return prefs


# # -------------------------------------------------------

# @router.put(
#     "/me/preferences",
#     response_model=PreferencesSchema,
#     summary="Update travel preferences",
# )
# def update_preferences(
#     data:         PreferencesSchema,
#     current_user: User    = Depends(get_current_user),
#     db:           Session = Depends(get_db)
# ):
#     """
#     PUT /api/v1/users/me/preferences
#     Updates travel preferences stored as JSONB in users.preferences column.
#     Merges with existing preferences — only provided fields are updated.
#     """
#     existing_prefs = current_user.preferences or {}
#     new_prefs      = data.dict(exclude_none=True)

#     # Merge: keep existing values for fields not in new_prefs
#     merged_prefs = {**existing_prefs, **new_prefs}

#     current_user.preferences = merged_prefs
#     current_user.updated_at  = datetime.utcnow()

#     db.commit()
#     db.refresh(current_user)

#     logger.info(f"Preferences updated for user_id={current_user.id}")
#     return current_user.preferences


# # ============================================================
# # SECTION 6: SESSIONS ENDPOINTS  (2 endpoints)
# # ============================================================

# @router.get(
#     "/me/sessions",
#     summary="Get all active login sessions",
#     description="Returns all active login sessions with device info, IP address, and last active time."
# )
# def get_sessions(
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     GET /api/v1/users/me/sessions
#     Retrieves all active sessions from Redis.
#     Each session has: session_id, device_info, ip_address, last_active, created_at.

#     Sessions are stored in Redis as:
#       Key: session:{user_id}:{session_id}
#       Value: { device_info, ip_address, last_active, created_at }
#     """
#     sessions = get_all_sessions(str(current_user.id))

#     logger.info(f"Sessions listed for user_id={current_user.id} count={len(sessions)}")
#     return {
#         "success": True,
#         "data": {
#             "sessions": sessions,
#             "total": len(sessions)
#         }
#     }


# # -------------------------------------------------------

# @router.delete(
#     "/me/sessions/{session_id}",
#     summary="Revoke a specific session",
#     description="Logs out a specific device/session by blacklisting its token in Redis."
# )
# def revoke_session(
#     session_id:   str,
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     DELETE /api/v1/users/me/sessions/{session_id}
#     Revokes (logs out) a specific session.
#     - Deletes session data from Redis
#     - The JWT token for that session will fail on next request
#     Used when user sees an unrecognized device in their sessions list.
#     """
#     # Check the session exists and belongs to this user
#     from src.utils.cache import get_cache
#     session_key  = f"session:{current_user.id}:{session_id}"
#     session_data = get_cache(session_key)

#     if not session_data:
#         raise HTTPException(status_code=404, detail="Session not found")

#     delete_session(str(current_user.id), session_id)

#     logger.info(f"Session revoked: session_id={session_id} by user_id={current_user.id}")
#     return {"success": True, "message": "Session revoked. That device has been logged out."}




"""
src/api/v1/endpoints/users.py
Module 2 — User APIs /api/v1/user
Author: LEV146
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid

from src.core.database import get_db  
from src.models.user import User, Address, FamilyMember, Gender, Language, AddressLabel, Relation, IDProofType
from src.api.deps.auth import get_current_user, get_verified_user

router = APIRouter(prefix="/user", tags=["User"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    language: Optional[Language] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[Gender] = None

class AddressRequest(BaseModel):
    label: AddressLabel = AddressLabel.HOME
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str

class FamilyMemberRequest(BaseModel):
    name: str
    relation: Relation
    date_of_birth: Optional[datetime] = None
    gender: Optional[Gender] = None
    id_proof_type: Optional[IDProofType] = None
    id_proof_number: Optional[str] = None

class PreferencesRequest(BaseModel):
    dietary: Optional[str] = None
    language: Optional[str] = None
    accessibility_needs: Optional[str] = None
    notification_settings: Optional[dict] = None


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """GET /me — Get full profile of logged-in user."""
    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "phone": current_user.phone,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "gender": current_user.gender,
            "date_of_birth": current_user.date_of_birth,
            "language": current_user.language,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
            "phone_verified": current_user.phone_verified,
            "email_verified": current_user.email_verified,
            "kyc_status": current_user.kyc_status,
            "wallet_balance": current_user.wallet_balance,
            "preferences": current_user.preferences,
            "created_at": current_user.created_at,
        }
    }


@router.put("/me")
def update_my_profile(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PUT /me — Update name, language, date_of_birth, gender."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.language is not None:
        current_user.language = body.language
    if body.date_of_birth is not None:
        current_user.date_of_birth = body.date_of_birth
    if body.gender is not None:
        current_user.gender = body.gender
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return {"success": True, "message": "Profile updated successfully"}


@router.patch("/me/avatar")
def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """PATCH /me/avatar — Upload profile photo (jpg/png, max 5MB)."""
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only jpg/png images are allowed")

    # TODO: Upload to S3 and get CloudFront URL
    # For now return a placeholder
    avatar_url = f"https://cdn.aptourism.com/avatars/{current_user.id}/{file.filename}"
    current_user.avatar_url = avatar_url
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "avatar_url": avatar_url}


@router.delete("/me")
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DELETE /me — Soft delete account."""
    current_user.deleted_at = datetime.utcnow()
    current_user.is_active = False
    db.commit()
    return {"success": True, "message": "Account deleted. Data will be anonymized after 30 days."}


# ─── Addresses ────────────────────────────────────────────────────────────────

@router.get("/me/addresses")
def get_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /me/addresses — List all saved addresses."""
    addresses = db.query(Address).filter(Address.user_id == current_user.id).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(a.id),
                "label": a.label,
                "address_line1": a.address_line1,
                "address_line2": a.address_line2,
                "city": a.city,
                "state": a.state,
                "pincode": a.pincode,
            }
            for a in addresses
        ],
    }


@router.post("/me/addresses", status_code=status.HTTP_201_CREATED)
def add_address(
    body: AddressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """POST /me/addresses — Add new address."""
    address = Address(
        user_id=current_user.id,
        label=body.label,
        address_line1=body.address_line1,
        address_line2=body.address_line2,
        city=body.city,
        state=body.state,
        pincode=body.pincode,
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return {"success": True, "message": "Address added", "id": str(address.id)}


@router.put("/me/addresses/{address_id}")
def update_address(
    address_id: str,
    body: AddressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PUT /me/addresses/{id} — Update address by ID."""
    address = db.query(Address).filter(
        and_(Address.id == address_id, Address.user_id == current_user.id)
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    address.label = body.label
    address.address_line1 = body.address_line1
    address.address_line2 = body.address_line2
    address.city = body.city
    address.state = body.state
    address.pincode = body.pincode
    address.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Address updated"}


@router.delete("/me/addresses/{address_id}")
def delete_address(
    address_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DELETE /me/addresses/{id} — Delete address by ID."""
    address = db.query(Address).filter(
        and_(Address.id == address_id, Address.user_id == current_user.id)
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(address)
    db.commit()
    return {"success": True, "message": "Address deleted"}


# ─── Family Members ───────────────────────────────────────────────────────────

@router.get("/me/family-members")
def get_family_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /me/family-members — List all family members."""
    members = db.query(FamilyMember).filter(FamilyMember.user_id == current_user.id).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(m.id),
                "name": m.name,
                "relation": m.relation,
                "date_of_birth": m.date_of_birth,
                "gender": m.gender,
                "id_proof_type": m.id_proof_type,
                "id_proof_number": m.id_proof_number,
            }
            for m in members
        ],
    }


@router.post("/me/family-members", status_code=status.HTTP_201_CREATED)
def add_family_member(
    body: FamilyMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """POST /me/family-members — Add family member."""
    member = FamilyMember(
        user_id=current_user.id,
        name=body.name,
        relation=body.relation,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        id_proof_type=body.id_proof_type,
        id_proof_number=body.id_proof_number,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"success": True, "message": "Family member added", "id": str(member.id)}


@router.put("/me/family-members/{member_id}")
def update_family_member(
    member_id: str,
    body: FamilyMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PUT /me/family-members/{id} — Update family member."""
    member = db.query(FamilyMember).filter(
        and_(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    member.name = body.name
    member.relation = body.relation
    member.date_of_birth = body.date_of_birth
    member.gender = body.gender
    member.id_proof_type = body.id_proof_type
    member.id_proof_number = body.id_proof_number
    member.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Family member updated"}


@router.delete("/me/family-members/{member_id}")
def delete_family_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DELETE /me/family-members/{id} — Remove family member."""
    member = db.query(FamilyMember).filter(
        and_(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    db.delete(member)
    db.commit()
    return {"success": True, "message": "Family member removed"}


# ─── Preferences ──────────────────────────────────────────────────────────────

@router.get("/me/preferences")
def get_preferences(current_user: User = Depends(get_current_user)):
    """GET /me/preferences — Get travel preferences."""
    return {"success": True, "data": current_user.preferences or {}}


@router.put("/me/preferences")
def update_preferences(
    body: PreferencesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PUT /me/preferences — Update preferences (stored as JSONB)."""
    current_user.preferences = body.dict(exclude_none=True)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Preferences updated"}


# ─── Verification ─────────────────────────────────────────────────────────────

@router.post("/me/verify-email")
def verify_email(current_user: User = Depends(get_current_user)):
    """POST /me/verify-email — Send verification link to email."""
    if not current_user.email:
        raise HTTPException(status_code=400, detail="No email address on file")
    if current_user.email_verified:
        return {"success": True, "message": "Email already verified"}
    # TODO: Send email via SendGrid
    return {"success": True, "message": f"Verification link sent to {current_user.email}"}


@router.post("/me/verify-phone")
def verify_phone(current_user: User = Depends(get_current_user)):
    """POST /me/verify-phone — Send OTP to phone."""
    if current_user.phone_verified:
        return {"success": True, "message": "Phone already verified"}
    # TODO: Send OTP via Twilio/MSG91
    return {"success": True, "message": f"OTP sent to {current_user.phone}"}
