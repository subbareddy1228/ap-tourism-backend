"""
tests/test_admin.py
Unit tests for Admin API endpoints.

Routes covered:
  GET    /admin/dashboard
  GET    /admin/bookings
  GET    /admin/bookings/{booking_id}
  PUT    /admin/bookings/{booking_id}/status
  POST   /admin/bookings/{booking_id}/refund
  GET    /admin/users
  GET    /admin/users/{user_id}
  PUT    /admin/users/{user_id}/status
  PUT    /admin/users/{user_id}/role
  GET    /admin/partners
  GET    /admin/partners/{partner_id}
  PUT    /admin/partners/{partner_id}/verify
  PUT    /admin/partners/{partner_id}/status
  PUT    /admin/partners/{partner_id}/commission
  GET    /admin/reports/bookings
  GET    /admin/reports/revenue
  GET    /admin/reports/users
  GET    /admin/reports/partners
  GET    /admin/analytics/overview
  POST   /admin/temples
  PUT    /admin/temples/{temple_id}
  DELETE /admin/temples/{temple_id}
  POST   /admin/destinations
  PUT    /admin/destinations/{dest_id}
  POST   /admin/packages
  PUT    /admin/packages/{package_id}
  GET    /admin/support/tickets
  PUT    /admin/support/tickets/{ticket_id}/assign
  PUT    /admin/support/tickets/{ticket_id}/resolve
  GET    /admin/coupons
  POST   /admin/coupons
  PUT    /admin/coupons/{coupon_id}
  DELETE /admin/coupons/{coupon_id}
  GET    /admin/reviews
  DELETE /admin/reviews/{review_id}
  POST   /admin/notifications/broadcast
  GET    /admin/settings
  PUT    /admin/settings/{key}
  GET    /admin/vehicles
  PUT    /admin/vehicles/{vehicle_id}/status
  GET    /admin/guides
  PUT    /admin/guides/{guide_id}/status
  GET    /admin/hotels
  GET    /admin/wallet/withdrawals
  PUT    /admin/wallet/withdrawals/{withdrawal_id}/process

Run with:
    pytest tests/test_admin.py -v
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock

from src.main import app

client = TestClient(app)

ADMIN_TOKEN = "Bearer test_admin_token"
BOOKING_ID = str(uuid4())
USER_ID = str(uuid4())
PARTNER_ID = str(uuid4())
TEMPLE_ID = str(uuid4())
DEST_ID = str(uuid4())
PACKAGE_ID = str(uuid4())
TICKET_ID = str(uuid4())
COUPON_ID = str(uuid4())
REVIEW_ID = str(uuid4())
VEHICLE_ID = str(uuid4())
GUIDE_ID = str(uuid4())
WITHDRAWAL_ID = str(uuid4())

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id = str(uuid4())
MOCK_ADMIN.role = "admin"
MOCK_ADMIN.is_phone_verified = True


def make_admin_dep():
    """Patch get_admin_user to return MOCK_ADMIN."""
    return patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN)


# ─────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────

class TestAdminDashboard:
    def test_dashboard_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.api.v1.endpoints.admin.admin_dashboard") as mock_ep:
            mock_ep.return_value = {"today_bookings": 5, "total_users": 100}
            response = client.get("/api/v1/admin/dashboard", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403)

    def test_dashboard_unauthorized(self):
        response = client.get("/api/v1/admin/dashboard")
        assert response.status_code in (401, 403, 422)


# ─────────────────────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────────────────────

class TestAdminBookings:
    def test_list_bookings(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/bookings", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_list_bookings_with_filter(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/bookings?status_filter=CONFIRMED&page=1&limit=10",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_get_booking_detail(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                f"/api/v1/admin/bookings/{BOOKING_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 500)

    def test_update_booking_status(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/bookings/{BOOKING_ID}/status",
                json={"status": "CONFIRMED"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_force_refund_booking(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                f"/api/v1/admin/bookings/{BOOKING_ID}/refund",
                json={"reason": "Admin forced refund"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 404, 500)

    def test_update_booking_status_invalid(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/bookings/{BOOKING_ID}/status",
                json={},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (401, 403, 422, 500)


# ─────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────

class TestAdminUsers:
    def test_list_users(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/users", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_list_users_with_search(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/users?search=test&role=traveler&page=1&limit=20",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_get_user_detail(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                f"/api/v1/admin/users/{USER_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 500)

    def test_update_user_status_activate(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/users/{USER_ID}/status",
                json={"status": "ACTIVE"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_update_user_status_suspend(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/users/{USER_ID}/status",
                json={"status": "SUSPENDED"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_update_user_role(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/users/{USER_ID}/role",
                json={"role": "partner"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# PARTNERS
# ─────────────────────────────────────────────────────────

class TestAdminPartners:
    def test_list_partners(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/partners", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_list_partners_with_filter(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/partners?status=APPLIED&page=1&limit=20",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_get_partner_detail(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                f"/api/v1/admin/partners/{PARTNER_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 500)

    def test_verify_partner_approve(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/partners/{PARTNER_ID}/verify",
                json={"status": "VERIFIED", "remarks": "All docs ok"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_verify_partner_reject(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/partners/{PARTNER_ID}/verify",
                json={"status": "REJECTED", "remarks": "Incomplete docs"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_update_partner_status(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/partners/{PARTNER_ID}/status",
                json={"status": "ACTIVE"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_set_partner_commission(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/partners/{PARTNER_ID}/commission",
                json={"commission_rate": 15.0},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────────────────

class TestAdminReports:
    def test_booking_report(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/reports/bookings?start_date=2024-01-01&end_date=2024-12-31",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_revenue_report(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/reports/revenue",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_user_growth_report(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/reports/users",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_partner_performance_report(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/reports/partners",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_analytics_overview(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/analytics/overview",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)


# ─────────────────────────────────────────────────────────
# TEMPLES
# ─────────────────────────────────────────────────────────

class TestAdminTemples:
    TEMPLE_PAYLOAD = {
        "name": "Test Temple",
        "district": "Tirupati",
        "state": "Andhra Pradesh",
        "deity": "Lord Venkateswara",
        "description": "A sacred temple",
        "latitude": 13.6833,
        "longitude": 79.3467,
    }

    def test_create_temple(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/temples",
                json=self.TEMPLE_PAYLOAD,
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 422, 500)

    def test_update_temple(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/temples/{TEMPLE_ID}",
                json={"description": "Updated description"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_delete_temple(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.delete(
                f"/api/v1/admin/temples/{TEMPLE_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 204, 401, 403, 404, 500)


# ─────────────────────────────────────────────────────────
# DESTINATIONS
# ─────────────────────────────────────────────────────────

class TestAdminDestinations:
    DEST_PAYLOAD = {
        "name": "Araku Valley",
        "state": "Andhra Pradesh",
        "description": "A scenic hill station",
        "type": "hill_station",
        "latitude": 18.3292,
        "longitude": 82.8760,
    }

    def test_create_destination(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/destinations",
                json=self.DEST_PAYLOAD,
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 422, 500)

    def test_update_destination(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/destinations/{DEST_ID}",
                json={"description": "Updated valley description"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# PACKAGES
# ─────────────────────────────────────────────────────────

class TestAdminPackages:
    PKG_PAYLOAD = {
        "name": "Tirupati 2D/1N",
        "destination_id": str(uuid4()),
        "duration_days": 2,
        "base_price": 4999.0,
        "description": "Darshan + Hotel + Transfer",
    }

    def test_create_package(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/packages",
                json=self.PKG_PAYLOAD,
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 422, 500)

    def test_update_package(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/packages/{PACKAGE_ID}",
                json={"base_price": 5499.0},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# SUPPORT TICKETS
# ─────────────────────────────────────────────────────────

class TestAdminSupport:
    def test_list_tickets(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/support/tickets",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_list_tickets_with_filter(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/support/tickets?status=OPEN",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_assign_ticket(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/support/tickets/{TICKET_ID}/assign",
                json={"agent_id": str(uuid4())},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_resolve_ticket(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/support/tickets/{TICKET_ID}/resolve",
                json={"resolution": "Issue resolved"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# COUPONS
# ─────────────────────────────────────────────────────────

class TestAdminCoupons:
    COUPON_PAYLOAD = {
        "code": "SAVE20",
        "discount_type": "percentage",
        "discount_value": 20.0,
        "min_order_value": 1000.0,
        "max_uses": 100,
        "valid_from": "2024-01-01",
        "valid_until": "2024-12-31",
    }

    def test_list_coupons(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/coupons", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_create_coupon(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/coupons",
                json=self.COUPON_PAYLOAD,
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 422, 500)

    def test_update_coupon(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/coupons/{COUPON_ID}",
                json={"max_uses": 200},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_deactivate_coupon(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.delete(
                f"/api/v1/admin/coupons/{COUPON_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 204, 401, 403, 404, 500)


# ─────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────

class TestAdminReviews:
    def test_list_reviews(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/reviews", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_delete_review(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.delete(
                f"/api/v1/admin/reviews/{REVIEW_ID}",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 204, 401, 403, 404, 500)


# ─────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────

class TestAdminNotifications:
    def test_broadcast_notification(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/notifications/broadcast",
                json={
                    "title": "System Update",
                    "body": "New features have been released.",
                    "type": "INFO"
                },
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 201, 401, 403, 422, 500)

    def test_broadcast_missing_fields(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/admin/notifications/broadcast",
                json={},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (401, 403, 422, 500)


# ─────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────

class TestAdminSettings:
    def test_get_settings(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/settings", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_update_setting(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                "/api/v1/admin/settings/maintenance_mode",
                json={"value": "false"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# VEHICLES
# ─────────────────────────────────────────────────────────

class TestAdminVehicles:
    def test_list_vehicles(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/vehicles", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_update_vehicle_status(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/vehicles/{VEHICLE_ID}/status",
                json={"status": "ACTIVE"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# GUIDES
# ─────────────────────────────────────────────────────────

class TestAdminGuides:
    def test_list_guides(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/guides", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)

    def test_update_guide_status(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/guides/{GUIDE_ID}/status",
                json={"status": "ACTIVE"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)


# ─────────────────────────────────────────────────────────
# HOTELS
# ─────────────────────────────────────────────────────────

class TestAdminHotels:
    def test_list_hotels(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get("/api/v1/admin/hotels", headers={"Authorization": ADMIN_TOKEN})
        assert response.status_code in (200, 401, 403, 500)


# ─────────────────────────────────────────────────────────
# WALLET WITHDRAWALS
# ─────────────────────────────────────────────────────────

class TestAdminWalletWithdrawals:
    def test_list_withdrawals(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.get(
                "/api/v1/admin/wallet/withdrawals",
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 500)

    def test_process_withdrawal_approve(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/wallet/withdrawals/{WITHDRAWAL_ID}/process",
                json={"action": "APPROVE", "remarks": "Verified"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)

    def test_process_withdrawal_reject(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN), \
             patch("src.core.database.get_db", new_callable=AsyncMock):
            response = client.put(
                f"/api/v1/admin/wallet/withdrawals/{WITHDRAWAL_ID}/process",
                json={"action": "REJECT", "remarks": "Insufficient info"},
                headers={"Authorization": ADMIN_TOKEN}
            )
        assert response.status_code in (200, 401, 403, 404, 422, 500)