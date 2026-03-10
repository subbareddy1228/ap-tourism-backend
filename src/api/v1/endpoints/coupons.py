import math, logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.api.deps import get_current_user
from src.schemas.coupon import (
    CouponApplyRequest, CouponApplyData,
    CouponDetailData, CouponListData, CouponPublicData,
    CouponValidateRequest, CouponValidateData,
    MyCouponsData, ReferralData,
)
from src.services.coupon_service import CouponService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coupon", tags=["Module 16 - Coupons"])

def ok(data, message=""):
    return {"success": True, "data": data, "message": message}

def err(message, code):
    raise HTTPException(status_code=code, detail={"success": False, "error": message, "code": code})

@router.get("/active")
def list_active(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user=Depends(get_current_user)):
    total, items = CouponService.list_active(db, page, limit)
    pages = math.ceil(total / limit) if total else 1
    return ok(CouponListData(data=[CouponPublicData.from_orm(c) for c in items], total=total, page=page, pages=pages, limit=limit), "Active coupons fetched.")

@router.get("/my-coupons")
def my_coupons(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = CouponService.my_coupons(db, user.id)
    return ok(MyCouponsData(data=[CouponDetailData.from_orm(c) for c in items], total=len(items)), "Your coupons fetched.")

@router.get("/referral")
def get_referral(db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = CouponService.get_referral(db, user.id)
    return ok(ReferralData(**result), "Referral coupon fetched.")

@router.post("/validate")
def validate_coupon(body: CouponValidateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = CouponService.validate(db, user.id, body)
    coupon_data = CouponPublicData.from_orm(result["coupon"]) if result["coupon"] else None
    return ok(CouponValidateData(is_valid=result["is_valid"], discount_amount=result["discount_amount"], final_amount=result["final_amount"], error_reason=result["error_reason"], coupon=coupon_data), "Coupon validated.")

@router.post("/apply", status_code=status.HTTP_201_CREATED)
def apply_coupon(body: CouponApplyRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        result = CouponService.apply(db, user.id, body)
    except ValueError as e:
        err(str(e), 400)
    return ok(CouponApplyData(applied_coupon_id=result["applied_coupon_id"], discount_amount=result["discount_amount"], final_amount=result["final_amount"]), f"Coupon applied!")

@router.delete("/remove")
def remove_coupon(applied_coupon_id: UUID = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        CouponService.remove(db, user.id, applied_coupon_id)
    except ValueError as e:
        err(str(e), 404)
    return ok(None, "Coupon removed from cart.")

@router.get("/")
def list_coupons(applicable_to: Optional[str] = Query(None), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user=Depends(get_current_user)):
    total, items = CouponService.list_public(db, applicable_to, page, limit)
    pages = math.ceil(total / limit) if total else 1
    return ok(CouponListData(data=[CouponPublicData.from_orm(c) for c in items], total=total, page=page, pages=pages, limit=limit), "Coupons fetched.")

@router.get("/{code}")
def get_coupon_by_code(code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        coupon = CouponService.get_by_code(db, code)
    except ValueError as e:
        err(str(e), 404)
    return ok(CouponDetailData.from_orm(coupon), "Coupon detail fetched.")
