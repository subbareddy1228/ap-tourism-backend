"""
services/tracking_service.py
M18 — Tracking Module  —  all business logic

Responsibilities:
  - Open / close tracking sessions
  - Process GPS pings  (upsert current location + append to history)
  - ETA & distance calculation (Haversine — no external call per ping)
  - Share-link enable / disable
  - Admin live-map list

Pattern matches existing services (wallet_service, vehicle_service):
  - Pure async functions, db: AsyncSession injected
  - Raises ValueError for business-rule violations
    → endpoint layer converts to HTTPException
  - No .from_orm() — returns plain dict via helper

Branch : feature/LEV156-tracking
Author : LEV156 Ram Kishore Pawar
"""

import secrets
import math
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from src.models.tracking import (
    TrackingSession, TripLocation, LocationHistory,
    TrackingSessionStatus, TrackerRole,
)


# ══════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two GPS coords (Haversine formula)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _session_to_dict(session: TrackingSession) -> dict:
    """Convert ORM session + location into a plain dict (no .from_orm)."""
    loc_dict = None
    loc = session.current_location
    if loc:
        loc_dict = {
            "latitude"              : loc.latitude,
            "longitude"             : loc.longitude,
            "accuracy"              : loc.accuracy,
            "speed"                 : loc.speed,
            "bearing"               : loc.bearing,
            "altitude"              : loc.altitude,
            "address"               : loc.address,
            "eta_minutes"           : loc.eta_minutes,
            "distance_remaining_km" : loc.distance_remaining_km,
            "destination_lat"       : loc.destination_lat,
            "destination_lng"       : loc.destination_lng,
            "pinged_at"             : loc.pinged_at,
        }
    return {
        "id"               : str(session.id),
        "booking_id"       : str(session.booking_id),
        "tracker_role"     : session.tracker_role,      # stored as string in DB
        "status"           : session.status.value if session.status else None,
        "share_token"      : session.share_token,
        "share_enabled"    : session.share_enabled,
        "trip_started_at"  : session.trip_started_at,
        "trip_completed_at": session.trip_completed_at,
        "created_at"       : session.created_at,
        "current_location" : loc_dict,
    }


async def _get_session_or_404(session_id: UUID, db: AsyncSession) -> TrackingSession:
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.id == session_id)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Tracking session not found")
    return session


# ══════════════════════════════════════════════════════════════
# 1. START SESSION
# POST /tracking/sessions
# ══════════════════════════════════════════════════════════════

async def start_session(
    booking_id   : UUID,
    tracker_id   : UUID,
    tracker_role : str,
    destination_lat : Optional[float],
    destination_lng : Optional[float],
    db: AsyncSession,
) -> dict:
    """
    Called by driver/guide when trip begins.
    Only one ACTIVE session allowed per booking.
    Returns session dict with share_token.
    """
    # Check no active session already exists
    result = await db.execute(
        select(TrackingSession)
        .where(
            TrackingSession.booking_id == booking_id,
            TrackingSession.status == TrackingSessionStatus.ACTIVE,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("An active tracking session already exists for this booking")

    session = TrackingSession(
        booking_id   = booking_id,
        user_id      = tracker_id,
        tracker_id   = tracker_id,
        tracker_role = tracker_role,        # "DRIVER" or "GUIDE" string
        share_token  = secrets.token_urlsafe(32),
        status       = TrackingSessionStatus.ACTIVE,
        trip_started_at = datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Eagerly load current_location (None at start)
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.id == session.id)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one()
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════
# 2. PROCESS PING
# POST /tracking/sessions/{id}/ping
# ══════════════════════════════════════════════════════════════

async def process_ping(
    session_id  : UUID,
    tracker_id  : UUID,
    latitude    : float,
    longitude   : float,
    accuracy    : Optional[float],
    speed       : Optional[float],
    bearing     : Optional[float],
    altitude    : Optional[float],
    destination_lat : Optional[float],
    destination_lng : Optional[float],
    db: AsyncSession,
) -> dict:
    """
    Accept a GPS ping.
    1. Validates session ownership and ACTIVE status.
    2. Resolves destination (ping value takes priority; falls back to stored).
    3. Calculates ETA using Haversine + current speed (no external API call).
    4. Upserts TripLocation (one row per session).
    5. Appends LocationHistory (breadcrumb, never updated).
    Returns lightweight ping response.
    """
    session = await _get_session_or_404(session_id, db)

    if str(session.tracker_id) != str(tracker_id):
        raise ValueError("You are not the tracker for this session")

    if session.status != TrackingSessionStatus.ACTIVE:
        raise ValueError(f"Session is {session.status.value}, not ACTIVE")

    # Resolve destination — use ping value first, then stored value
    dest_lat = destination_lat
    dest_lng = destination_lng
    if dest_lat is None and session.current_location:
        dest_lat = session.current_location.destination_lat
        dest_lng = session.current_location.destination_lng

    # ETA calculation
    eta_minutes           = None
    distance_remaining_km = None
    if dest_lat is not None and dest_lng is not None:
        distance_remaining_km = round(
            _haversine_km(latitude, longitude, dest_lat, dest_lng), 2
        )
        # Use reported speed if meaningful, otherwise assume 40 km/h
        avg_speed = speed if (speed and speed > 5) else 40.0
        eta_minutes = round((distance_remaining_km / avg_speed) * 60, 1)

    # ── Upsert TripLocation (one row per session) ─────────────
    existing_loc = session.current_location
    if existing_loc:
        existing_loc.latitude              = latitude
        existing_loc.longitude             = longitude
        existing_loc.accuracy              = accuracy
        existing_loc.speed                 = speed
        existing_loc.bearing               = bearing
        existing_loc.altitude              = altitude
        existing_loc.destination_lat       = dest_lat
        existing_loc.destination_lng       = dest_lng
        existing_loc.eta_minutes           = eta_minutes
        existing_loc.distance_remaining_km = distance_remaining_km
        existing_loc.pinged_at             = datetime.now(timezone.utc)
    else:
        new_loc = TripLocation(
            session_id            = session_id,
            latitude              = latitude,
            longitude             = longitude,
            accuracy              = accuracy,
            speed                 = speed,
            bearing               = bearing,
            altitude              = altitude,
            destination_lat       = dest_lat,
            destination_lng       = dest_lng,
            eta_minutes           = eta_minutes,
            distance_remaining_km = distance_remaining_km,
        )
        db.add(new_loc)

    # ── Append to LocationHistory (breadcrumb) ─────────────────
    db.add(LocationHistory(
        session_id = session_id,
        latitude   = latitude,
        longitude  = longitude,
        accuracy   = accuracy,
        speed      = speed,
        bearing    = bearing,
        altitude   = altitude,
    ))

    await db.commit()

    return {
        "session_id"            : str(session_id),
        "eta_minutes"           : eta_minutes,
        "distance_remaining_km" : distance_remaining_km,
        "message"               : "Location updated",
    }


# ══════════════════════════════════════════════════════════════
# 3. GET SESSION  (traveler — by booking_id)
# GET /tracking/bookings/{booking_id}
# ══════════════════════════════════════════════════════════════

async def get_session_by_booking(booking_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.booking_id == booking_id)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("No tracking session found for this booking")
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════
# 4. GET SESSION  (by session_id)
# GET /tracking/sessions/{id}
# ══════════════════════════════════════════════════════════════

async def get_session_by_id(session_id: UUID, db: AsyncSession) -> dict:
    session = await _get_session_or_404(session_id, db)
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════
# 5. END SESSION
# PUT /tracking/sessions/{id}/end
# ══════════════════════════════════════════════════════════════

async def end_session(session_id: UUID, tracker_id: UUID, db: AsyncSession) -> dict:
    session = await _get_session_or_404(session_id, db)

    if str(session.tracker_id) != str(tracker_id):
        raise ValueError("You are not the tracker for this session")

    if session.status == TrackingSessionStatus.COMPLETED:
        raise ValueError("Session is already completed")

    session.status            = TrackingSessionStatus.COMPLETED
    session.trip_completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)

    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.id == session_id)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one()
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════
# 6. SHARE LINK  — toggle
# PUT /tracking/sessions/{id}/share
# ══════════════════════════════════════════════════════════════

async def toggle_share(
    session_id    : UUID,
    share_enabled : bool,
    user_id       : UUID,
    db: AsyncSession,
) -> dict:
    session = await _get_session_or_404(session_id, db)

    # Only the traveler (user_id) or the tracker can toggle
    if str(session.user_id) != str(user_id) and str(session.tracker_id) != str(user_id):
        raise ValueError("Access denied")

    session.share_enabled = share_enabled
    await db.commit()

    return {
        "share_token"  : session.share_token,
        "share_enabled": share_enabled,
        "share_url"    : f"/api/v1/tracking/share/{session.share_token}",
    }


# ══════════════════════════════════════════════════════════════
# 7. PUBLIC SHARE  (no auth — family link)
# GET /tracking/share/{token}
# ══════════════════════════════════════════════════════════════

async def get_by_share_token(token: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.share_token == token)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Invalid or expired share link")
    if not session.share_enabled:
        raise ValueError("Location sharing has been disabled by the traveler")
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════
# 8. BREADCRUMB HISTORY
# GET /tracking/sessions/{id}/history
# ══════════════════════════════════════════════════════════════

async def get_history(
    session_id : UUID,
    user_id    : UUID,
    db         : AsyncSession,
    limit      : int = 500,
) -> dict:
    session = await _get_session_or_404(session_id, db)

    # Access: traveler or tracker only
    if str(session.user_id) != str(user_id) and str(session.tracker_id) != str(user_id):
        raise ValueError("Access denied")

    result = await db.execute(
        select(LocationHistory)
        .where(LocationHistory.session_id == session_id)
        .order_by(LocationHistory.pinged_at.asc())
        .limit(limit)
    )
    points_raw = result.scalars().all()

    # Total count (separate query)
    count_result = await db.execute(
        select(func.count()).where(LocationHistory.session_id == session_id)
    )
    total = count_result.scalar_one()

    points = [
        {
            "latitude" : p.latitude,
            "longitude": p.longitude,
            "speed"    : p.speed,
            "bearing"  : p.bearing,
            "pinged_at": p.pinged_at,
        }
        for p in points_raw
    ]

    return {
        "session_id": str(session_id),
        "booking_id": str(session.booking_id),
        "points"    : points,
        "total"     : total,
    }


# ══════════════════════════════════════════════════════════════
# 9. ADMIN — all active sessions
# GET /tracking/admin/active
# ══════════════════════════════════════════════════════════════

async def get_active_sessions(db: AsyncSession) -> list:
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.status == TrackingSessionStatus.ACTIVE)
        .options(selectinload(TrackingSession.current_location))
        .order_by(TrackingSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [_session_to_dict(s) for s in sessions]
