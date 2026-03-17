import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database import get_db
from src.core.config import settings
from src.schemas.coupon import (
    ValidateCouponRequest, ValidateCouponResponse,
    ApplyCouponRequest, ApplyCouponResponse,
    RemoveCouponRequest, RemoveCouponResponse,
    MyCouponsResponse, ReferralResponse,
    ActiveCouponsResponse, CouponOut,
)
from src.services.coupon_service import (
    validate_coupon, apply_coupon, remove_coupon,
    get_my_coupons, get_referral_info,
    get_active_coupons, get_by_code_public,
)

router = APIRouter(prefix="/coupon", tags=["Module 16 - Coupons"])
logger = logging.getLogger(__name__)
security = HTTPBearer()


# ─────────────────────────────────────────────
# JWT DEPENDENCY
# ─────────────────────────────────────────────

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: user_id not found.")
        return UUID(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")


def _err(code: int, msg: str):
    raise HTTPException(status_code=code, detail={"success": False, "error": msg})


# ─── GET / ───────────────────────────────────
@router.get("/", response_model=MyCouponsResponse, summary="List coupons available to user")
async def list_coupons(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_my_coupons(db, user_id)


# ─── POST /validate ──────────────────────────
@router.post("/validate", response_model=ValidateCouponResponse, summary="Validate a coupon code")
async def validate(
    body: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    body.user_id = user_id
    return await validate_coupon(db, body)


# ─── POST /apply ─────────────────────────────
@router.post("/apply", response_model=ApplyCouponResponse, summary="Apply coupon to a booking")
async def apply(
    body: ApplyCouponRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    body.user_id = user_id
    return await apply_coupon(db, body)


# ─── DELETE /remove ──────────────────────────
@router.delete("/remove", summary="Remove coupon from a booking")
async def remove(
    body: RemoveCouponRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await remove_coupon(db, user_id, body.booking_id)


# ─── GET /my-coupons ─────────────────────────
@router.get("/my-coupons", response_model=MyCouponsResponse, summary="User's available and used coupons")
async def my_coupons(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_my_coupons(db, user_id)


# ─── GET /referral ───────────────────────────
@router.get("/referral", response_model=ReferralResponse, summary="Get user's referral code and stats")
async def referral(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_referral_info(db, user_id)


# ─── GET /active (no auth) ───────────────────
@router.get("/active", response_model=ActiveCouponsResponse, summary="List all active public coupons (no auth)")
async def active_coupons(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_coupons(db, page, per_page)


# ─── GET /{code} (no auth) ───────────────────
@router.get("/{code}", response_model=CouponOut, summary="Get public coupon details by code (no auth)")
async def coupon_by_code(code: str, db: AsyncSession = Depends(get_db)):
    try:
        return await get_by_code_public(db, code)
    except ValueError as e:
        _err(404, str(e))