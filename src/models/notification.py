"""
models/notification.py
SQLAlchemy models for M14 — Notification APIs.
Owner: LEV156 Ram Kishore Pawar

Tables:
    notifications              — per-user notification inbox
    notification_preferences   — per-user channel & type toggle settings
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Semantic type — used for filtering and deep-linking on the frontend
    # Values: booking_confirmed | booking_cancelled | payment_success |
    #         darshan_reminder | guide_assigned | otp | promotion | system
    type    = Column(String(50),  nullable=False)

    title   = Column(String(200), nullable=False)
    body    = Column(Text,        nullable=False)

    # Channel this notification was dispatched on
    # Values: push | sms | email | in_app
    channel = Column(String(20),  nullable=False, default="in_app")

    is_read = Column(Boolean, default=False, nullable=False)

    # Optional deep-link payload — e.g. {"booking_id": "uuid", "screen": "BookingDetail"}
    data = Column(JSONB, nullable=True)

    # FCM message_id returned by Firebase — kept for delivery auditing
    fcm_message_id = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at    = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Notification type={self.type} user_id={self.user_id} read={self.is_read}>"


class NotificationPreference(Base):
    """
    Per-user preferences for which channels and notification types are enabled.
    One row per user — upserted on save, not inserted.
    """

    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Channel-level toggles
    push_enabled  = Column(Boolean, default=True,  nullable=False)
    sms_enabled   = Column(Boolean, default=True,  nullable=False)
    email_enabled = Column(Boolean, default=True,  nullable=False)

    # Granular per-type toggles stored as JSONB
    # e.g. {"promotions": false, "reminders": true, "booking_updates": true}
    type_preferences = Column(JSONB, nullable=False, default=dict)

    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<NotificationPreference user_id={self.user_id}>"
