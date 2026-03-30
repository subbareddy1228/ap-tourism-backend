"""
websockets/tracking.py
Real-time GPS tracking WebSocket endpoint.
Drivers/guides send location pings → travellers receive live updates.

WebSocket URL:
    ws://localhost:8000/api/v1/ws/tracking/{session_id}?token=<JWT>

Flow:
    1. Driver/Guide connects with share_token
    2. Sends GPS pings: {"lat": 13.6, "lng": 79.4, "speed": 45}
    3. Server broadcasts location to all travellers watching same session
    4. Travellers connect with booking_id to watch live location
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.websockets.manager import manager
from src.core.security import decode_token
from src.models.tracking import TrackingSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/tracking/{share_token}")
async def tracking_websocket(
    websocket: WebSocket,
    share_token: str,
    token: str = Query(..., description="JWT access token"),
):
    """
    Real-time tracking WebSocket.

    - Tracker (driver/guide): sends GPS pings
    - Viewer (traveller):     receives live location updates

    Message format (tracker sends):
        {"lat": 13.628, "lng": 79.419, "speed": 45, "heading": 180}

    Message format (viewer receives):
        {"type": "location", "lat": 13.628, "lng": 79.419, "speed": 45,
         "heading": 180, "session_id": "...", "timestamp": "..."}
    """
    # ── Auth check ─────────────────────────────────────────────
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # ── Connect ────────────────────────────────────────────────
    session_key = f"tracking:{share_token}"
    await manager.connect(websocket, session_key)
    logger.info("Tracking WS connected user_id=%s share_token=%s", user_id, share_token)

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            # ── Validate payload ───────────────────────────────
            lat = data.get("lat")
            lng = data.get("lng")
            if lat is None or lng is None:
                await websocket.send_json({"error": "lat and lng are required"})
                continue

            # ── Broadcast to all viewers of this session ───────
            broadcast_data = {
                "type":        "location_update",
                "lat":         lat,
                "lng":         lng,
                "speed":       data.get("speed"),
                "heading":     data.get("heading"),
                "share_token": share_token,
                "tracker_id":  user_id,
            }

            await manager.broadcast_json(broadcast_data)
            logger.debug("Location broadcast share_token=%s lat=%s lng=%s",
                         share_token, lat, lng)

    except WebSocketDisconnect:
        manager.disconnect(session_key, websocket)
        logger.info("Tracking WS disconnected user_id=%s share_token=%s",
                    user_id, share_token)

        # Notify viewers that tracker disconnected
        await manager.send_json(
            {"type": "tracker_offline", "share_token": share_token},
            session_key,
        )