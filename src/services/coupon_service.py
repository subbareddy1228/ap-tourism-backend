"""
src/services/coupon_service.py — Module 16 Coupon Business Logic
"""
import logging
import random
import string
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.coupon import Coupon, CouponUsage, Referral, DiscountType, CouponType
from src.schemas.coupon import (
    ValidateCouponRequest, ValidateCouponResponse,
    ApplyCouponRequest, ApplyCouponResponse,
    MyCouponItem, MyCouponsResponse,
    ReferralResponse, ActiveCouponsResponse,
    CouponOut, CreateCouponRequest, UpdateCouponRequest,
    AdminCouponOut,
)

logger = logging.getLogger(__name__)


def _get_by_code(db: Session, code: str) -> Optional[Coupon]:
    return db.query(Coupon).filter(
        Coupon.code == code.upper(),
        Coupon.is_active == True,
    ).first()


def _user_usage_count(db: Session, coupon_id: UUID, user_id: UUID) -> int:
    return db.query(CouponUsage).filter(
        CouponUsage.coupon_id == coupon_id,
        CouponUsage.user_id == user_id,
    ).count()


def _gen_referral_code(user_id: UUID) -> str:
    prefix = str(user_id).replace("-", "")[:6].upper()
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"REF{prefix}{suffix}"


def validate_coupon(db: Session, data: ValidateCouponRequest) -> ValidateCouponResponse:
    coupon = _get_by_code(db, data.code)

    if not coupon:
        return ValidateCouponResponse(
            is_valid=False, code=data.code.upper(),
            final_amount=data.order_value,
            message="Coupon code not found."
        )
    if not coupon.is_valid():
        return ValidateCouponResponse(
            is_valid=False, code=coupon.code,
            final_amount=data.order_value,
            message="Coupon has expired or is no longer active."
        )
    min_val = float(coupon.min_order_value or 0)
    if data.order_value < min_val:
        return ValidateCouponResponse(
            is_valid=False, code=coupon.code,
            final_amount=data.order_value,
            message=f"Minimum order value Rs.{min_val:.0f} required."
        )

    per_user = coupon.usage_per_user or coupon.max_uses_per_user or 1
    usage_count = _user_usage_count(db, coupon.id, data.user_id)
    if usage_count >= per_user:
        return ValidateCouponResponse(
            is_valid=False, code=coupon.code,
            final_amount=data.order_value,
            message="You have already used this coupon the maximum number of times."
        )

    discount = coupon.calculate_discount(data.order_value)
    final    = round(data.order_value - discount, 2)

    return ValidateCouponResponse(
        is_valid=True,
        code=coupon.code,
        discount_type=str(coupon.discount_type),
        discount_value=float(coupon.discount_value),
        discount_amount=discount,
        final_amount=final,
        message=f"Coupon valid! You save Rs.{discount:.2f}",
        coupon=CouponOut.model_validate(coupon),
    )


def apply_coupon(db: Session, data: ApplyCouponRequest) -> ApplyCouponResponse:
    validation = validate_coupon(
        db, ValidateCouponRequest(user_id=data.user_id, code=data.code, order_value=data.order_value)
    )
    if not validation.is_valid:
        return ApplyCouponResponse(
            success=False, code=data.code.upper(),
            discount_amount=0.0, final_amount=data.order_value,
            message=validation.message,
        )

    coupon = _get_by_code(db, data.code)
    usage  = CouponUsage(
        coupon_id        = coupon.id,
        user_id          = data.user_id,
        booking_id       = data.booking_id,
        discount_applied = validation.discount_amount,
        order_value      = data.order_value,
    )
    db.add(usage)
    coupon.used_count    = (coupon.used_count or 0) + 1
    coupon.current_uses  = (coupon.current_uses or 0) + 1
    db.commit()

    return ApplyCouponResponse(
        success=True,
        code=coupon.code,
        discount_amount=validation.discount_amount,
        final_amount=validation.final_amount,
        message=f"Coupon applied! You save Rs.{validation.discount_amount:.2f}",
        coupon=CouponOut.model_validate(coupon),
    )


def remove_coupon(db: Session, user_id: UUID, booking_id: UUID):
    usage = db.query(CouponUsage).filter(
        CouponUsage.user_id == user_id,
        CouponUsage.booking_id == booking_id,
    ).first()
    if not usage:
        return {"success": False, "message": "No coupon found for this booking.", "refunded_amount": 0.0}

    refunded = usage.discount_applied
    coupon   = db.query(Coupon).filter(Coupon.id == usage.coupon_id).first()
    if coupon:
        if coupon.used_count and coupon.used_count > 0:
            coupon.used_count -= 1
        if coupon.current_uses and coupon.current_uses > 0:
            coupon.current_uses -= 1
    db.delete(usage)
    db.commit()
    return {"success": True, "message": f"Coupon removed. Rs.{refunded:.2f} discount reversed.", "refunded_amount": refunded}


def get_my_coupons(db: Session, user_id: UUID) -> MyCouponsResponse:
    now = datetime.utcnow()
    all_active = db.query(Coupon).filter(
        Coupon.is_active == True,
        Coupon.valid_until >= now,
    ).all()

    usages   = db.query(CouponUsage).filter(CouponUsage.user_id == user_id).all()
    used_ids = {str(u.coupon_id) for u in usages}

    available = []
    for c in all_active:
        if not (c.is_public or str(c.coupon_type).lower() == "public"):
            continue
        per_user = c.usage_per_user or c.max_uses_per_user or 1
        count    = sum(1 for u in usages if str(u.coupon_id) == str(c.id))
        available.append(MyCouponItem(
            coupon=CouponOut.model_validate(c),
            is_used=str(c.id) in used_ids,
            is_applicable=count < per_user,
        ))

    used_items  = []
    total_saved = 0.0
    for u in usages:
        c = db.query(Coupon).filter(Coupon.id == u.coupon_id).first()
        if c:
            used_items.append(MyCouponItem(
                coupon=CouponOut.model_validate(c),
                is_used=True,
                used_at=u.used_at,
                discount_applied=u.discount_applied,
                is_applicable=False,
            ))
            total_saved += u.discount_applied

    return MyCouponsResponse(available=available, used=used_items, total_savings=round(total_saved, 2))


def get_referral_info(db: Session, user_id: UUID) -> ReferralResponse:
    referral = db.query(Referral).filter(Referral.referrer_user_id == user_id).first()
    if not referral:
        code       = _gen_referral_code(user_id)
        ref_coupon = Coupon(
            code            = code,
            title           = f"Referral — {code}",
            discount_type   = "flat",
            discount_value  = 200.0,
            min_order_value = 500.0,
            valid_from      = datetime.utcnow(),
            valid_until     = datetime(2099, 12, 31),
            max_uses        = 1,
            is_public       = False,
            is_referral     = True,
            referral_user_id= user_id,
        )
        db.add(ref_coupon)
        db.flush()
        referral = Referral(
            referrer_user_id=user_id,
            coupon_id=ref_coupon.id,
            referral_code=code,
            referrer_reward=100.0,
            referred_reward=200.0,
        )
        db.add(referral)
        db.commit()
        db.refresh(referral)

    total      = db.query(Referral).filter(Referral.referrer_user_id == user_id).count()
    successful = db.query(Referral).filter(Referral.referrer_user_id == user_id, Referral.is_redeemed == True).count()

    return ReferralResponse(
        referral_code=referral.referral_code,
        referral_link=f"https://aptravel.in/join?ref={referral.referral_code}",
        referrer_reward=referral.referrer_reward,
        referred_reward=referral.referred_reward,
        total_referrals=total,
        successful_referrals=successful,
        total_earned=successful * referral.referrer_reward,
    )


def get_active_coupons(db: Session, page: int = 1, per_page: int = 10) -> ActiveCouponsResponse:
    now    = datetime.utcnow()
    offset = (page - 1) * per_page
    query  = db.query(Coupon).filter(
        Coupon.is_active == True,
        Coupon.is_public == True,
        Coupon.valid_until >= now,
    )
    total   = query.count()
    coupons = query.order_by(Coupon.created_at.desc()).offset(offset).limit(per_page).all()
    return ActiveCouponsResponse(
        coupons=[CouponOut.model_validate(c) for c in coupons],
        total=total, page=page, per_page=per_page,
    )


def get_by_code_public(db: Session, code: str) -> CouponOut:
    c = _get_by_code(db, code)
    if not c:
        raise ValueError("Coupon not found")
    return CouponOut.model_validate(c)


def admin_create(db: Session, admin_id: UUID, data: CreateCouponRequest) -> AdminCouponOut:
    if _get_by_code(db, data.code):
        raise ValueError(f"Coupon '{data.code}' already exists")
    c = Coupon(
        code            = data.code,
        title           = data.title,
        description     = data.description,
        discount_type   = data.discount_type,
        discount_value  = data.discount_value,
        max_discount    = data.max_discount,
        min_order_value = data.min_order_value,
        valid_from      = data.valid_from,
        valid_until     = data.valid_until,
        max_uses        = data.usage_limit,
        usage_limit     = data.usage_limit,
        max_uses_per_user = data.usage_per_user,
        usage_per_user  = data.usage_per_user,
        is_public       = data.coupon_type == "public",
        coupon_type     = data.coupon_type,
        applicable_on   = data.applicable_on,
        created_by      = admin_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return AdminCouponOut.model_validate(c)


def admin_update(db: Session, coupon_id: UUID, data: UpdateCouponRequest) -> AdminCouponOut:
    c = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not c:
        raise ValueError("Coupon not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return AdminCouponOut.model_validate(c)


def admin_delete(db: Session, coupon_id: UUID) -> None:
    c = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not c:
        raise ValueError("Coupon not found")
    c.is_active = False
    db.commit()


def admin_list(db: Session, page: int = 1, per_page: int = 20) -> List[AdminCouponOut]:
    offset  = (page - 1) * per_page
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).offset(offset).limit(per_page).all()
    return [AdminCouponOut.model_validate(c) for c in coupons]