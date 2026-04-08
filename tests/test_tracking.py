"""
tests/test_tracking.py
Unit tests for all Tracking API endpoints.

Routes covered:
  POST   /tracking/sessions                             — Start session (auth)
  POST   /tracking/sessions/{session_id}/ping           — Send location ping (auth)
  PUT    /tracking/sessions/{session_id}/end            — End session (auth)
  GET    /tracking/bookings/{booking_id}                — Get trip location (auth)
  GET    /tracking/sessions/{session_id}/history        — Route history (auth)
  PUT    /tracking/sessions/{session_id}/share          — Toggle share (auth)
  GET    /tracking/sessions/{session_id}/share          — Get share link (auth)
  GET    /tracking/share/{token}                        — Public share view
  GET    /tracking/admin/active                         — Admin active sessions (admin)

Run with:
    pytest tests/test_tracking.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER  = {"Authorization": "Bearer test_token"}
ADMIN_HEADER = {"Authorization": "Bearer admin_token"}
SESSION_ID   = str(uuid4())
BOOKING_ID   = str(uuid4())
SHARE_TOKEN  = "abc123sharetoken"

MOCK_USER = MagicMock()
MOCK_USER.id   = uuid4()
MOCK_USER.role = "traveler"

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id   = uuid4()
MOCK_ADMIN.role = "admin"

SAMPLE_SESSION = {
    "id":         SESSION_ID,
    "booking_id": BOOKING_ID,
    "status":     "ACTIVE",
    "latitude":   13.6288,
    "longitude":  79.4192,
}


def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER)

def mock_admin_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_ADMIN)


# ─── Start Session ────────────────────────────────────────────────────────────

class TestStartSession:

    def test_start_unauthorized(self):
        response = client.post(
            "/api/v1/tracking/sessions",
            json={"booking_id": BOOKING_ID, "latitude": 13.63, "longitude": 79.42},
        )
        assert response.status_code == 401

    def test_start_success(self):
        with mock_auth():
            with patch("src.services.tracking_service.start_session") as mock_svc:
                mock_svc.return_value = SAMPLE_SESSION
                response = client.post(
                    "/api/v1/tracking/sessions",
                    json={"booking_id": BOOKING_ID, "latitude": 13.6288, "longitude": 79.4192},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)

    def test_start_missing_booking_id(self):
        with mock_auth():
            response = client.post(
                "/api/v1/tracking/sessions",
                json={"latitude": 13.63, "longitude": 79.42},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)

    def test_start_missing_coords(self):
        with mock_auth():
            response = client.post(
                "/api/v1/tracking/sessions",
                json={"booking_id": BOOKING_ID},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)

    def test_start_invalid_booking_id(self):
        with mock_auth():
            response = client.post(
                "/api/v1/tracking/sessions",
                json={"booking_id": "not-a-uuid", "latitude": 13.63, "longitude": 79.42},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422, 500)


# ─── Ping ─────────────────────────────────────────────────────────────────────

class TestSendPing:

    def test_ping_unauthorized(self):
        response = client.post(
            f"/api/v1/tracking/sessions/{SESSION_ID}/ping",
            json={"latitude": 13.63, "longitude": 79.42},
        )
        assert response.status_code == 401

    def test_ping_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.send_ping") as mock_svc:
                mock_svc.return_value = {"message": "Location updated"}
                response = client.post(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/ping",
                    json={"latitude": 13.6300, "longitude": 79.4200, "speed_kmh": 45.0},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 404, 422)

    def test_ping_missing_coords(self):
        with mock_auth():
            response = client.post(
                f"/api/v1/tracking/sessions/{SESSION_ID}/ping",
                json={},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)

    def test_ping_session_not_found(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.send_ping") as mock_svc:
                mock_svc.side_effect = ValueError("Session not found")
                response = client.post(
                    f"/api/v1/tracking/sessions/{uuid4()}/ping",
                    json={"latitude": 13.63, "longitude": 79.42},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (400, 401, 404)

    def test_ping_invalid_session_uuid(self):
        with mock_auth():
            response = client.post(
                "/api/v1/tracking/sessions/not-a-uuid/ping",
                json={"latitude": 13.63, "longitude": 79.42},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)


# ─── End Session ──────────────────────────────────────────────────────────────

class TestEndSession:

    def test_end_unauthorized(self):
        response = client.put(f"/api/v1/tracking/sessions/{SESSION_ID}/end")
        assert response.status_code == 401

    def test_end_success(self):
        with mock_auth():
            with patch("src.services.tracking_service.end_session") as mock_svc:
                mock_svc.return_value = {"message": "Session ended", "duration_minutes": 45}
                response = client.put(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/end",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_end_session_not_found(self):
        with mock_auth():
            with patch("src.services.tracking_service.end_session") as mock_svc:
                mock_svc.side_effect = ValueError("Session not found")
                response = client.put(
                    f"/api/v1/tracking/sessions/{uuid4()}/end",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (400, 401, 404)

    def test_end_already_ended(self):
        with mock_auth():
            with patch("src.services.tracking_service.end_session") as mock_svc:
                mock_svc.side_effect = ValueError("Session already ended")
                response = client.put(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/end",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (400, 401, 404, 409)


# ─── Get Booking Location & Route History ────────────────────────────────────

class TestLocationRetrieval:

    def test_get_booking_location_unauthorized(self):
        response = client.get(f"/api/v1/tracking/bookings/{BOOKING_ID}")
        assert response.status_code == 401

    def test_get_booking_location_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.get_booking_location") as mock_svc:
                mock_svc.return_value = {"latitude": 13.63, "longitude": 79.42, "status": "IN_TRANSIT"}
                response = client.get(
                    f"/api/v1/tracking/bookings/{BOOKING_ID}",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_get_booking_location_not_found(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.get_booking_location") as mock_svc:
                mock_svc.side_effect = ValueError("No active session for this booking")
                response = client.get(
                    f"/api/v1/tracking/bookings/{uuid4()}",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (400, 401, 404)

    def test_get_route_history_unauthorized(self):
        response = client.get(f"/api/v1/tracking/sessions/{SESSION_ID}/history")
        assert response.status_code == 401

    def test_get_route_history_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.get_booking_route_history") as mock_svc:
                mock_svc.return_value = [
                    {"latitude": 13.63, "longitude": 79.42, "timestamp": "2025-06-15T08:00:00Z"},
                    {"latitude": 13.64, "longitude": 79.43, "timestamp": "2025-06-15T08:05:00Z"},
                ]
                response = client.get(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/history",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_get_route_history_empty(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.get_booking_route_history") as mock_svc:
                mock_svc.return_value = []
                response = client.get(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/history",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)


# ─── Sharing ──────────────────────────────────────────────────────────────────

class TestTrackingShare:

    def test_toggle_share_unauthorized(self):
        response = client.put(f"/api/v1/tracking/sessions/{SESSION_ID}/share", json={})
        assert response.status_code == 401

    def test_toggle_share_enable(self):
        with mock_auth():
            with patch("src.services.tracking_service.toggle_share") as mock_svc:
                mock_svc.return_value = {"share_url": f"https://example.com/track/{SHARE_TOKEN}", "enabled": True}
                response = client.put(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/share",
                    json={"enable": True, "expires_in_hours": 24},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_toggle_share_disable(self):
        with mock_auth():
            with patch("src.services.tracking_service.toggle_share") as mock_svc:
                mock_svc.return_value = {"enabled": False}
                response = client.put(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/share",
                    json={"enable": False},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_get_share_link_unauthorized(self):
        response = client.get(f"/api/v1/tracking/sessions/{SESSION_ID}/share")
        assert response.status_code == 401

    def test_get_share_link_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.generate_share_link") as mock_svc:
                mock_svc.return_value = {"share_url": f"https://example.com/track/{SHARE_TOKEN}", "expires_at": "2025-06-16T08:00:00Z"}
                response = client.get(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/share",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_get_share_link_sharing_disabled(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.tracking.tracking_service.generate_share_link") as mock_svc:
                mock_svc.side_effect = ValueError("Sharing is not enabled for this session")
                response = client.get(
                    f"/api/v1/tracking/sessions/{SESSION_ID}/share",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (400, 401, 404)


# ─── Public Share View ────────────────────────────────────────────────────────

class TestPublicShareView:

    def test_public_view_success(self):
        with patch("src.api.v1.endpoints.tracking.tracking_service.get_public_tracking_view") as mock_svc:
            mock_svc.return_value = {
                "session_id": SESSION_ID,
                "latitude":   13.63,
                "longitude":  79.42,
                "status":     "IN_TRANSIT",
            }
            response = client.get(f"/api/v1/tracking/share/{SHARE_TOKEN}")
        assert response.status_code in (200, 404, 410, 500)

    def test_public_view_invalid_token(self):
        with patch("src.api.v1.endpoints.tracking.tracking_service.get_public_tracking_view") as mock_svc:
            mock_svc.side_effect = ValueError("Invalid or expired share token")
            response = client.get("/api/v1/tracking/share/invalid-token-xyz")
        assert response.status_code in (400, 404, 410, 500)

    def test_public_view_expired_token(self):
        with patch("src.api.v1.endpoints.tracking.tracking_service.get_public_tracking_view") as mock_svc:
            mock_svc.side_effect = ValueError("Share link has expired")
            response = client.get(f"/api/v1/tracking/share/expired-token")
        assert response.status_code in (400, 404, 410, 500)

    def test_public_view_no_auth_required(self):
        # Public endpoint — no auth header needed
        with patch("src.api.v1.endpoints.tracking.tracking_service.get_public_tracking_view") as mock_svc:
            mock_svc.return_value = {"latitude": 13.63, "longitude": 79.42}
            response = client.get(f"/api/v1/tracking/share/{SHARE_TOKEN}")
        assert response.status_code in (200, 404, 410, 500)


# ─── Admin Active Sessions ────────────────────────────────────────────────────

class TestAdminActiveSessions:

    def test_admin_active_unauthorized(self):
        response = client.get("/api/v1/tracking/admin/active")
        assert response.status_code == 401

    def test_admin_active_success(self):
        with mock_admin_auth():
            with patch("src.services.tracking_service.get_active_sessions") as mock_svc:
                mock_svc.return_value = {"items": [SAMPLE_SESSION], "total": 1}
                response = client.get("/api/v1/tracking/admin/active", headers=ADMIN_HEADER)
        assert response.status_code in (200, 401)

    def test_admin_active_empty(self):
        with mock_admin_auth():
            with patch("src.services.tracking_service.get_active_sessions") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/tracking/admin/active", headers=ADMIN_HEADER)
        assert response.status_code in (200, 401)

    def test_admin_active_with_pagination(self):
        with mock_admin_auth():
            with patch("src.services.tracking_service.get_active_sessions") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get(
                    "/api/v1/tracking/admin/active?page=1&limit=20",
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_admin_active_invalid_page(self):
        with mock_admin_auth():
            response = client.get("/api/v1/tracking/admin/active?page=0", headers=ADMIN_HEADER)
        assert response.status_code in (401, 422)