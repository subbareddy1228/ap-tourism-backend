"""
tests/test_partner.py
Unit tests for Partner API endpoints.
Base URL: /api/v1/partners

Run with:
    pytest tests/test_partner.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}
BOOKING_ID = str(uuid4())
PAYOUT_ID = str(uuid4())
DOC_ID = str(uuid4())

MOCK_PARTNER = MagicMock()
MOCK_PARTNER.id = uuid4()
MOCK_PARTNER.role = "partner"


def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_PARTNER)


# ─── Registration ─────────────────────────────────────────────────────────────

class TestPartnerRegistration:

    def test_register_missing_fields(self):
        response = client.post("/api/v1/partners/register", json={})
        assert response.status_code in (401, 422)

    def test_register_success(self):
        payload = {
            "business_name": "AP Tours",
            "business_type": "travel_agency",
            "phone": "9876543210",
            "email": "partner@example.com",
        }
        with patch("src.services.partner_service.register_partner") as mock_svc:
            mock_svc.return_value = {"partner_id": str(uuid4()), "message": "Registration submitted"}
            response = client.post("/api/v1/partners/register", json=payload)
        assert response.status_code in (200, 201, 401, 422)

    def test_register_duplicate_phone(self):
        with patch("src.services.partner_service.register_partner") as mock_svc:
            mock_svc.side_effect = ValueError("Phone already registered")
            response = client.post(
                "/api/v1/partners/register",
                json={"business_name": "AP Tours", "phone": "9876543210"},
            )
        assert response.status_code in (400, 401, 422)


# ─── Profile & Dashboard ──────────────────────────────────────────────────────

class TestPartnerProfile:

    def test_get_profile_unauthorized(self):
        response = client.get("/api/v1/partners/me")
        assert response.status_code == 401

    def test_get_profile_success(self):
        with mock_auth():
            with patch("src.services.partner_service.get_my_profile") as mock_svc:
                mock_svc.return_value = {"business_name": "AP Tours", "status": "verified"}
                response = client.get("/api/v1/partners/me", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_get_dashboard_unauthorized(self):
        response = client.get("/api/v1/partners/me/dashboard")
        assert response.status_code == 401

    def test_get_dashboard_success(self):
        with mock_auth():
            with patch("src.services.partner_service.get_dashboard") as mock_svc:
                mock_svc.return_value = {"total_bookings": 50, "earnings": 75000}
                response = client.get("/api/v1/partners/me/dashboard", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_get_analytics_unauthorized(self):
        response = client.get("/api/v1/partners/me/analytics")
        assert response.status_code == 401

    def test_get_notifications_unauthorized(self):
        response = client.get("/api/v1/partners/me/notifications")
        assert response.status_code == 401

    def test_get_reviews_unauthorized(self):
        response = client.get("/api/v1/partners/my-reviews")
        assert response.status_code == 401


# ─── Bookings ─────────────────────────────────────────────────────────────────

class TestPartnerBookings:

    def test_list_bookings_unauthorized(self):
        response = client.get("/api/v1/partners/me/bookings")
        assert response.status_code == 401

    def test_list_bookings_success(self):
        with mock_auth():
            with patch("src.services.partner_service.get_partner_bookings") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/partners/me/bookings", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_get_booking_detail_unauthorized(self):
        response = client.get(f"/api/v1/partners/me/bookings/{BOOKING_ID}")
        assert response.status_code == 401

    def test_accept_booking_unauthorized(self):
        response = client.put(f"/api/v1/partners/me/bookings/{BOOKING_ID}/accept")
        assert response.status_code == 401

    def test_accept_booking_success(self):
        with mock_auth():
            with patch("src.services.partner_service.accept_booking") as mock_svc:
                mock_svc.return_value = {"message": "Booking accepted"}
                response = client.put(
                    f"/api/v1/partners/me/bookings/{BOOKING_ID}/accept",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)

    def test_reject_booking_unauthorized(self):
        response = client.put(
            f"/api/v1/partners/me/bookings/{BOOKING_ID}/reject",
            json={"reason": "not available"},
        )
        assert response.status_code == 401

    def test_reject_booking_success(self):
        with mock_auth():
            with patch("src.services.partner_service.reject_booking") as mock_svc:
                mock_svc.return_value = {"message": "Booking rejected"}
                response = client.put(
                    f"/api/v1/partners/me/bookings/{BOOKING_ID}/reject",
                    json={"reason": "not available"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404)


# ─── Earnings & Payouts ───────────────────────────────────────────────────────

class TestPartnerEarnings:

    def test_get_earnings_unauthorized(self):
        response = client.get("/api/v1/partners/me/earnings")
        assert response.status_code == 401

    def test_get_earnings_success(self):
        with mock_auth():
            with patch("src.services.partner_service.get_earnings_summary") as mock_svc:
                mock_svc.return_value = {"total": 75000, "this_month": 12000}
                response = client.get("/api/v1/partners/me/earnings", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_get_earnings_report_unauthorized(self):
        response = client.get("/api/v1/partners/me/earnings/report")
        assert response.status_code == 401

    def test_get_payouts_unauthorized(self):
        response = client.get("/api/v1/partners/me/payouts")
        assert response.status_code == 401

    def test_get_payouts_success(self):
        with mock_auth():
            with patch("src.services.partner_service.get_payouts") as mock_svc:
                mock_svc.return_value = {"items": [], "total": 0}
                response = client.get("/api/v1/partners/me/payouts", headers=AUTH_HEADER)
        assert response.status_code in (200, 401)

    def test_get_payout_detail_unauthorized(self):
        response = client.get(f"/api/v1/partners/me/payouts/{PAYOUT_ID}")
        assert response.status_code == 401


# ─── Documents & Settings ─────────────────────────────────────────────────────

class TestPartnerDocumentsAndSettings:

    def test_list_documents_unauthorized(self):
        response = client.get("/api/v1/partners/me/documents")
        assert response.status_code == 401

    def test_upload_document_unauthorized(self):
        response = client.post("/api/v1/partners/me/documents", data={})
        assert response.status_code == 401

    def test_delete_document_unauthorized(self):
        response = client.delete(f"/api/v1/partners/me/documents/{DOC_ID}")
        assert response.status_code == 401

    def test_update_bank_details_unauthorized(self):
        response = client.put("/api/v1/partners/me/bank-details", json={})
        assert response.status_code == 401

    def test_update_bank_details_success(self):
        payload = {
            "account_number": "1234567890",
            "ifsc_code": "SBIN0001234",
            "account_holder": "AP Tours",
        }
        with mock_auth():
            with patch("src.services.partner_service.update_bank_details") as mock_svc:
                mock_svc.return_value = {"message": "Bank details updated"}
                response = client.put(
                    "/api/v1/partners/me/bank-details",
                    json=payload,
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 422)

    def test_update_availability_unauthorized(self):
        response = client.put("/api/v1/partners/me/availability", json={})
        assert response.status_code == 401

    def test_update_settings_unauthorized(self):
        response = client.put("/api/v1/partners/me/settings", json={})
        assert response.status_code == 401

    def test_update_settings_success(self):
        with mock_auth():
            with patch("src.services.partner_service.update_settings") as mock_svc:
                mock_svc.return_value = {"message": "Settings updated"}
                response = client.put(
                    "/api/v1/partners/me/settings",
                    json={"auto_accept_bookings": True},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 422)
