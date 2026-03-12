import logging
import random
import string
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.coupon import Coupon, CouponUsage, Referral
from src.schemas.coupon import (
    ValidateCouponRequest, ValidateCouponResponse,
    ApplyCouponRequest, ApplyCouponResponse,
    RemoveCouponRequest, RemoveCouponResponse,
    MyCouponItem, MyCouponsResponse,
    ReferralResponse, ActiveCouponsResponse,
    CouponOut,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_by_code(db: Session, code: str) -> Optional[Coupon]:
    return db.query(Coupon).filter(
        Coupon.code == code.upper(),
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


def _is_valid(coupon: Coupon) -> bool:
    now = datetime.utcnow()
    if not (coupon.valid_from <= now <= coupon.valid_until):
        return False
    max_uses = coupon.usage_limit or coupon.max_uses
    used = coupon.used_count or coupon.current_uses or 0
    if max_uses and used >= max_uses:
        return False
    return True


def _calculate_discount(coupon: Coupon, order_value: float) -> float:
    dtype = str(coupon.discount_type or "").upper()
    value = float(coupon.discount_value or 0)
    if dtype == "FLAT":
        return min(value, order_value)
    elif dtype == "PERCENTAGE":
        disc = order_value * (value / 100)
        max_d = float(coupon.max_discount) if coupon.max_discount else None
        if max_d:
            disc = min(disc, max_d)
        return round(disc, 2)
    return 0.0


# ─────────────────────────────────────────────
# VALIDATE
# ─────────────────────────────────────────────

def validate_coupon(db: Session, data: ValidateCouponRequest) -> ValidateCouponResponse:
    coupon = _get_by_code(db, data.code)

    if not coupon:
        return ValidateCouponResponse(
            is_valid=False, code=data.code.upper(),
            final_amount=data.order_value,
            message="Coupon code not found."
        )

    if not _is_valid(coupon):
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

    per_user = int(coupon.usage_per_user or coupon.max_uses_per_user or 1)
    if _user_usage_count(db, coupon.id, data.user_id) >= per_user:
        return ValidateCouponResponse(
            is_valid=False, code=coupon.code,
            final_amount=data.order_value,
            message="You have already used this coupon the maximum number of times."
        )

    discount = _calculate_discount(coupon, data.order_value)
    final    = round(data.order_value - discount, 2)

    return ValidateCouponResponse(
        is_valid=True,
        code=coupon.code,
        discount_type=str(coupon.discount_type).upper(),
        discount_value=float(coupon.discount_value),
        discount_amount=discount,
        final_amount=final,
        message=f"Coupon valid! You save Rs.{discount:.2f}",
        coupon=CouponOut.model_validate(coupon),
    )


# ─────────────────────────────────────────────
# APPLY
# ─────────────────────────────────────────────

def apply_coupon(db: Session, data: ApplyCouponRequest) -> ApplyCouponResponse:
    val = validate_coupon(db, ValidateCouponRequest(
        user_id=data.user_id, code=data.code, order_value=data.order_value
    ))

    if not val.is_valid:
        return ApplyCouponResponse(
            success=False, code=data.code.upper(),
            discount_amount=0.0, final_amount=data.order_value,
            message=val.message,
        )

    coupon = _get_by_code(db, data.code)
    usage  = CouponUsage(
        coupon_id        = coupon.id,
        user_id          = data.user_id,
        booking_id       = data.booking_id,
        discount_applied = val.discount_amount,
        order_value      = data.order_value,
    )
    db.add(usage)
    coupon.used_count   = (coupon.used_count or 0) + 1
    coupon.current_uses = (coupon.current_uses or 0) + 1
    db.commit()

    logger.info(f"Coupon applied: {coupon.code} user={data.user_id} discount=Rs.{val.discount_amount}")

    return ApplyCouponResponse(
        success=True, code=coupon.code,
        discount_amount=val.discount_amount, final_amount=val.final_amount,
        message=f"Coupon '{coupon.code}' applied! You save Rs.{val.discount_amount:.2f}",
        coupon=CouponOut.model_validate(coupon),
    )


# ─────────────────────────────────────────────
# REMOVE
# ─────────────────────────────────────────────

def remove_coupon(db: Session, user_id: UUID, booking_id: UUID) -> RemoveCouponResponse:
    usage = db.query(CouponUsage).filter(
        CouponUsage.user_id == user_id,
        CouponUsage.booking_id == booking_id,
    ).first()

    if not usage:
        return RemoveCouponResponse(
            success=False,
            message="No coupon found for this booking.",
            refunded_amount=0.0
        )

    refunded = float(usage.discount_applied or 0)
    coupon   = db.query(Coupon).filter(Coupon.id == usage.coupon_id).first()
    if coupon:
        coupon.used_count   = max(0, (coupon.used_count or 0) - 1)
        coupon.current_uses = max(0, (coupon.current_uses or 0) - 1)

    db.delete(usage)
    db.commit()

    return RemoveCouponResponse(
        success=True,
        message=f"Coupon removed. Rs.{refunded:.2f} discount reversed.",
        refunded_amount=refunded,
    )


# ─────────────────────────────────────────────
# MY COUPONS
# ─────────────────────────────────────────────

def get_my_coupons(db: Session, user_id: UUID) -> MyCouponsResponse:
    now    = datetime.utcnow()
    usages = db.query(CouponUsage).filter(CouponUsage.user_id == user_id).all()
    used_coupon_ids = {str(u.coupon_id) for u in usages}

    all_public = db.query(Coupon).filter(
        Coupon.is_public == True,
        Coupon.valid_until >= now,
    ).all()

    available = []
    for c in all_public:
        per_user = int(c.usage_per_user or c.max_uses_per_user or 1)
        count    = sum(1 for u in usages if str(u.coupon_id) == str(c.id))
        available.append(MyCouponItem(
            coupon=CouponOut.model_validate(c),
            is_used=str(c.id) in used_coupon_ids,
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
                discount_applied=float(u.discount_applied or 0),
                is_applicable=False,
            ))
            total_saved += float(u.discount_applied or 0)

    return MyCouponsResponse(
        available=available,
        used=used_items,
        total_savings=round(total_saved, 2)
    )


# ─────────────────────────────────────────────
# REFERRAL
# ─────────────────────────────────────────────

def get_referral_info(db: Session, user_id: UUID) -> ReferralResponse:
    referral = db.query(Referral).filter(Referral.referrer_user_id == user_id).first()

    if not referral:
        code = _gen_referral_code(user_id)

        ref_coupon = Coupon(
            code              = code,
            title             = f"Referral - {code}",
            discount_type     = "FLAT",
            discount_value    = 200.0,
            min_order_value   = 500.0,
            applicable_to     = "ALL",
            applicable_on     = "all",
            valid_from        = datetime.utcnow(),
            valid_until       = datetime(2099, 12, 31),
            max_uses          = 1,
            max_uses_per_user = 1,
            usage_per_user    = 1,
            current_uses      = 0,
            used_count        = 0,
            is_public         = False,
            is_referral       = True,
            coupon_type       = "referral",
            referral_user_id  = user_id,
        )
        db.add(ref_coupon)
        db.flush()

        referral = Referral(
            referrer_user_id = user_id,
            coupon_id        = ref_coupon.id,
            referral_code    = code,
            referrer_reward  = 100.0,
            referred_reward  = 200.0,
        )
        db.add(referral)
        db.commit()
        db.refresh(referral)

    total      = db.query(Referral).filter(Referral.referrer_user_id == user_id).count()
    successful = db.query(Referral).filter(
        Referral.referrer_user_id == user_id,
        Referral.is_redeemed == True,
    ).count()

    return ReferralResponse(
        referral_code        = referral.referral_code,
        referral_link        = f"https://aptravel.in/join?ref={referral.referral_code}",
        referrer_reward      = float(referral.referrer_reward),
        referred_reward      = float(referral.referred_reward),
        total_referrals      = total,
        successful_referrals = successful,
        total_earned         = successful * float(referral.referrer_reward),
    )


# ─────────────────────────────────────────────
# ACTIVE / PUBLIC
# ─────────────────────────────────────────────

def get_active_coupons(db: Session, page: int = 1, per_page: int = 10) -> ActiveCouponsResponse:
    now    = datetime.utcnow()
    offset = (page - 1) * per_page
    query  = db.query(Coupon).filter(
        Coupon.is_public == True,
        Coupon.valid_until >= now,
    )
    total   = query.count()
    coupons = query.order_by(Coupon.valid_until).offset(offset).limit(per_page).all()

    return ActiveCouponsResponse(
        coupons=[CouponOut.model_validate(c) for c in coupons],
        total=total, page=page, per_page=per_page,
    )


def get_by_code_public(db: Session, code: str) -> CouponOut:
    c = _get_by_code(db, code)
    if not c or not c.is_public:
        raise ValueError("Coupon not found")
    return CouponOut.model_validate(c)