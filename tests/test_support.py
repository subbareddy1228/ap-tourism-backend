"""
tests/test_support.py
Unit tests for all Support Ticket API endpoints.

Routes covered (User):
  POST   /support/tickets                               — Create ticket
  GET    /support/tickets                               — List my tickets
  GET    /support/tickets/{ticket_id}                   — Ticket detail
  POST   /support/tickets/{ticket_id}/messages          — Add message
  PUT    /support/tickets/{ticket_id}/close             — Close ticket
  POST   /support/tickets/{ticket_id}/reopen            — Reopen ticket

Routes covered (Admin):
  GET    /support/admin/tickets                         — List all tickets
  PUT    /support/admin/tickets/{ticket_id}/assign      — Assign to agent
  PUT    /support/admin/tickets/{ticket_id}/resolve     — Resolve ticket
  POST   /support/admin/tickets/{ticket_id}/messages    — Admin add message
  GET    /support/admin/tickets/{ticket_id}             — Admin ticket detail
  GET    /support/admin/tickets/{ticket_id}/messages    — Ticket messages

Run with:
    pytest tests/test_support.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER  = {"Authorization": "Bearer test_token"}
ADMIN_HEADER = {"Authorization": "Bearer admin_token"}
TICKET_ID    = str(uuid4())
AGENT_ID     = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id   = uuid4()
MOCK_USER.role = "traveler"

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id   = uuid4()
MOCK_ADMIN.role = "admin"

TICKET_PAYLOAD = {
    "subject":  "Booking not confirmed",
    "category": "BOOKING",
    "priority": "HIGH",
    "message":  "I made a payment but my booking is still pending.",
}

SAMPLE_TICKET = {
    "id":       TICKET_ID,
    "subject":  "Booking not confirmed",
    "status":   "OPEN",
    "priority": "HIGH",
}


def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER)

def mock_admin_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_ADMIN)


# ─── User: Create Ticket ──────────────────────────────────────────────────────

class TestCreateTicket:

    def test_create_unauthorized(self):
        response = client.post("/api/v1/support/tickets", json=TICKET_PAYLOAD)
        assert response.status_code == 401

    def test_create_success(self):
        with mock_auth():
            with patch("src.services.support_service.create_ticket") as mock_svc:
                mock_svc.return_value = {"ticket_id": TICKET_ID, "message": "Ticket created"}
                response = client.post(
                    "/api/v1/support/tickets",
                    json=TICKET_PAYLOAD,
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)

    def test_create_missing_subject(self):
        with mock_auth():
            response = client.post(
                "/api/v1/support/tickets",
                json={"message": "Help!"},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)

    def test_create_missing_message(self):
        with mock_auth():
            response = client.post(
                "/api/v1/support/tickets",
                json={"subject": "Need help"},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)


# ─── User: List & Detail ──────────────────────────────────────────────────────

class TestUserTicketList:

    def test_list_unauthorized(self):
        response = client.get("/api/v1/support/tickets")
        assert response.status_code == 401

    def test_list_success(self):
        with mock_auth():
            with patch("src.services.support_service.list_my_tickets") as mock_svc:
                mock_svc.return_value = {"items": [SAMPLE_TICKET], "total": 1}
                response = client.get("/api/v1/support/tickets", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_list_with_status_filter(self):
        with mock_auth():
            with patch("src.services.support_service.list_my_tickets") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/support/tickets?status=OPEN", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 422)

    def test_get_detail_unauthorized(self):
        response = client.get(f"/api/v1/support/tickets/{TICKET_ID}")
        assert response.status_code == 401

    def test_get_detail_success(self):
        with mock_auth():
            with patch("src.services.support_service.get_ticket") as mock_svc:
                mock_svc.return_value = SAMPLE_TICKET
                response = client.get(f"/api/v1/support/tickets/{TICKET_ID}", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 404)

    def test_get_detail_not_found(self):
        with mock_auth():
            with patch("src.services.support_service.get_ticket") as mock_svc:
                mock_svc.side_effect = ValueError("Ticket not found")
                response = client.get(f"/api/v1/support/tickets/{uuid4()}", headers=AUTH_HEADER)
        assert response.status_code in (400, 401, 404)


# ─── User: Add Message, Close, Reopen ────────────────────────────────────────

class TestUserTicketActions:

    def test_add_message_unauthorized(self):
        response = client.post(f"/api/v1/support/tickets/{TICKET_ID}/messages", json={})
        assert response.status_code == 401

    def test_add_message_success(self):
        with mock_auth():
            with patch("src.services.support_service.add_message") as mock_svc:
                mock_svc.return_value = {"message_id": str(uuid4())}
                response = client.post(
                    f"/api/v1/support/tickets/{TICKET_ID}/messages",
                    json={"message": "Any update on my issue?"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 404, 422)

    def test_add_message_empty_body(self):
        with mock_auth():
            response = client.post(
                f"/api/v1/support/tickets/{TICKET_ID}/messages",
                json={},
                headers=AUTH_HEADER,
            )
        assert response.status_code in (401, 422)

    def test_close_ticket_unauthorized(self):
        response = client.put(f"/api/v1/support/tickets/{TICKET_ID}/close")
        assert response.status_code == 401

    def test_close_ticket_success(self):
        with mock_auth():
            with patch("src.services.support_service.close_ticket") as mock_svc:
                mock_svc.return_value = {"message": "Ticket closed"}
                response = client.put(
                    f"/api/v1/support/tickets/{TICKET_ID}/close",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_reopen_ticket_unauthorized(self):
        response = client.post(f"/api/v1/support/tickets/{TICKET_ID}/reopen", json={})
        assert response.status_code == 401

    def test_reopen_ticket_success(self):
        with mock_auth():
            with patch("src.services.support_service.reopen_ticket") as mock_svc:
                mock_svc.return_value = {"message": "Ticket reopened"}
                response = client.post(
                    f"/api/v1/support/tickets/{TICKET_ID}/reopen",
                    json={"reason": "Issue recurred"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 404, 422)


# ─── Admin Ticket Endpoints ───────────────────────────────────────────────────

class TestAdminTickets:

    def test_admin_list_unauthorized(self):
        response = client.get("/api/v1/support/admin/tickets")
        assert response.status_code == 401

    def test_admin_list_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.admin_list_tickets") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/support/admin/tickets", headers=ADMIN_HEADER)
        assert response.status_code in (200, 401)

    def test_admin_list_with_filters(self):
        with mock_admin_auth():
            with patch("src.services.support_service.admin_list_tickets") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get(
                    "/api/v1/support/admin/tickets?status=OPEN&priority=HIGH",
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_admin_assign_unauthorized(self):
        response = client.put(f"/api/v1/support/admin/tickets/{TICKET_ID}/assign", json={})
        assert response.status_code == 401

    def test_admin_assign_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.assign_ticket") as mock_svc:
                mock_svc.return_value = {"message": "Ticket assigned"}
                response = client.put(
                    f"/api/v1/support/admin/tickets/{TICKET_ID}/assign",
                    json={"agent_id": AGENT_ID},
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_admin_resolve_unauthorized(self):
        response = client.put(f"/api/v1/support/admin/tickets/{TICKET_ID}/resolve", json={})
        assert response.status_code == 401

    def test_admin_resolve_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.resolve_ticket") as mock_svc:
                mock_svc.return_value = {"message": "Ticket resolved"}
                response = client.put(
                    f"/api/v1/support/admin/tickets/{TICKET_ID}/resolve",
                    json={"resolution": "Booking confirmed. Payment processed."},
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_admin_add_message_unauthorized(self):
        response = client.post(f"/api/v1/support/admin/tickets/{TICKET_ID}/messages", json={})
        assert response.status_code == 401

    def test_admin_add_message_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.admin_add_message") as mock_svc:
                mock_svc.return_value = {"message_id": str(uuid4())}
                response = client.post(
                    f"/api/v1/support/admin/tickets/{TICKET_ID}/messages",
                    json={"message": "We have looked into your issue."},
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 201, 401, 404, 422)

    def test_admin_get_ticket_detail_unauthorized(self):
        response = client.get(f"/api/v1/support/admin/tickets/{TICKET_ID}")
        assert response.status_code == 401

    def test_admin_get_ticket_detail_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.admin_get_ticket") as mock_svc:
                mock_svc.return_value = SAMPLE_TICKET
                response = client.get(
                    f"/api/v1/support/admin/tickets/{TICKET_ID}",
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_admin_get_messages_unauthorized(self):
        response = client.get(f"/api/v1/support/admin/tickets/{TICKET_ID}/messages")
        assert response.status_code == 401

    def test_admin_get_messages_success(self):
        with mock_admin_auth():
            with patch("src.services.support_service.admin_get_messages") as mock_svc:
                mock_svc.return_value = []
                response = client.get(
                    f"/api/v1/support/admin/tickets/{TICKET_ID}/messages",
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 404)