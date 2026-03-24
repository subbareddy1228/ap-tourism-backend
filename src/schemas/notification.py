"""
schemas/notification.py
Pydantic schemas for M14 — Notification APIs.
Owner: LEV156 Ram Kishore Pawar

Request  schemas: SendNotificationRequest, MarkReadRequest, UpdatePreferencesRequest
Response schemas: NotificationResponse, NotificationListResponse,
                  PreferenceResponse, UnreadCountResponse
"""

from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID

from pydantic import BaseModel, field_validator


# ═══════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════

class SendNotificationRequest(BaseModel):
    """
    POST /notifications/send  (admin-only)
    Send a notification to one or more users.
    """
    user_ids:  List[UUID]
    type:      str              # booking_confirmed | promotion | system | etc.
    title:     str
    body:      str
    channel:   str = "push"    # push | sms | email | in_app
    data:      Optional[Dict[str, str]] = None   # deep-link payload

    @field_validator("title")
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        return v

    @field_validator("channel")
    def channel_valid(cls, v: str) -> str:
        allowed = {"push", "sms", "email", "in_app"}
        if v not in allowed:
            raise ValueError(f"channel must be one of {allowed}")
        return v


class MarkReadRequest(BaseModel):
    """
    POST /notifications/mark-read
    Mark specific notifications as read by their IDs.
    """
    notification_ids: List[UUID]

    @field_validator("notification_ids")
    def ids_not_empty(cls, v: List[UUID]) -> List[UUID]:
        if not v:
            raise ValueError("notification_ids cannot be empty")
        return v


class TypePreferencesRequest(BaseModel):
    """Granular per-type toggle map sent inside UpdatePreferencesRequest."""
    promotions:      Optional[bool] = None
    reminders:       Optional[bool] = None
    booking_updates: Optional[bool] = None
    system:          Optional[bool] = None


class UpdatePreferencesRequest(BaseModel):
    """
    PUT /notifications/preferences
    Update channel toggles and per-type settings.
    All fields are optional — only supplied fields are updated.
    """
    push_enabled:     Optional[bool] = None
    sms_enabled:      Optional[bool] = None
    email_enabled:    Optional[bool] = None
    type_preferences: Optional[TypePreferencesRequest] = None


# ═══════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class NotificationResponse(BaseModel):
    """Single notification record returned in list and detail endpoints."""
    id:             UUID
    type:           str
    title:          str
    body:           str
    channel:        str
    is_read:        bool
    data:           Optional[Dict[str, str]]
    created_at:     datetime
    read_at:        Optional[datetime]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """GET /notifications — paginated list."""
    notifications: List[NotificationResponse]
    total:         int
    unread_count:  int
    page:          int
    per_page:      int


class UnreadCountResponse(BaseModel):
    """GET /notifications/unread-count"""
    unread_count: int


class PreferenceResponse(BaseModel):
    """GET /notifications/preferences"""
    push_enabled:     bool
    sms_enabled:      bool
    email_enabled:    bool
    type_preferences: Dict

    class Config:
        from_attributes = True
