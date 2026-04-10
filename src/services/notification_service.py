"""
services/notification_service.py
Business logic for M14 — Notification APIs.
Owner: LEV156 Ram Kishore Pawar

Functions (one per endpoint):
    get_notifications          — list inbox with pagination + filters
    get_unread_count           — quick unread badge count
    get_notification_by_id     — single notification detail
    mark_notifications_read    — mark specific IDs as read
    mark_all_read              — mark every unread notification as read
    delete_notification        — soft-delete (hard-delete) one notification
    send_notification          — admin: dispatch to one or many users
    get_preferences            — fetch or create preference row
    update_preferences         — patch channel / type toggles
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_

from src.models.notification import Notification, NotificationPreference
from src.models.user import User
from src.schemas.notification import (
    SendNotificationRequest,
    MarkReadRequest,
    UpdatePreferencesRequest,
)
from src.integrations.firebase import send_push, send_multicast
from src.integrations.msg91 import send_sms
from src.core.exceptions import (
    NotFoundException,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPER
# ═══════════════════════════════════════════════════════════════

async def _get_or_create_preferences(
    user_id: UUID, db: AsyncSession
) -> NotificationPreference:
    """Return preference row for user, creating defaults if missing."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreference(
            user_id=user_id,
            push_enabled=True,
            sms_enabled=True,
            email_enabled=True,
            type_preferences={
                "promotions":      True,
                "reminders":       True,
                "booking_updates": True,
                "system":          True,
            },
        )
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return prefs

# ═══════════════════════════════════════════════════════════════
# 1. LIST NOTIFICATIONS
# GET /notifications
# ═══════════════════════════════════════════════════════════════

async def get_notifications(
    current_user: User,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
    notification_type: Optional[str] = None,
) -> dict:
    """
    Return paginated inbox for the current user.
    Newest notifications first.
    Optional filters: unread_only, type.
    """
    query = select(Notification).where(
        Notification.user_id == current_user.id
    )

    if unread_only:
        query = query.where(Notification.is_read == False)

    if notification_type:
        query = query.where(Notification.type == notification_type)

    # total matching rows
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # unread count (always, regardless of filter)
    unread_result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
    )
    unread_count = unread_result.scalar()

    # paginate — newest first
    query = (
        query
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    notifications = result.scalars().all()

    return {
        "notifications": notifications,
        "total":         total,
        "unread_count":  unread_count,
        "page":          page,
        "per_page":      per_page,
    }

# ═══════════════════════════════════════════════════════════════
# 2. UNREAD COUNT
# GET /notifications/unread-count
# ═══════════════════════════════════════════════════════════════

async def get_unread_count(current_user: User, db: AsyncSession) -> int:
    """Return number of unread notifications for the current user."""
    result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
    )
    return result.scalar()

# ═══════════════════════════════════════════════════════════════
# 3. GET SINGLE NOTIFICATION
# GET /notifications/{notification_id}
# ═══════════════════════════════════════════════════════════════

async def get_notification_by_id(
    notification_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> Notification:
    """Fetch a single notification — verifies ownership."""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise NotFoundException("Notification not found",)

    # Auto-mark as read on open
    if not notification.is_read:
        notification.is_read = True
        notification.read_at  = datetime.utcnow()
        await db.commit()
        await db.refresh(notification)

    return notification

# ═══════════════════════════════════════════════════════════════
# 4. MARK SPECIFIC NOTIFICATIONS AS READ
# POST /notifications/mark-read
# ═══════════════════════════════════════════════════════════════

async def mark_notifications_read(
    data: MarkReadRequest,
    current_user: User,
    db: AsyncSession,
) -> dict:
    """
    Bulk-mark a list of notification IDs as read.
    IDs that don't belong to the current user are silently skipped.
    """
    now = datetime.utcnow()

    await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.id.in_([str(nid) for nid in data.notification_ids]),
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
        .values(is_read=True, read_at=now)
    )
    await db.commit()

    return {"message": f"{len(data.notification_ids)} notification(s) marked as read"}

# ═══════════════════════════════════════════════════════════════
# 5. MARK ALL AS READ
# POST /notifications/mark-all-read
# ═══════════════════════════════════════════════════════════════

async def mark_all_read(current_user: User, db: AsyncSession) -> dict:
    """Mark every unread notification for the current user as read."""
    now = datetime.utcnow()

    result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
        .values(is_read=True, read_at=now)
    )
    await db.commit()

    updated = result.rowcount
    return {"message": f"All {updated} notification(s) marked as read"}

# ═══════════════════════════════════════════════════════════════
# 6. DELETE A NOTIFICATION
# DELETE /notifications/{notification_id}
# ═══════════════════════════════════════════════════════════════

async def delete_notification(
    notification_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> dict:
    """Hard-delete a notification — verifies ownership first."""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise NotFoundException("Notification not found",)

    await db.delete(notification)
    await db.commit()

    return {"message": "Notification deleted"}

# ═══════════════════════════════════════════════════════════════
# 7. SEND NOTIFICATION  (admin)
# POST /notifications/send
# ═══════════════════════════════════════════════════════════════

async def send_notification(
    data: SendNotificationRequest,
    db: AsyncSession,
) -> dict:
    """
    Admin endpoint — dispatch a notification to one or many users.

    Flow:
      1. Persist a Notification row for every user_id.
      2. If channel == 'push': call Firebase FCM.
      3. If channel == 'sms':  call Twilio (requires phone lookup).
      4. Other channels (email, in_app) are stored only — no external call.

    Returns: { sent: int, failed: int }
    """
    sent   = 0
    failed = 0

    for uid in data.user_ids:
        # Fetch user to get phone / fcm_token
        user_result = await db.execute(
            select(User).where(User.id == uid)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.warning("send_notification: user_id=%s not found — skipped", uid)
            failed += 1
            continue

        # Persist inbox row
        notification = Notification(
            user_id=user.id,
            type=data.type,
            title=data.title,
            body=data.body,
            channel=data.channel,
            data=data.data,
        )
        db.add(notification)

        # Dispatch on the requested channel
        try:
            if data.channel == "push":
                fcm_token = getattr(user, "fcm_token", None)
                if fcm_token:
                    ok = await send_push(
                        fcm_token=fcm_token,
                        title=data.title,
                        body=data.body,
                        data=data.data,
                    )
                    if ok:
                        notification.fcm_message_id = "sent"
                else:
                    logger.info(
                        "No FCM token for user_id=%s — stored as in_app only", uid
                    )

            elif data.channel == "sms":
                if user.phone:
                    await send_sms(user.phone, data.body)
                else:
                    logger.info("No phone for user_id=%s — SMS skipped", uid)

            # email / in_app: stored only, no external dispatch here
            sent += 1

        except Exception as e:
            logger.error(
                "send_notification dispatch failed user_id=%s channel=%s error=%s",
                uid, data.channel, str(e),
            )
            failed += 1

    await db.commit()

    return {
        "message": f"Notification dispatch complete",
        "sent":    sent,
        "failed":  failed,
    }

# ═══════════════════════════════════════════════════════════════
# 8. GET PREFERENCES
# GET /notifications/preferences
# ═══════════════════════════════════════════════════════════════

async def get_preferences(
    current_user: User, db: AsyncSession
) -> NotificationPreference:
    """Fetch (or auto-create) notification preferences for the current user."""
    return await _get_or_create_preferences(current_user.id, db)

# ═══════════════════════════════════════════════════════════════
# 9. UPDATE PREFERENCES
# PUT /notifications/preferences
# ═══════════════════════════════════════════════════════════════

async def update_preferences(
    data: UpdatePreferencesRequest,
    current_user: User,
    db: AsyncSession,
) -> NotificationPreference:
    """
    Patch notification preferences.
    Only supplied fields are updated — missing fields keep their current value.
    """
    prefs = await _get_or_create_preferences(current_user.id, db)

    if data.push_enabled is not None:
        prefs.push_enabled = data.push_enabled

    if data.sms_enabled is not None:
        prefs.sms_enabled = data.sms_enabled

    if data.email_enabled is not None:
        prefs.email_enabled = data.email_enabled

    if data.type_preferences is not None:
        # Merge into existing JSONB — don't overwrite unmentioned keys
        current_type_prefs = dict(prefs.type_preferences or {})
        incoming = data.type_preferences.model_dump(exclude_none=True)
        current_type_prefs.update(incoming)
        prefs.type_preferences = current_type_prefs

    prefs.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(prefs)

    return prefs

# ── Module-level alias (called by GET /users/me/notifications) ───────────────
# Endpoint passes user_id: str; get_notifications expects a User object.
# This wrapper adapts the signature without touching the endpoint or existing function.

async def get_user_notifications(
    user_id: str,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
) -> dict:
    from src.models.user import User as UserModel
    from sqlalchemy import select

    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    return await get_notifications(
        current_user=user,
        db=db,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
    )