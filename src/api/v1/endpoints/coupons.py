import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps.auth import get_current_user
from src.models.user import User
from src.core.database import get_db
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

router = APIRouter(prefix="/coupons", tags=["Coupons"])
logger = logging.getLogger(__name__)


def _err(code: int, msg: str):
    raise HTTPException(status_code=code, detail={"success": False, "error": msg})


# ─── GET / ───────────────────────────────────
@router.get("/", response_model=MyCouponsResponse, summary="List coupons available to user")
async def list_coupons(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_my_coupons(db, current_user.id)


# ─── POST /validate ──────────────────────────
@router.post("/validate", response_model=ValidateCouponResponse, summary="Validate a coupon code")
async def validate(
    body: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body.user_id = current_user.id
    return await validate_coupon(db, body)


# ─── POST /apply ─────────────────────────────
@router.post("/apply", response_model=ApplyCouponResponse, summary="Apply coupon to a booking")
async def apply(
    body: ApplyCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body.user_id = current_user.id
    return await apply_coupon(db, body)


# ─── DELETE /remove ──────────────────────────
@router.delete("/remove", summary="Remove coupon from a booking")
async def remove(
    body: RemoveCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await remove_coupon(db, current_user.id, body.booking_id)


# ─── GET /my-coupons ─────────────────────────
@router.get("/my-coupons", response_model=MyCouponsResponse, summary="User's available and used coupons")
async def my_coupons(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_my_coupons(db, current_user.id)


# ─── GET /referral ───────────────────────────
@router.get("/referral", response_model=ReferralResponse, summary="Get user's referral code and stats")
async def referral(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_referral_info(db, current_user.id)


# ─── GET /active (no auth) ───────────────────
@router.get("/active", response_model=ActiveCouponsResponse, summary="List all active public coupons")
async def active_coupons(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_coupons(db, page, per_page)


# ─── GET /{code} (no auth) ───────────────────
@router.get("/{code}", response_model=CouponOut, summary="Get coupon details by code")
async def coupon_by_code(code: str, db: AsyncSession = Depends(get_db)):
    try:
        return await get_by_code_public(db, code)
    except ValueError as e:
        _err(404, str(e))