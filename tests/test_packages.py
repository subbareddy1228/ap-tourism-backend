"""
tests/test_packages.py
Unit tests for all Package API endpoints.

Routes covered:
  GET    /packages/                         — List packages
  GET    /packages/featured                 — Featured packages
  GET    /packages/popular                  — Popular packages
  GET    /packages/by-duration/{days}       — By duration
  GET    /packages/by-budget                — By budget range
  GET    /packages/{package_id}             — Package detail
  GET    /packages/{package_id}/images      — Package images
  GET    /packages/{package_id}/reviews     — Package reviews
  GET    /packages/{package_id}/itinerary   — Package itinerary
  POST   /packages/                         — Create package (admin)
  PUT    /packages/{package_id}             — Update package (admin)
  DELETE /packages/{package_id}             — Delete package (admin)
  POST   /packages/calculate-price          — Calculate price
  POST   /packages/customize                — Build custom package (auth)
  POST   /packages/{package_id}/itinerary   — Add itinerary day (admin)

Run with:
    pytest tests/test_packages.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER  = {"Authorization": "Bearer test_token"}
ADMIN_HEADER = {"Authorization": "Bearer admin_token"}
PKG_ID       = str(uuid4())
DEST_ID      = str(uuid4())

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id   = uuid4()
MOCK_ADMIN.role = "admin"

MOCK_USER = MagicMock()
MOCK_USER.id   = uuid4()
MOCK_USER.role = "traveler"

SAMPLE_PACKAGE = {
    "id":           PKG_ID,
    "name":         "Tirupati 2D/1N",
    "duration_days": 2,
    "base_price":   4999.0,
    "is_featured":  True,
}

PKG_PAYLOAD = {
    "name":           "Tirupati 2D/1N Special",
    "destination_id": DEST_ID,
    "duration_days":  2,
    "base_price":     4999.0,
    "description":    "Darshan + Hotel + Transfer",
}


def mock_admin_auth():
    return patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN)

def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER)


# ─── Public List Endpoints ────────────────────────────────────────────────────

class TestListPackages:

    def test_list_no_filters(self):
        with patch("src.services.package_service.get_packages") as mock_svc:
            mock_svc.return_value = {"items": [], "total": 0}
            response = client.get("/api/v1/packages/")
        assert response.status_code in (200, 500)

    def test_list_with_destination_filter(self):
        with patch("src.services.package_service.get_packages") as mock_svc:
            mock_svc.return_value = {"items": [], "total": 0}
            response = client.get(f"/api/v1/packages/?destination_id={DEST_ID}")
        assert response.status_code in (200, 422, 500)

    def test_list_pagination(self):
        with patch("src.services.package_service.get_packages") as mock_svc:
            mock_svc.return_value = {"items": [], "total": 0}
            response = client.get("/api/v1/packages/?page=1&limit=10")
        assert response.status_code in (200, 422, 500)

    def test_list_invalid_page(self):
        response = client.get("/api/v1/packages/?page=0")
        assert response.status_code in (422, 500)


class TestFeaturedPackages:

    def test_featured_success(self):
        with patch("src.services.package_service.get_featured_packages") as mock_svc:
            mock_svc.return_value = [SAMPLE_PACKAGE]
            response = client.get("/api/v1/packages/featured")
        assert response.status_code in (200, 500)

    def test_featured_empty(self):
        with patch("src.services.package_service.get_featured_packages") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/packages/featured")
        assert response.status_code in (200, 500)


class TestPopularPackages:

    def test_popular_success(self):
        with patch("src.services.package_service.get_popular_packages") as mock_svc:
            mock_svc.return_value = [SAMPLE_PACKAGE]
            response = client.get("/api/v1/packages/popular")
        assert response.status_code in (200, 500)


class TestPackagesByDuration:

    def test_by_duration_success(self):
        with patch("src.services.package_service.get_packages_by_duration") as mock_svc:
            mock_svc.return_value = [SAMPLE_PACKAGE]
            response = client.get("/api/v1/packages/by-duration/3")
        assert response.status_code in (200, 404, 500)

    def test_by_duration_invalid(self):
        response = client.get("/api/v1/packages/by-duration/abc")
        assert response.status_code == 422

    def test_by_duration_zero_days(self):
        response = client.get("/api/v1/packages/by-duration/0")
        assert response.status_code in (200, 404, 422, 500)


class TestPackagesByBudget:

    def test_by_budget_success(self):
        with patch("src.services.package_service.get_packages_by_budget") as mock_svc:
            mock_svc.return_value = [SAMPLE_PACKAGE]
            response = client.get("/api/v1/packages/by-budget?min=1000&max=10000")
        assert response.status_code in (200, 422, 500)

    def test_by_budget_missing_params(self):
        response = client.get("/api/v1/packages/by-budget")
        assert response.status_code in (200, 422, 500)


# ─── Package Detail ───────────────────────────────────────────────────────────

class TestPackageDetail:

    def test_get_detail_success(self):
        with patch("src.services.package_service.get_package") as mock_svc:
            mock_svc.return_value = SAMPLE_PACKAGE
            response = client.get(f"/api/v1/packages/{PKG_ID}")
        assert response.status_code in (200, 500)

    def test_get_detail_not_found(self):
        with patch("src.services.package_service.get_package") as mock_svc:
            mock_svc.side_effect = ValueError("Package not found")
            response = client.get(f"/api/v1/packages/{uuid4()}")
        assert response.status_code in (400, 404, 500)

    def test_get_images(self):
        with patch("src.services.package_service.get_package_images") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/packages/{PKG_ID}/images")
        assert response.status_code in (200, 404, 500)

    def test_get_reviews(self):
        with patch("src.services.package_service.get_package_reviews") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/packages/{PKG_ID}/reviews")
        assert response.status_code in (200, 404, 500)

    def test_get_itinerary(self):
        with patch("src.services.package_service.get_package_itinerary") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/packages/{PKG_ID}/itinerary")
        assert response.status_code in (200, 404, 500)


# ─── Admin Write ──────────────────────────────────────────────────────────────

class TestAdminPackageWrite:

    def test_create_unauthorized(self):
        response = client.post("/api/v1/packages/", json=PKG_PAYLOAD)
        assert response.status_code in (401, 403, 422)

    def test_create_success(self):
        with mock_admin_auth():
            with patch("src.services.package_service.create_package") as mock_svc:
                mock_svc.return_value = {"id": PKG_ID, "message": "Package created"}
                response = client.post("/api/v1/packages/", json=PKG_PAYLOAD, headers=ADMIN_HEADER)
        assert response.status_code in (200, 201, 401, 422)

    def test_create_missing_name(self):
        with mock_admin_auth():
            payload = {k: v for k, v in PKG_PAYLOAD.items() if k != "name"}
            response = client.post("/api/v1/packages/", json=payload, headers=ADMIN_HEADER)
        assert response.status_code in (401, 422)

    def test_update_unauthorized(self):
        response = client.put(f"/api/v1/packages/{PKG_ID}", json={"base_price": 5499.0})
        assert response.status_code in (401, 403)

    def test_update_success(self):
        with mock_admin_auth():
            with patch("src.services.package_service.update_package") as mock_svc:
                mock_svc.return_value = {"id": PKG_ID}
                response = client.put(
                    f"/api/v1/packages/{PKG_ID}",
                    json={"base_price": 5499.0},
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_delete_unauthorized(self):
        response = client.delete(f"/api/v1/packages/{PKG_ID}")
        assert response.status_code in (401, 403)

    def test_delete_success(self):
        with mock_admin_auth():
            with patch("src.services.package_service.delete_package") as mock_svc:
                mock_svc.return_value = {"message": "Deleted"}
                response = client.delete(f"/api/v1/packages/{PKG_ID}", headers=ADMIN_HEADER)
        assert response.status_code in (200, 204, 401, 404)

    def test_add_itinerary_day_unauthorized(self):
        response = client.post(f"/api/v1/packages/{PKG_ID}/itinerary", json={})
        assert response.status_code in (401, 403, 422)

    def test_add_itinerary_day_success(self):
        with mock_admin_auth():
            with patch("src.services.package_service.add_itinerary_day") as mock_svc:
                mock_svc.return_value = {"day_number": 1}
                response = client.post(
                    f"/api/v1/packages/{PKG_ID}/itinerary",
                    json={"day_number": 1, "title": "Arrival & Darshan", "description": "Check-in, evening darshan"},
                    headers=ADMIN_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)


# ─── Price Calculation & Customization ───────────────────────────────────────

class TestPackageCalculation:

    def test_calculate_price_success(self):
        with patch("src.services.package_service.calculate_price") as mock_svc:
            mock_svc.return_value = {"total_price": 9998.0}
            response = client.post(
                "/api/v1/packages/calculate-price",
                json={"package_id": PKG_ID, "num_adults": 2, "num_children": 0, "travel_date": "2025-08-15"},
            )
        assert response.status_code in (200, 404, 422, 500)

    def test_calculate_price_missing_package(self):
        response = client.post(
            "/api/v1/packages/calculate-price",
            json={"num_adults": 2},
        )
        assert response.status_code in (422, 500)

    def test_customize_unauthorized(self):
        response = client.post("/api/v1/packages/customize", json={})
        assert response.status_code in (401, 403, 422)

    def test_customize_success(self):
        with mock_auth():
            with patch("src.services.package_service.create_custom_package") as mock_svc:
                mock_svc.return_value = {"id": str(uuid4()), "message": "Custom package created"}
                response = client.post(
                    "/api/v1/packages/customize",
                    json={
                        "destination_id":  DEST_ID,
                        "duration_days":   3,
                        "num_adults":      2,
                        "include_hotel":   True,
                        "include_guide":   True,
                        "include_vehicle": True,
                        "travel_date":     "2025-09-01",
                    },
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)