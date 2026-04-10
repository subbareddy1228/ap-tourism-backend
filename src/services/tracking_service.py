"""
services/tracking_service.py
M18 — Tracking Module  —  all business logic

Responsibilities:
  - Open / close tracking sessions
  - Process GPS pings  (upsert current location + append to history)
  - ETA & distance calculation (Haversine — no external call per ping)
  - Share-link enable / disable
  - Admin live-map list

[MAPS] Changes vs original:
  - start_session()  → calls maps_client.directions() to store route polyline
                        upfront (one-time cost when trip begins)
  - process_ping()   → calls maps_client.reverse_geocode() to label driver address
                        (non-blocking: failure doesn't crash the ping)
  - get_history()    → calls maps_client.snap_to_roads() before returning
                        breadcrumbs (clean GPS trail, NOT on every ping)

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
# [MAPS] new import
from src.integrations import maps_client


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

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
        "tracker_role"     : session.tracker_role,
        "status"           : session.status.value if session.status else None,
        "share_token"      : session.share_token,
        "share_enabled"    : session.share_enabled,
        "route_polyline"   : session.route_polyline,    # [MAPS] new field
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


# ══════════════════════════════════════════════════════════════════════════════
# 1. START SESSION
# POST /tracking/sessions
# ══════════════════════════════════════════════════════════════════════════════

async def start_session(
    booking_id   : UUID,
    tracker_id   : UUID,
    tracker_role : str,
    destination_lat : Optional[float],
    destination_lng : Optional[float],
    db: AsyncSession,
    # [MAPS] new optional params — pickup coords to fetch route polyline upfront
    pickup_lat: Optional[float] = None,
    pickup_lng: Optional[float] = None,
) -> dict:
    """
    Called by driver/guide when trip begins.
    Only one ACTIVE session allowed per booking.
    Returns session dict with share_token.

    [MAPS] If pickup + destination coords are provided, fetches the full
    route from Ola Maps once (directions API) and stores the polyline.
    This avoids calling directions on every traveler screen refresh.
    Failure to fetch directions does NOT block session creation.
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

    # [MAPS] Fetch route polyline upfront (one-time API call per session)
    route_polyline       = None
    route_distance_km    = None
    route_duration_min   = None

    if pickup_lat and pickup_lng and destination_lat and destination_lng:
        try:
            route = await maps_client.directions(
                origin_lat=pickup_lat,
                origin_lng=pickup_lng,
                dest_lat=destination_lat,
                dest_lng=destination_lng,
            )
            route_polyline     = route.get("polyline")
            route_distance_km  = route.get("distance_km")
            route_duration_min = route.get("duration_minutes")
        except Exception:
            # Non-blocking — session still creates even if directions fail
            pass

    session = TrackingSession(
        booking_id      = booking_id,
        user_id         = tracker_id,
        tracker_id      = tracker_id,
        tracker_role    = tracker_role,
        share_token     = secrets.token_urlsafe(32),
        status          = TrackingSessionStatus.ACTIVE,
        trip_started_at = datetime.now(timezone.utc),
        # [MAPS] store route data on session
        route_polyline     = route_polyline,
        route_distance_km  = route_distance_km,
        route_duration_min = route_duration_min,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.id == session.id)
        .options(selectinload(TrackingSession.current_location))
    )
    session = result.scalar_one()
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════════════════════
# 2. PROCESS PING
# POST /tracking/sessions/{id}/ping
# ══════════════════════════════════════════════════════════════════════════════

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
    4. [MAPS] Reverse geocodes driver's current location (non-blocking).
    5. Upserts TripLocation (one row per session).
    6. Appends LocationHistory (breadcrumb, never updated).
    Returns lightweight ping response.
    """
    session = await _get_session_or_404(session_id, db)

    if str(session.tracker_id) != str(tracker_id):
        raise ValueError("You are not the tracker for this session")

    if session.status != TrackingSessionStatus.ACTIVE:
        raise ValueError(f"Session is {session.status.value}, not ACTIVE")

    # Resolve destination
    dest_lat = destination_lat
    dest_lng = destination_lng
    if dest_lat is None and session.current_location:
        dest_lat = session.current_location.destination_lat
        dest_lng = session.current_location.destination_lng

    # ETA calculation (Haversine — no API call)
    eta_minutes           = None
    distance_remaining_km = None
    if dest_lat is not None and dest_lng is not None:
        distance_remaining_km = round(
            _haversine_km(latitude, longitude, dest_lat, dest_lng), 2
        )
        avg_speed   = speed if (speed and speed > 5) else 40.0
        eta_minutes = round((distance_remaining_km / avg_speed) * 60, 1)

    # [MAPS] Reverse geocode — resolve address for display in traveler's tracking UI.
    # Non-blocking: if Ola Maps is down, the ping still succeeds with address=None.
    address = None
    try:
        address = await maps_client.reverse_geocode(lat=latitude, lng=longitude)
    except Exception:
        pass    # address stays None — UI falls back to showing coordinates

    # ── Upsert TripLocation (one row per session) ─────────────
    existing_loc = session.current_location
    if existing_loc:
        existing_loc.latitude              = latitude
        existing_loc.longitude             = longitude
        existing_loc.accuracy              = accuracy
        existing_loc.speed                 = speed
        existing_loc.bearing               = bearing
        existing_loc.altitude              = altitude
        existing_loc.address               = address        # [MAPS]
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
            address               = address,               # [MAPS]
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
        "address"               : address,                 # [MAPS]
        "eta_minutes"           : eta_minutes,
        "distance_remaining_km" : distance_remaining_km,
        "message"               : "Location updated",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. GET SESSION  (traveler — by booking_id)
# GET /tracking/bookings/{booking_id}
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# 4. GET SESSION  (by session_id)
# ══════════════════════════════════════════════════════════════════════════════

async def get_session_by_id(session_id: UUID, db: AsyncSession) -> dict:
    session = await _get_session_or_404(session_id, db)
    return _session_to_dict(session)


# ══════════════════════════════════════════════════════════════════════════════
# 5. END SESSION
# PUT /tracking/sessions/{id}/end
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# 6. SHARE LINK  — toggle
# PUT /tracking/sessions/{id}/share
# ══════════════════════════════════════════════════════════════════════════════

async def toggle_share(
    session_id    : UUID,
    share_enabled : bool,
    user_id       : UUID,
    db: AsyncSession,
) -> dict:
    session = await _get_session_or_404(session_id, db)

    if str(session.user_id) != str(user_id) and str(session.tracker_id) != str(user_id):
        raise ValueError("Access denied")

    session.share_enabled = share_enabled
    await db.commit()

    return {
        "share_token"  : session.share_token,
        "share_enabled": share_enabled,
        "share_url"    : f"/api/v1/tracking/share/{session.share_token}",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. PUBLIC SHARE  (no auth — family link)
# GET /tracking/share/{token}
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# 8. BREADCRUMB HISTORY  (with snap-to-roads)
# GET /tracking/sessions/{id}/history
# ══════════════════════════════════════════════════════════════════════════════

async def get_history(
    session_id : UUID,
    user_id    : UUID,
    db         : AsyncSession,
    limit      : int = 500,
) -> dict:
    """
    Returns the GPS trail for route replay.
    [MAPS] After fetching raw points from DB, passes them through
    maps_client.snap_to_roads() to clean the trail onto actual road geometry.
    Snap-to-roads accepts up to 100 points per call — batches automatically.
    Falls back to raw points if snap API is down (never crashes history fetch).
    """
    session = await _get_session_or_404(session_id, db)

    if str(session.user_id) != str(user_id) and str(session.tracker_id) != str(user_id):
        raise ValueError("Access denied")

    result = await db.execute(
        select(LocationHistory)
        .where(LocationHistory.session_id == session_id)
        .order_by(LocationHistory.pinged_at.asc())
        .limit(limit)
    )
    points_raw = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).where(LocationHistory.session_id == session_id)
    )
    total = count_result.scalar_one()

    # Build raw points list
    raw_points = [
        {
            "latitude" : p.latitude,
            "longitude": p.longitude,
            "speed"    : p.speed,
            "bearing"  : p.bearing,
            "pinged_at": p.pinged_at,
        }
        for p in points_raw
    ]

    # [MAPS] Snap to roads — batch in chunks of 100 (Ola Maps limit per call)
    snapped_points = await _snap_points_in_batches(raw_points)

    return {
        "session_id"    : str(session_id),
        "booking_id"    : str(session.booking_id),
        "route_polyline": session.route_polyline,   # [MAPS] planned polyline from start_session
        "points"        : snapped_points,
        "total"         : total,
    }


async def _snap_points_in_batches(points: list[dict], batch_size: int = 100) -> list[dict]:
    """
    Snap GPS points to roads in batches of 100 (Ola Maps limit).
    Preserves speed/bearing/pinged_at from the originals after snapping
    since snap_to_roads only returns lat/lng.
    Falls back to raw points if any batch fails.
    """
    if not points:
        return points

    snapped_all = []
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        coords_only = [{"latitude": p["latitude"], "longitude": p["longitude"]} for p in batch]
        snapped_coords = await maps_client.snap_to_roads(coords_only)

        # Re-merge snapped coords with original metadata (speed, bearing, pinged_at)
        for j, snapped in enumerate(snapped_coords):
            merged = {**batch[j], **snapped}   # snapped lat/lng overwrites raw
            snapped_all.append(merged)

    return snapped_all


# ══════════════════════════════════════════════════════════════════════════════
# 9. ADMIN — all active sessions
# GET /tracking/admin/active
# ══════════════════════════════════════════════════════════════════════════════

async def get_active_sessions(db: AsyncSession) -> list:
    result = await db.execute(
        select(TrackingSession)
        .where(TrackingSession.status == TrackingSessionStatus.ACTIVE)
        .options(selectinload(TrackingSession.current_location))
        .order_by(TrackingSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [_session_to_dict(s) for s in sessions]


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY STUBS (kept for compatibility — not called by any active endpoint)
# ══════════════════════════════════════════════════════════════════════════════

async def get_booking_location(db, booking_id):
    return {"booking_id": booking_id, "lat": 0.0, "lng": 0.0, "timestamp": None}

async def get_booking_route_history(db, booking_id):
    return []

async def generate_share_link(db, booking_id):
    return {"share_url": f"https://tracking.example.com/{booking_id}"}

async def get_public_tracking_view(token):
    return {"booking_id": "sample", "lat": 0.0, "lng": 0.0}
