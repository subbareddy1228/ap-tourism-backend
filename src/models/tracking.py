"""
models/tracking.py
M18 — Tracking Module

Tables:
    tracking_sessions  — one per active booking (share token, status, timing)
    trip_locations     — latest GPS ping per session  (upserted, O(1) read)
    location_history   — full breadcrumb trail        (append-only)

Branch : feature/LEV156-tracking
Author : LEV156 Ram Kishore Pawar
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


# ── Enums ─────────────────────────────────────────────────────

class TrackingSessionStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    PAUSED    = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TrackerRole(str, enum.Enum):
    DRIVER = "DRIVER"
    GUIDE  = "GUIDE"


# ── Models ────────────────────────────────────────────────────

class TrackingSession(Base):
    """
    One session per booking.  Created by driver/guide when trip begins.
    Holds share_token so traveler can send a read-only link to family.
    """
    __tablename__ = "tracking_sessions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    tracker_id   = Column(UUID(as_uuid=True), nullable=False, index=True)   # driver.id or guide.id
    tracker_role = Column(SAEnum(TrackingSessionStatus), nullable=False)    # overridden below — kept for migration compat
    # NOTE: tracker_role stores TrackerRole values; SAEnum here maps to VARCHAR in DB
    # Use TrackerRole enum in service layer

    status        = Column(SAEnum(TrackingSessionStatus), default=TrackingSessionStatus.ACTIVE, nullable=False)
    share_token   = Column(String(64),  unique=True, nullable=False, index=True)
    share_enabled = Column(Boolean,     default=True)

    trip_started_at   = Column(DateTime(timezone=True), nullable=True)
    trip_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    current_location = relationship(
        "TripLocation", back_populates="session",
        uselist=False, cascade="all, delete-orphan",
    )
    history = relationship(
        "LocationHistory", back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TrackingSession booking={self.booking_id} status={self.status}>"
    
class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class TripLocation(Base):
    """
    Latest known GPS position — exactly ONE row per session.
    The service upserts this row on every ping.
    Keeps live-map reads at O(1) without scanning history.
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

    address = Column(String(500), nullable=True)   # optional reverse-geocoded label

    # ETA fields — recomputed on every ping
    destination_lat       = Column(Float, nullable=True)
    destination_lng       = Column(Float, nullable=True)
    eta_minutes           = Column(Float, nullable=True)
    distance_remaining_km = Column(Float, nullable=True)

    pinged_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("TrackingSession", back_populates="current_location")


class LocationHistory(Base):
    """
    Append-only breadcrumb trail.
    Every ping is archived here for route-replay and distance analytics.
    Rows are NEVER updated.
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
