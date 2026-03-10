import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session
from src.models.coupon import Coupon, CouponUsage, DiscountType
from src.schemas.coupon import CouponValidateRequest, CouponApplyRequest

logger = logging.getLogger(__name__)
REFERRAL_REWARD = Decimal("200.00")

def _calc_discount(coupon, cart_amount):
    if coupon.discount_type == DiscountType.PERCENTAGE:
        raw = (cart_amount * coupon.discount_value / 100).quantize(Decimal("0.01"))
        return min(raw, coupon.max_discount) if coupon.max_discount else raw
    return min(coupon.discount_value, cart_amount)

def _invalid(cart_amount, reason):
    return {"is_valid": False, "discount_amount": Decimal("0"), "final_amount": cart_amount, "error_reason": reason, "coupon": None}

def _run_validate(db, user_id, code, cart_amount, applicable_to):
    coupon = db.query(Coupon).filter(Coupon.code == code.strip().upper()).first()
    if not coupon: return _invalid(cart_amount, "Coupon code not found.")
    now = datetime.utcnow()
    if not coupon.is_active: return _invalid(cart_amount, "Coupon is inactive.")
    if now < coupon.valid_from: return _invalid(cart_amount, "Coupon is not yet active.")
    if now > coupon.valid_until: return _invalid(cart_amount, "Coupon has expired.")
    if cart_amount < coupon.min_order_value: return _invalid(cart_amount, f"Minimum order value is ₹{coupon.min_order_value:.0f}.")
    if coupon.applicable_to != "ALL" and applicable_to and coupon.applicable_to != applicable_to:
        return _invalid(cart_amount, f"Coupon only valid for {coupon.applicable_to} bookings.")
    if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses: return _invalid(cart_amount, "Coupon usage limit reached.")
    user_uses = db.query(CouponUsage).filter(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id).count()
    if user_uses >= coupon.max_uses_per_user: return _invalid(cart_amount, "You have already used this coupon.")
    discount = _calc_discount(coupon, cart_amount)
    return {"is_valid": True, "discount_amount": discount, "final_amount": cart_amount - discount, "error_reason": None, "coupon": coupon}

class CouponService:
    @staticmethod
    def list_public(db, applicable_to, page, limit):
        now = datetime.utcnow()
        q = db.query(Coupon).filter(Coupon.is_active == True, Coupon.is_public == True, Coupon.valid_from <= now, Coupon.valid_until >= now)
        if applicable_to:
            q = q.filter(or_(Coupon.applicable_to == applicable_to, Coupon.applicable_to == "ALL"))
        total = q.count()
        items = q.order_by(Coupon.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        return total, items

    @staticmethod
    def list_active(db, page, limit):
        now = datetime.utcnow()
        q = db.query(Coupon).filter(Coupon.is_active == True, Coupon.valid_from <= now, Coupon.valid_until >= now)
        total = q.count()
        items = q.order_by(Coupon.valid_until.asc()).offset((page - 1) * limit).limit(limit).all()
        return total, items

    @staticmethod
    def my_coupons(db, user_id):
        now = datetime.utcnow()
        return db.query(Coupon).filter(Coupon.is_active == True, Coupon.assigned_user_id == user_id, Coupon.valid_until >= now).order_by(Coupon.valid_until.asc()).all()

    @staticmethod
    def get_referral(db, user_id):
        code = f"REF{str(user_id).replace('-', '').upper()[:8]}"
        coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.is_referral == True).first()
        total_referrals = 0
        if coupon:
            total_referrals = db.query(CouponUsage).filter(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id != user_id).count()
        return {"referral_code": code, "reward_amount": REFERRAL_REWARD, "total_referrals": total_referrals, "total_earned": REFERRAL_REWARD * total_referrals}

    @staticmethod
    def get_by_code(db, code):
        coupon = db.query(Coupon).filter(Coupon.code == code.strip().upper()).first()
        if not coupon: raise ValueError(f"Coupon '{code}' not found.")
        return coupon

    @staticmethod
    def validate(db, user_id, data):
        return _run_validate(db, user_id, data.code, data.cart_amount, data.applicable_to)

    @staticmethod
    def apply(db, user_id, data):
        result = _run_validate(db, user_id, data.code, data.cart_amount, applicable_to=None)
        if not result["is_valid"]: raise ValueError(result["error_reason"])
        coupon = result["coupon"]
        usage = CouponUsage(coupon_id=coupon.id, user_id=user_id, booking_id=data.booking_id, discount_amount=result["discount_amount"])
        coupon.current_uses += 1
        db.add(usage); db.commit(); db.refresh(usage)
        result["applied_coupon_id"] = usage.id
        return result

    @staticmethod
    def remove(db, user_id, applied_coupon_id):
        usage = db.query(CouponUsage).filter(CouponUsage.id == applied_coupon_id, CouponUsage.user_id == user_id).first()
        if not usage: raise ValueError("Applied coupon record not found.")
        coupon = db.query(Coupon).filter(Coupon.id == usage.coupon_id).first()
        if coupon and coupon.current_uses > 0: coupon.current_uses -= 1
        db.delete(usage); db.commit()