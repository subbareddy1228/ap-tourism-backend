"""
repositories/coupon_repo.py
DB access for Coupon model.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.coupon import Coupon


async def get_coupon_by_code(code: str, db: AsyncSession) -> Optional[Coupon]:
    """Fetch active coupon by code string (case-insensitive)."""
    result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper().strip()
        )
    )
    return result.scalar_one_or_none()


async def get_active_coupons(
    db: AsyncSession, page: int = 1, per_page: int = 20
) -> dict:
    """List all currently active and valid public coupons."""
    now = datetime.utcnow()
    query = select(Coupon).where(
        Coupon.is_active == True,
        Coupon.valid_from <= now,
        Coupon.valid_until >= now,
    )
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(Coupon.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {
        "coupons": result.scalars().all(),
        "total": total or 0,
        "page": page,
        "per_page": per_page,
    }


async def get_coupon_by_id(coupon_id: str, db: AsyncSession) -> Optional[Coupon]:
    """Fetch coupon by UUID primary key."""
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id)
    )
    return result.scalar_one_or_none()


async def increment_coupon_usage(coupon: Coupon, db: AsyncSession) -> Coupon:
    """Increment used_count by 1 after a successful coupon apply."""
    coupon.used_count = (coupon.used_count or 0) + 1
    coupon.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(coupon)
    return coupon