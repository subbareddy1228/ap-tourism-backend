"""
websockets/manager.py
WebSocket connection manager.
Manages active WebSocket connections per user.
Used by tracking and notifications modules for real-time updates.
"""

import logging
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Usage:
        manager = ConnectionManager()

        # In WebSocket endpoint:
        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                await manager.send_personal(data, user_id)
        except WebSocketDisconnect:
            manager.disconnect(user_id, websocket)
    """

    def __init__(self):
        # user_id → list of active connections (multi-device support)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept connection and register it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("WebSocket connected user_id=%s total=%d",
                    user_id, len(self.active_connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a specific connection."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("WebSocket disconnected user_id=%s", user_id)

    async def send_personal(self, message: str, user_id: str) -> None:
        """Send text message to all connections of a specific user."""
        connections = self.active_connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def send_json(self, data: dict, user_id: str) -> None:
        """Send JSON payload to all connections of a specific user."""
        connections = self.active_connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, message: str) -> None:
        """Send text message to ALL connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal(message, user_id)

    async def broadcast_json(self, data: dict) -> None:
        """Send JSON to ALL connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_json(data, user_id)

    def is_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return bool(self.active_connections.get(user_id))

    @property
    def connected_users(self) -> List[str]:
        """List of all currently connected user IDs."""
        return list(self.active_connections.keys())

    @property
    def total_connections(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(v) for v in self.active_connections.values())


# Global singleton instance
manager = ConnectionManager()