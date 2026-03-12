import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database import get_db
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


def _err(code: int, msg: str):
    raise HTTPException(status_code=code, detail={"success": False, "error": msg})


@router.get("/", response_model=MyCouponsResponse, summary="List coupons available to user")
def list_coupons(user_id: UUID = Query(...), db: Session = Depends(get_db)):
    return get_my_coupons(db, user_id)


@router.post("/validate", response_model=ValidateCouponResponse, summary="Validate a coupon code (without applying)")
def validate(body: ValidateCouponRequest, db: Session = Depends(get_db)):
    return validate_coupon(db, body)


@router.post("/apply", response_model=ApplyCouponResponse, summary="Apply coupon to a booking")
def apply(body: ApplyCouponRequest, db: Session = Depends(get_db)):
    return apply_coupon(db, body)


@router.delete("/remove", summary="Remove coupon from a booking")
def remove(body: RemoveCouponRequest, db: Session = Depends(get_db)):
    return remove_coupon(db, body.user_id, body.booking_id)


@router.get("/my-coupons", response_model=MyCouponsResponse, summary="User's available and used coupons with total savings")
def my_coupons(user_id: UUID = Query(...), db: Session = Depends(get_db)):
    return get_my_coupons(db, user_id)


@router.get("/referral", response_model=ReferralResponse, summary="Get user's referral code and stats")
def referral(user_id: UUID = Query(...), db: Session = Depends(get_db)):
    return get_referral_info(db, user_id)


@router.get("/active", response_model=ActiveCouponsResponse, summary="List all active public coupons (no auth)")
def active_coupons(page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    return get_active_coupons(db, page, per_page)


@router.get("/{code}", response_model=CouponOut, summary="Get public coupon details by code (no auth)")
def coupon_by_code(code: str, db: Session = Depends(get_db)):
    try:
        return get_by_code_public(db, code)
    except ValueError as e:
        _err(404, str(e))