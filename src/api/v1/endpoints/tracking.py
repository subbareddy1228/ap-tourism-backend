"""
api/v1/endpoints/tracking.py
M18 — Tracking APIs    prefix: /api/v1/tracking

Endpoints (6 total — matches spec):

  Driver / Guide  (role: guide or admin)
    POST  /tracking/sessions                  — Start tracking session
    POST  /tracking/sessions/{id}/ping        — Send GPS ping
    PUT   /tracking/sessions/{id}/end         — End / complete trip

  Traveler  (any authenticated user)
    GET   /tracking/bookings/{booking_id}     — Live location for my booking
    GET   /tracking/sessions/{id}/history     — Full route breadcrumb
    PUT   /tracking/sessions/{id}/share       — Toggle family share link
    GET   /tracking/sessions/{id}/share       — Get share link URL

  Public  (no auth)
    GET   /tracking/share/{token}             — Family live-location view

  Admin   (role: admin only)
    GET   /tracking/admin/active              — All currently active trips

Pattern follows existing endpoints (wallet, vehicle, bookings):
  - APIResponse.success / .error wrappers
  - ValueError from service → HTTPException in endpoint
  - Depends(get_current_user) / require_role() for auth
  - db: AsyncSession = Depends(get_db) injected per request

Branch : feature/LEV156-tracking
Author : LEV156 Ram Kishore Pawar
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, require_role
from src.models.user import User
from src.schemas.tracking import (
    TrackingSessionCreate,
    LocationPingCreate,
    ShareToggleRequest,
)
from src.common.responses import APIResponse
from src.services import tracking_service

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ══════════════════════════════════════════════════════════════
# DRIVER / GUIDE ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.post(
    "/sessions",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Guide/Driver] Start tracking session",
)
async def start_session(
    data: TrackingSessionCreate,
    current_user: User = Depends(require_role("guide", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by guide or driver when the trip begins.

    - Creates one tracking session per booking (409 if already active).
    - Returns a `share_token` the traveler can use to share with family.
    - `tracker_role` must be `"DRIVER"` or `"GUIDE"`.
    """
    try:
        result = await tracking_service.start_session(
            booking_id      = data.booking_id,
            tracker_id      = current_user.id,
            tracker_role    = data.tracker_role,
            destination_lat = data.destination_lat,
            destination_lng = data.destination_lng,
            db              = db,
        )
        return APIResponse.success(message="Tracking session started", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if "already exists" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/sessions/{session_id}/ping",
    response_model=APIResponse,
    summary="[Guide/Driver] Send GPS ping",
)
async def send_ping(
    session_id: UUID,
    data: LocationPingCreate,
    current_user: User = Depends(require_role("guide", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a GPS coordinate update every 5–10 seconds from the app.

    - Upserts the live location (one row per session).
    - Appends to breadcrumb history.
    - Recalculates ETA using Haversine + reported speed.
    - Send `destination_lat/lng` only when the next stop changes.

    Returns `eta_minutes` and `distance_remaining_km`.
    """
    try:
        result = await tracking_service.process_ping(
            session_id      = session_id,
            tracker_id      = current_user.id,
            latitude        = data.latitude,
            longitude       = data.longitude,
            accuracy        = data.accuracy,
            speed           = data.speed,
            bearing         = data.bearing,
            altitude        = data.altitude,
            destination_lat = data.destination_lat,
            destination_lng = data.destination_lng,
            db              = db,
        )
        return APIResponse.success(message="Location updated", data=result)
    except ValueError as e:
        code = status.HTTP_403_FORBIDDEN if "not the tracker" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(e))


@router.put(
    "/sessions/{session_id}/end",
    response_model=APIResponse,
    summary="[Guide/Driver] End tracking session",
)
async def end_session(
    session_id: UUID,
    current_user: User = Depends(require_role("guide", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark the session COMPLETED when the trip ends.
    Stops accepting further pings for this session.
    """
    try:
        result = await tracking_service.end_session(
            session_id = session_id,
            tracker_id = current_user.id,
            db         = db,
        )
        return APIResponse.success(message="Trip completed. Tracking session closed.", data=result)
    except ValueError as e:
        code = status.HTTP_403_FORBIDDEN if "not the tracker" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(e))


# ══════════════════════════════════════════════════════════════
# TRAVELER ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get(
    "/bookings/{booking_id}",
    response_model=APIResponse,
    summary="[Traveler] Get live location for my booking",
)
async def get_my_trip_location(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current live location + ETA for the given booking.
    Call this every 5–10 seconds to refresh the traveler's map view.
    Returns 404 if no session exists yet (trip not started).
    """
    try:
        result = await tracking_service.get_session_by_booking(booking_id, db)
        return APIResponse.success(message="Live location fetched", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/sessions/{session_id}/history",
    response_model=APIResponse,
    summary="[Traveler] Get full route breadcrumb",
)
async def get_route_history(
    session_id : UUID,
    limit      : int = Query(500, ge=1, le=2000, description="Max breadcrumb points to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the complete GPS trail for route replay on the map.
    Points are ordered oldest → newest.
    Use `limit` to cap the response size (default 500, max 2000).
    """
    try:
        result = await tracking_service.get_history(
            session_id = session_id,
            user_id    = current_user.id,
            db         = db,
            limit      = limit,
        )
        return APIResponse.success(message="Route history fetched", data=result)
    except ValueError as e:
        code = status.HTTP_403_FORBIDDEN if "Access denied" in str(e) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(e))


@router.put(
    "/sessions/{session_id}/share",
    response_model=APIResponse,
    summary="[Traveler] Toggle family share link",
)
async def toggle_share(
    session_id : UUID,
    data       : ShareToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enable or disable the public share link for family tracking.
    When `share_enabled: false`, the share URL returns 403.
    """
    try:
        result = await tracking_service.toggle_share(
            session_id    = session_id,
            share_enabled = data.share_enabled,
            user_id       = current_user.id,
            db            = db,
        )
        msg = "Share link enabled" if data.share_enabled else "Share link disabled"
        return APIResponse.success(message=msg, data=result)
    except ValueError as e:
        code = status.HTTP_403_FORBIDDEN if "Access denied" in str(e) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(e))


@router.get(
    "/sessions/{session_id}/share",
    response_model=APIResponse,
    summary="[Traveler] Get share link details",
)
async def get_share_link(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the share token and full share URL for this session."""
    try:
        session = await tracking_service.get_session_by_id(session_id, db)
        return APIResponse.success(
            message="Share link details",
            data={
                "share_token"  : session["share_token"],
                "share_enabled": session["share_enabled"],
                "share_url"    : f"/api/v1/tracking/share/{session['share_token']}",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINT  (no auth — family share link)
# ══════════════════════════════════════════════════════════════

@router.get(
    "/share/{token}",
    response_model=APIResponse,
    summary="[Public] Live location via share link",
)
async def public_share_view(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    No authentication required.
    Used by family members who receive a share link from the traveler.

    Returns current location + ETA.
    Returns 403 if sharing has been disabled by the traveler.
    Returns 404 if the token is invalid.
    """
    try:
        result = await tracking_service.get_public_tracking_view(token)
        return APIResponse.success(message="Live location", data=result)
    except ValueError as e:
        code = status.HTTP_403_FORBIDDEN if "disabled" in str(e) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(e))


# ══════════════════════════════════════════════════════════════
# ADMIN ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get(
    "/admin/active",
    response_model=APIResponse,
    summary="[Admin] All active tracking sessions",
)
async def admin_active_sessions(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all ACTIVE tracking sessions with current locations.
    Used by the operations dashboard live-map view.
    """
    result = await tracking_service.get_active_sessions(db)
    return APIResponse.success(
        message=f"{len(result)} active sessions",
        data=result,
    )
