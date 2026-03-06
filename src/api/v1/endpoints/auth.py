"""
api/v1/endpoints/auth.py
All 12 Authentication API endpoints.

Routes:
  POST /auth/register           → Register new user
  POST /auth/send-otp           → Send OTP
  POST /auth/verify-otp         → Verify OTP → get JWT
  POST /auth/resend-otp         → Resend OTP (60s cooldown)
  POST /auth/login              → Login with password
  POST /auth/login/otp          → Passwordless OTP login
  POST /auth/refresh-token      → Refresh access token
  POST /auth/logout             → Logout current device
  POST /auth/logout-all         → Logout all devices
  POST /auth/forgot-password    → Send reset OTP
  POST /auth/reset-password     → Reset password with OTP
  POST /auth/change-password    → Change password (auth required)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_verified_user
from src.models.user import User
from src.schemas.auth import (
    RegisterRequest, SendOTPRequest, VerifyOTPRequest,
    ResendOTPRequest, LoginRequest, OTPLoginRequest,
    RefreshTokenRequest, ForgotPasswordRequest,
    ResetPasswordRequest, ChangePasswordRequest,
    TokenResponse, OTPSentResponse, UserResponse
)
from src.common.responses import APIResponse
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── 1. Register ───────────────────────────────────────────────
@router.post(
    "/register",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.
    - Validates phone & email uniqueness
    - Creates unverified user
    - Sends OTP to phone number

    **Next step:** Call `/auth/verify-otp` with the OTP received.
    """
    try:
        result = await auth_service.register_user(data, db)
        return APIResponse.success(
            message="Registration successful. OTP sent to your phone.",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 2. Send OTP ───────────────────────────────────────────────
@router.post(
    "/send-otp",
    response_model=APIResponse,
    summary="Send OTP to phone"
)
async def send_otp(data: SendOTPRequest):
    """
    Send a 6-digit OTP to the given phone number.

    **purpose values:**
    - `register` — for new user registration
    - `login` — for passwordless login
    - `forgot_password` — for password reset
    """
    try:
        result = await auth_service.send_otp(data.phone, data.purpose)
        return APIResponse.success(message="OTP sent successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 3. Verify OTP ─────────────────────────────────────────────
@router.post(
    "/verify-otp",
    response_model=APIResponse,
    summary="Verify OTP and get JWT tokens"
)
async def verify_otp(
    data: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify the OTP sent to the user's phone.
    - Marks phone as verified
    - Returns access_token + refresh_token
    """
    try:
        result = await auth_service.verify_otp_and_login(data, db)
        return APIResponse.success(
            message="Phone verified successfully",
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type":    "bearer",
                "user": UserResponse.model_validate(result["user"]).model_dump()
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 4. Resend OTP ─────────────────────────────────────────────
@router.post(
    "/resend-otp",
    response_model=APIResponse,
    summary="Resend OTP (60s cooldown)"
)
async def resend_otp(data: ResendOTPRequest):
    """
    Resend OTP to the phone number.
    Enforces a 60-second cooldown to prevent spam.
    """
    try:
        result = await auth_service.resend_otp(data.phone, data.purpose)
        return APIResponse.success(message="OTP resent successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


# ── 5. Login (Password) ───────────────────────────────────────
@router.post(
    "/login",
    response_model=APIResponse,
    summary="Login with phone + password"
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login using phone number and password.
    Returns access_token + refresh_token.
    """
    try:
        result = await auth_service.login_with_password(data, db)
        return APIResponse.success(
            message="Login successful",
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type":    "bearer",
                "user": UserResponse.model_validate(result["user"]).model_dump()
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── 6. Login (OTP / Passwordless) ────────────────────────────
@router.post(
    "/login/otp",
    response_model=APIResponse,
    summary="Passwordless OTP login"
)
async def login_otp(
    data: OTPLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login without a password using OTP.
    1. Call `/auth/send-otp` with purpose=`login`
    2. Enter the OTP here to get tokens
    """
    try:
        result = await auth_service.login_with_otp(data, db)
        return APIResponse.success(
            message="Login successful",
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type":    "bearer",
                "user": UserResponse.model_validate(result["user"]).model_dump()
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── 7. Refresh Token ──────────────────────────────────────────
@router.post(
    "/refresh-token",
    response_model=APIResponse,
    summary="Refresh access token"
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a new access token using your refresh token.
    Call this when your access token expires (every 15 minutes).
    """
    try:
        result = await auth_service.refresh_access_token(data.refresh_token, db)
        return APIResponse.success(
            message="Token refreshed",
            data={
                "access_token":  result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type":    "bearer",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── 8. Logout (Current Device) ────────────────────────────────
@router.post(
    "/logout",
    response_model=APIResponse,
    summary="Logout from current device"
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Logout from the current device.
    Blacklists the current token and removes the session.

    **Requires:** Bearer token in Authorization header.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    result = await auth_service.logout(str(current_user.id), token)
    return APIResponse.success(message=result["message"])


# ── 9. Logout All Devices ─────────────────────────────────────
@router.post(
    "/logout-all",
    response_model=APIResponse,
    summary="Logout from all devices"
)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Logout from ALL devices simultaneously.
    Removes all active sessions for this user.

    **Requires:** Bearer token in Authorization header.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    result = await auth_service.logout_all(str(current_user.id), token)
    return APIResponse.success(message=result["message"])


# ── 10. Forgot Password ───────────────────────────────────────
@router.post(
    "/forgot-password",
    response_model=APIResponse,
    summary="Request password reset OTP"
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send an OTP to the registered phone number for password reset.

    **Next step:** Call `/auth/reset-password` with the OTP.
    """
    try:
        result = await auth_service.forgot_password(data.phone, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 11. Reset Password ────────────────────────────────────────
@router.post(
    "/reset-password",
    response_model=APIResponse,
    summary="Reset password using OTP"
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset the account password using the OTP received via SMS.
    - Verifies OTP
    - Updates password
    - Forces logout on all devices
    """
    try:
        result = await auth_service.reset_password(data, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 12. Change Password ───────────────────────────────────────
@router.post(
    "/change-password",
    response_model=APIResponse,
    summary="Change password (auth required)"
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for the currently logged-in user.
    - Verifies current password
    - Updates to new password
    - Logs out all other devices

    **Requires:** Bearer token in Authorization header.
    """
    try:
        result = await auth_service.change_password(data, current_user, db)
        return APIResponse.success(message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
