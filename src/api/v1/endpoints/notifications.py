"""
api/v1/endpoints/notifications.py
M14 — Notification APIs  (8 endpoints)
Owner: LEV156 Ram Kishore Pawar

Routes:
  GET    /notifications                       → List inbox (paginated)
  GET    /notifications/unread-count          → Unread badge count
  GET    /notifications/{notification_id}     → Single notification (auto-marks read)
  POST   /notifications/mark-read            → Mark specific IDs as read
  POST   /notifications/mark-all-read        → Mark all as read
  DELETE /notifications/{notification_id}    → Delete one notification
  POST   /notifications/send                 → Admin: send to users
  GET    /notifications/preferences          → Get channel preferences
  PUT    /notifications/preferences          → Update channel preferences
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_admin_user
from src.models.user import User
from src.schemas.notification import (
    SendNotificationRequest,
    MarkReadRequest,
    UpdatePreferencesRequest,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    PreferenceResponse,
)
from src.common.responses import APIResponse
from src.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── 1. LIST INBOX ─────────────────────────────────────────────
@router.get(
    "",
    response_model=APIResponse,
    summary="List notification inbox",
)
async def list_notifications(
    page:       int           = Query(default=1,     ge=1),
    per_page:   int           = Query(default=20,    ge=1, le=100),
    unread_only: bool         = Query(default=False, description="Return only unread notifications"),
    type:       Optional[str] = Query(default=None,  description="Filter by type e.g. booking_confirmed"),
    current_user: User        = Depends(get_current_user),
    db: AsyncSession          = Depends(get_db),
):
    """
    Get paginated list of notifications for the logged-in user.

    **Filters:**
    - `unread_only`: only return unread notifications
    - `type`: filter by notification type (booking_confirmed, promotion, etc.)

    Returns newest first.
    """
    result = await notification_service.get_notifications(
        current_user=current_user,
        db=db,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
        notification_type=type,
    )
    return APIResponse.success(
        message="Notifications fetched",
        data={
            "notifications": [
                NotificationResponse.model_validate(n).model_dump()
                for n in result["notifications"]
            ],
            "total":        result["total"],
            "unread_count": result["unread_count"],
            "page":         result["page"],
            "per_page":     result["per_page"],
        },
    )


# ── 2. UNREAD COUNT ───────────────────────────────────────────
@router.get(
    "/unread-count",
    response_model=APIResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    current_user: User   = Depends(get_current_user),
    db: AsyncSession     = Depends(get_db),
):
    """
    Returns the number of unread notifications.
    Used to display the badge count on the app's notification bell.
    """
    count = await notification_service.get_unread_count(current_user, db)
    return APIResponse.success(
        message="Unread count fetched",
        data={"unread_count": count},
    )


# ── 3. GET SINGLE NOTIFICATION ────────────────────────────────
@router.get(
    "/{notification_id}",
    response_model=APIResponse,
    summary="Get notification detail",
)
async def get_notification(
    notification_id: UUID,
    current_user: User   = Depends(get_current_user),
    db: AsyncSession     = Depends(get_db),
):
    """
    Get a single notification by ID.
    Automatically marks the notification as read on open.
    Returns 404 if not found or not owned by the current user.
    """
    notification = await notification_service.get_notification_by_id(
        notification_id, current_user, db
    )
    return APIResponse.success(
        message="Notification fetched",
        data=NotificationResponse.model_validate(notification).model_dump(),
    )


# ── 4. MARK SPECIFIC IDs AS READ ─────────────────────────────
@router.post(
    "/mark-read",
    response_model=APIResponse,
    summary="Mark notifications as read",
)
async def mark_read(
    data: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Mark one or more specific notifications as read by their IDs.
    IDs that don't belong to the current user are silently skipped.
    """
    result = await notification_service.mark_notifications_read(
        data, current_user, db
    )
    return APIResponse.success(message=result["message"])


# ── 5. MARK ALL AS READ ───────────────────────────────────────
@router.post(
    "/mark-all-read",
    response_model=APIResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """Mark every unread notification in the user's inbox as read in one call."""
    result = await notification_service.mark_all_read(current_user, db)
    return APIResponse.success(message=result["message"])


# ── 6. DELETE NOTIFICATION ────────────────────────────────────
@router.delete(
    "/{notification_id}",
    response_model=APIResponse,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: UUID,
    current_user: User   = Depends(get_current_user),
    db: AsyncSession     = Depends(get_db),
):
    """
    Permanently delete a notification from the inbox.
    Returns 404 if the notification doesn't exist or isn't owned by the current user.
    """
    result = await notification_service.delete_notification(
        notification_id, current_user, db
    )
    return APIResponse.success(message=result["message"])


# ── 7. SEND NOTIFICATION  (admin only) ────────────────────────
@router.post(
    "/send",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send notification to users (admin)",
)
async def send_notification(
    data: SendNotificationRequest,
    admin: User      = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Admin only.** Dispatch a notification to one or more users.

    **Channels:**
    - `push`   — Firebase FCM (requires user has FCM token registered)
    - `sms`    — Twilio SMS to registered phone number
    - `email`  — stored only (email dispatch via task queue, not here)
    - `in_app` — stored in inbox only, no external dispatch

    Returns `{ sent, failed }` counts.
    """
    result = await notification_service.send_notification(data, db)
    return APIResponse.success(message=result["message"], data=result)


# ── 8. GET PREFERENCES ────────────────────────────────────────
@router.get(
    "/preferences",
    response_model=APIResponse,
    summary="Get notification preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Get the current user's notification channel preferences.
    Preferences are auto-created with all channels enabled if not set before.
    """
    prefs = await notification_service.get_preferences(current_user, db)
    return APIResponse.success(
        message="Preferences fetched",
        data=PreferenceResponse.model_validate(prefs).model_dump(),
    )


# ── 9. UPDATE PREFERENCES ─────────────────────────────────────
@router.put(
    "/preferences",
    response_model=APIResponse,
    summary="Update notification preferences",
)
async def update_preferences(
    data: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Update notification channel and type preferences.
    Only fields included in the request body are changed — omitted fields keep their current value.

    **Channel toggles:** push_enabled, sms_enabled, email_enabled

    **Type toggles (inside type_preferences):**
    - `promotions`      — deals and special offers
    - `reminders`       — darshan slot and trip reminders
    - `booking_updates` — confirmations, cancellations, status changes
    - `system`          — account and security alerts (cannot be disabled)
    """
    prefs = await notification_service.update_preferences(data, current_user, db)
    return APIResponse.success(
        message="Preferences updated",
        data=PreferenceResponse.model_validate(prefs).model_dump(),
    )
