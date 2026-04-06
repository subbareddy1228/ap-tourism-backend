"""
models/tracking.py  —  M18 Tracking Module
Author: LEV156 Ram Kishore Pawar

Changes vs original:
  TrackingSession.tracker_role — was Column(SAEnum(TrackingSessionStatus))
    which is wrong; TrackingSessionStatus has values ACTIVE/PAUSED/COMPLETED/
    CANCELLED — those are session states, not roles.
    Fixed: Column(SAEnum(TrackerRole)) — TrackerRole has DRIVER and GUIDE.
    The original code even had a comment acknowledging the bug.
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class TrackingSessionStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    PAUSED    = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TrackerRole(str, enum.Enum):
    DRIVER = "DRIVER"
    GUIDE  = "GUIDE"


# ── Models ────────────────────────────────────────────────────────────────────

class TrackingSession(Base):
    """
    One session per booking.  Created by driver/guide when trip begins.
    Holds share_token so traveler can share a read-only link with family.
    """
    __tablename__ = "tracking_sessions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    user_id    = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    tracker_id   = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Fixed: was SAEnum(TrackingSessionStatus) — wrong enum entirely.
    tracker_role = Column(SAEnum(TrackerRole), nullable=False)

    status        = Column(SAEnum(TrackingSessionStatus), default=TrackingSessionStatus.ACTIVE, nullable=False)
    share_token   = Column(String(64), unique=True, nullable=False, index=True)
    share_enabled = Column(Boolean,    default=True)

    trip_started_at   = Column(DateTime(timezone=True), nullable=True)
    trip_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    current_location = relationship(
        "TripLocation", back_populates="session",
        uselist=False, cascade="all, delete-orphan",
    )
    history = relationship(
        "LocationHistory", back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TrackingSession booking={self.booking_id} role={self.tracker_role} status={self.status}>"


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id          = Column(Integer,  primary_key=True, index=True)
    event_type  = Column(String,   nullable=False)
    description = Column(String,   nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TrackingEvent {self.event_type}>"


class TripLocation(Base):
    """
    Latest known GPS position — exactly ONE row per session.
    The service upserts this row on every ping so live-map reads are O(1).
    """
    __tablename__ = "trip_locations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracking_sessions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    latitude  = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy  = Column(Float, nullable=True)   # metres
    speed     = Column(Float, nullable=True)   # km/h
    bearing   = Column(Float, nullable=True)   # 0–360°
    altitude  = Column(Float, nullable=True)   # metres above sea level
    address   = Column(String(500), nullable=True)

    destination_lat       = Column(Float, nullable=True)
    destination_lng       = Column(Float, nullable=True)
    eta_minutes           = Column(Float, nullable=True)
    distance_remaining_km = Column(Float, nullable=True)

    pinged_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("TrackingSession", back_populates="current_location")

    def __repr__(self) -> str:
        return f"<TripLocation lat={self.latitude} lng={self.longitude}>"


class LocationHistory(Base):
    """
    Append-only breadcrumb trail — every ping archived here.
    Used for route-replay and distance analytics.  Rows are NEVER updated.
    """
    __tablename__ = "location_history"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracking_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    latitude  = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy  = Column(Float, nullable=True)
    speed     = Column(Float, nullable=True)
    bearing   = Column(Float, nullable=True)
    altitude  = Column(Float, nullable=True)

    pinged_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("TrackingSession", back_populates="history")

    __table_args__ = (
        Index("ix_location_history_session_pinged", "session_id", "pinged_at"),
    )

    def __repr__(self) -> str:
        return f"<LocationHistory session={self.session_id} pinged={self.pinged_at}>"