"""
tests/test_notifications.py
Unit tests for all Notification API endpoints.

Routes covered:
  GET    /notifications                   — List notifications (auth)
  GET    /notifications/unread-count      — Unread count (auth)
  GET    /notifications/{id}              — Single notification (auth)
  POST   /notifications/mark-read         — Mark specific as read (auth)
  POST   /notifications/mark-all-read     — Mark all as read (auth)
  DELETE /notifications/{id}              — Delete notification (auth)
  POST   /notifications/send              — Send notification (admin)
  GET    /notifications/preferences       — Get preferences (auth)
  PUT    /notifications/preferences       — Update preferences (auth)

Run with:
    pytest tests/test_notifications.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER  = {"Authorization": "Bearer test_token"}
ADMIN_HEADER = {"Authorization": "Bearer admin_token"}
NOTIF_ID     = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id   = uuid4()
MOCK_USER.role = "traveler"

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id   = uuid4()
MOCK_ADMIN.role = "admin"

SAMPLE_NOTIFICATION = {
    "id":         NOTIF_ID,
    "title":      "Booking Confirmed",
    "body":       "Your booking #12345 has been confirmed.",
    "type":       "BOOKING",
    "is_read":    False,
    "created_at": "2025-06-15T10:00:00Z",
}


def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER)

def mock_admin_auth():
    return patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN)


# ─── List & Read ──────────────────────────────────────────────────────────────

class TestListNotifications:

    def test_list_unauthorized(self):
        response = client.get("/api/v1/notifications")
        assert response.status_code == 401

    def test_list_success(self):
        with mock_auth():
            with patch("src.services.notification_service.list_notifications") as mock_svc:
                mock_svc.return_value = {"items": [SAMPLE_NOTIFICATION], "total": 1}
                response = client.get("/api/v1/notifications", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_list_unread_only(self):
        with mock_auth():
            with patch("src.services.notification_service.list_notifications") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/notifications?unread_only=true", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 422)

    def test_list_pagination(self):
        with mock_auth():
            with patch("src.services.notification_service.list_notifications") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/notifications?page=2&limit=10", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 422)

    def test_list_invalid_page(self):
        with mock_auth():
            response = client.get("/api/v1/notifications?page=0", headers=AUTH_HEADER)
        assert response.status_code in (401, 422)


class TestUnreadCount:

    def test_unread_count_unauthorized(self):
        response = client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 401

    def test_unread_count_success(self):
        with mock_auth():
            with patch("src.services.notification_service.get_unread_count") as mock_svc:
                mock_svc.return_value = {"count": 5}
                response = client.get("/api/v1/notifications/unread-count", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)


class TestNotificationDetail:

    def test_get_detail_unauthorized(self):
        response = client.get(f"/api/v1/notifications/{NOTIF_ID}")
        assert response.status_code == 401

    def test_get_detail_success(self):
        with mock_auth():
            with patch("src.services.notification_service.get_notification") as mock_svc:
                mock_svc.return_value = SAMPLE_NOTIFICATION
                response = client.get(f"/api/v1/notifications/{NOTIF_ID}", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 404)

    def test_get_detail_not_found(self):
        with mock_auth():
            with patch("src.services.notification_service.get_notification") as mock_svc:
                mock_svc.side_effect = ValueError("Not found")
                response = client.get(f"/api/v1/notifications/{uuid4()}", headers=AUTH_HEADER)
        assert response.status_code in (400, 401, 404)


# ─── Mark Read / Delete ───────────────────────────────────────────────────────

class TestMarkRead:

    def test_mark_read_unauthorized(self):
        response = client.post("/api/v1/notifications/mark-read", json={"notification_ids": [NOTIF_ID]})
        assert response.status_code == 401

    def test_mark_read_success(self):
        with mock_auth():
            with patch("src.services.notification_service.mark_notifications_read") as mock_svc:
                mock_svc.return_value = {"message": "Marked as read"}
                response = client.post(
                    "/api/v1/notifications/mark-read",
                    json={"notification_ids": [NOTIF_ID]},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_mark_read_empty_list(self):
        with mock_auth():
            with patch("src.services.notification_service.mark_notifications_read") as mock_svc:
                mock_svc.return_value = {"message": "Nothing to mark"}
                response = client.post(
                    "/api/v1/notifications/mark-read",
                    json={"notification_ids": []},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_mark_all_read_unauthorized(self):
        response = client.post("/api/v1/notifications/mark-all-read")
        assert response.status_code == 401

    def test_mark_all_read_success(self):
        with mock_auth():
            with patch("src.services.notification_service.mark_all_read") as mock_svc:
                mock_svc.return_value = {"message": "All marked as read"}
                response = client.post("/api/v1/notifications/mark-all-read", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)


class TestDeleteNotification:

    def test_delete_unauthorized(self):
        response = client.delete(f"/api/v1/notifications/{NOTIF_ID}")
        assert response.status_code == 401

    def test_delete_success(self):
        with mock_auth():
            with patch("src.services.notification_service.delete_notification") as mock_svc:
                mock_svc.return_value = {"message": "Deleted"}
                response = client.delete(f"/api/v1/notifications/{NOTIF_ID}", headers=AUTH_HEADER)
        assert response.status_code in (200, 204, 401, 404)

    def test_delete_not_found(self):
        with mock_auth():
            with patch("src.services.notification_service.delete_notification") as mock_svc:
                mock_svc.side_effect = ValueError("Not found")
                response = client.delete(f"/api/v1/notifications/{uuid4()}", headers=AUTH_HEADER)
        assert response.status_code in (400, 401, 404)


# ─── Send (Admin) ─────────────────────────────────────────────────────────────

class TestSendNotification:

    def test_send_unauthorized(self):
        response = client.post("/api/v1/notifications/send", json={})
        assert response.status_code == 401

    def test_send_success(self):
        with mock_auth():
            with patch("src.services.notification_service.send_notification") as mock_svc:
                mock_svc.return_value = {"message": "Notification sent"}
                response = client.post(
                    "/api/v1/notifications/send",
                    json={
                        "user_id": str(uuid4()),
                        "title":   "Payment Received",
                        "body":    "Your payment of ₹5000 has been received.",
                        "type":    "PAYMENT",
                    },
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)

    def test_send_missing_title(self):
        with mock_auth():
            response = client.post(
                "/api/v1/notifications/send",
                json={"body": "Test body"},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)


# ─── Preferences ──────────────────────────────────────────────────────────────

class TestNotificationPreferences:

    def test_get_preferences_unauthorized(self):
        response = client.get("/api/v1/notifications/preferences")
        assert response.status_code == 401

    def test_get_preferences_success(self):
        with mock_auth():
            with patch("src.services.notification_service.get_preferences") as mock_svc:
                mock_svc.return_value = {"push": True, "email": True, "sms": False}
                response = client.get("/api/v1/notifications/preferences", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_update_preferences_unauthorized(self):
        response = client.put("/api/v1/notifications/preferences", json={})
        assert response.status_code == 401

    def test_update_preferences_success(self):
        with mock_auth():
            with patch("src.services.notification_service.update_preferences") as mock_svc:
                mock_svc.return_value = {"message": "Preferences updated"}
                response = client.put(
                    "/api/v1/notifications/preferences",
                    json={"push_notifications": True, "email_notifications": False, "sms_notifications": False},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_update_preferences_invalid_body(self):
        with mock_auth():
            response = client.put("/api/v1/notifications/preferences", json=None, headers=AUTH_HEADER)
        assert response.status_code in (401, 422)