"""
services/analytics_service.py
Business analytics aggregation for admin dashboard.
"""

from datetime import date, timedelta, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.user import User
from src.models.booking import Booking
from src.models.transaction import Transaction
from src.models.partner import Partner
from src.models.temple import Temple
from src.common.enums import UserStatus, BookingStatus


async def get_platform_overview(db: AsyncSession) -> dict:
    """
    Full analytics snapshot for admin dashboard.
    Returns: users, bookings, revenue, partners, top temples.
    """
    today = date.today()
    month_start = today.replace(day=1)
    week_ago = today - timedelta(days=7)

    # ── Users ────────────────────────────────────────────────
    total_users = await db.scalar(select(func.count(User.id))) or 0
    new_users_month = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= month_start)
    ) or 0

    # ── Bookings ─────────────────────────────────────────────
    total_bookings = await db.scalar(select(func.count(Booking.id))) or 0
    bookings_week = await db.scalar(
        select(func.count(Booking.id)).where(Booking.created_at >= week_ago)
    ) or 0
    confirmed_bookings = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED)
    ) or 0

    # ── Revenue ──────────────────────────────────────────────
    total_revenue = await db.scalar(
        select(func.sum(Transaction.amount)).where(Transaction.status == "SUCCESS")
    ) or Decimal("0")
    month_revenue = await db.scalar(
        select(func.sum(Transaction.amount))
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.created_at >= month_start)
    ) or Decimal("0")

    # ── Partners ─────────────────────────────────────────────
    total_partners = await db.scalar(select(func.count(Partner.id))) or 0

    # ── Top Temples by booking_count ──────────────────────────
    top_temples_result = await db.execute(
        select(Temple.name, Temple.booking_count)
        .order_by(Temple.booking_count.desc())
        .limit(5)
    )
    top_temples = [
        {"name": r.name, "bookings": r.booking_count}
        for r in top_temples_result
    ]

    return {
        "users": {
            "total": total_users,
            "new_this_month": new_users_month,
        },
        "bookings": {
            "total": total_bookings,
            "this_week": bookings_week,
            "confirmed": confirmed_bookings,
        },
        "revenue": {
            "total_inr": float(total_revenue),
            "this_month_inr": float(month_revenue),
        },
        "partners": {"total": total_partners},
        "top_temples": top_temples,
        "generated_at": datetime.utcnow().isoformat(),
    }