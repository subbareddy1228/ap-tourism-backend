"""
services/admin_service.py
Admin business logic — called by src/api/v1/endpoints/admin.py
Handles: settings CRUD, partner commission, report generation,
         analytics aggregation, bulk notifications.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_
from fastapi import status

from src.models.user import User
from src.models.partner import Partner
from src.models.booking import Booking
from src.models.transaction import Transaction
from src.models.support import SupportTicket
from src.models.notification import Notification
from src.common.enums import UserStatus, BookingStatus
from src.core.exceptions import (
    NotFoundException,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# PLATFORM SETTINGS  (key-value store in memory/DB)
# ═══════════════════════════════════════════════════════

# In-memory settings store — replace with DB table if needed
_PLATFORM_SETTINGS: dict = {
    "maintenance_mode":      "false",
    "booking_enabled":       "true",
    "wallet_topup_enabled":  "true",
    "default_commission_pct":"10",
    "support_email":         "support@aptourism.gov.in",
    "max_booking_per_slot":  "50",
}

async def get_platform_settings() -> dict:
    """Return all platform settings."""
    return {"settings": _PLATFORM_SETTINGS}

async def update_platform_setting(key: str, value: str) -> dict:
    """Update a single platform setting by key."""
    if key not in _PLATFORM_SETTINGS:
        raise NotFoundException(f"Setting '{key}' not found")
    _PLATFORM_SETTINGS[key] = value
    logger.info("Platform setting updated key=%s value=%s", key, value)
    return {"key": key, "value": value, "updated": True}

# ═══════════════════════════════════════════════════════
# PARTNER MANAGEMENT
# ═══════════════════════════════════════════════════════

async def set_partner_commission(
    partner_id: str,
    commission_rate: float,
    db: AsyncSession
) -> dict:
    """Set a partner's commission rate."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise NotFoundException("Partner not found")

    partner.commission_rate = commission_rate
    partner.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(partner)

    logger.info("Commission updated partner_id=%s rate=%s", partner_id, commission_rate)
    return {
        "partner_id": str(partner.id),
        "commission_rate": float(partner.commission_rate),
        "message": "Commission rate updated"
    }

# ═══════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════

async def get_booking_report(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Booking report: counts by status and type."""
    query = select(Booking)
    if start_date:
        query = query.where(Booking.created_at >= start_date)
    if end_date:
        query = query.where(Booking.created_at <= end_date)

    total = await db.scalar(select(func.count(Booking.id)))
    confirmed = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED)
    )
    cancelled = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.CANCELLED)
    )
    pending = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.PENDING)
    )

    return {
        "total_bookings": total or 0,
        "confirmed": confirmed or 0,
        "cancelled": cancelled or 0,
        "pending": pending or 0,
        "period": {"from": str(start_date), "to": str(end_date)},
    }

async def get_revenue_report(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Revenue report from successful transactions."""
    query = select(func.sum(Transaction.amount)).where(
        Transaction.status == "SUCCESS"
    )
    if start_date:
        query = query.where(Transaction.created_at >= start_date)
    if end_date:
        query = query.where(Transaction.created_at <= end_date)

    total_revenue = await db.scalar(query) or Decimal("0")
    txn_count = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "SUCCESS")
    ) or 0

    return {
        "total_revenue_inr": float(total_revenue),
        "total_transactions": txn_count,
        "average_order_value": float(total_revenue / txn_count) if txn_count > 0 else 0,
        "period": {"from": str(start_date), "to": str(end_date)},
    }

async def get_user_growth_report(db: AsyncSession) -> dict:
    """User growth report — total, active, new this month."""
    today = date.today()
    month_start = today.replace(day=1)

    total = await db.scalar(select(func.count(User.id))) or 0
    active = await db.scalar(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    ) or 0
    new_this_month = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= month_start)
    ) or 0

    return {
        "total_users": total,
        "active_users": active,
        "new_this_month": new_this_month,
        "suspended_users": total - active,
    }

async def get_partner_performance_report(db: AsyncSession) -> dict:
    """Partner performance — counts by verification status."""
    total = await db.scalar(select(func.count(Partner.id))) or 0
    verified = await db.scalar(
        select(func.count(Partner.id)).where(Partner.verification_status == "VERIFIED")
    ) or 0
    pending = await db.scalar(
        select(func.count(Partner.id)).where(Partner.verification_status == "APPLIED")
    ) or 0

    return {
        "total_partners": total,
        "verified": verified,
        "pending_verification": pending,
        "rejected": total - verified - pending,
    }

# ═══════════════════════════════════════════════════════
# ANALYTICS OVERVIEW
# ═══════════════════════════════════════════════════════

async def get_analytics_overview(db: AsyncSession) -> dict:
    """Single overview for admin dashboard analytics panel."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    bookings_this_week = await db.scalar(
        select(func.count(Booking.id)).where(Booking.created_at >= week_ago)
    ) or 0

    revenue_this_week = await db.scalar(
        select(func.sum(Transaction.amount))
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.created_at >= week_ago)
    ) or Decimal("0")

    open_tickets = await db.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "OPEN")
    ) or 0

    return {
        "bookings_this_week": bookings_this_week,
        "revenue_this_week_inr": float(revenue_this_week),
        "open_support_tickets": open_tickets,
        "week_start": str(week_ago),
        "week_end": str(today),
    }

# ═══════════════════════════════════════════════════════
# BROADCAST NOTIFICATION
# ═══════════════════════════════════════════════════════

async def broadcast_notification(
    title: str,
    body: str,
    db: AsyncSession,
    user_ids: Optional[List[str]] = None
) -> dict:
    """
    Create Notification records for all users (or specific users).
    Firebase push is sent separately via the notifications endpoint.
    """
    if user_ids:
        result = await db.execute(
            select(User.id).where(User.id.in_(user_ids))
        )
    else:
        result = await db.execute(
            select(User.id).where(User.status == UserStatus.ACTIVE)
        )

    ids = result.scalars().all()

    notifications = [
        Notification(
            user_id=uid,
            title=title,
            body=body,
            notif_type="BROADCAST",
            is_read=False,
        )
        for uid in ids
    ]

    db.add_all(notifications)
    await db.commit()

    logger.info("Broadcast sent to %d users", len(ids))
    return {"sent_to": len(ids), "title": title}