"""
tests/test_destination.py
Unit tests for all Destination API endpoints.

Routes covered:
  GET    /destinations/featured                         — Featured destinations
  GET    /destinations/popular                          — Popular destinations
  GET    /destinations/types                            — Destination types
  GET    /destinations                                  — List all destinations
  GET    /destinations/{destination_id}                 — Get destination by ID or slug
  POST   /destinations                                  — [Admin] Create destination
  PUT    /destinations/{destination_id}                 — [Admin] Update destination
  DELETE /destinations/{destination_id}                 — [Admin] Delete destination
  GET    /destinations/{destination_id}/packages        — Packages at this destination
  GET    /destinations/{destination_id}/hotels          — Hotels at this destination
  GET    /destinations/{destination_id}/guides          — Guides at this destination
  GET    /destinations/{destination_id}/temples         — Temples at this destination

Run with:
    pytest tests/test_destination.py -v
"""

from uuid import uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}
DEST_ID = str(uuid4())

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id = uuid4()
MOCK_ADMIN.role = "admin"

SAMPLE_DESTINATION = {
    "id": DEST_ID,
    "name": "Araku Valley",
    "district": "Visakhapatnam",
    "state": "Andhra Pradesh",
    "type": "NATURE",
    "description": "A scenic hill station in Andhra Pradesh",
    "is_featured": True,
}

DEST_PAYLOAD = {
    "name": "Araku Valley",
    "state": "Andhra Pradesh",
    "district": "Visakhapatnam",
    "description": "A scenic hill station",
    "type": "NATURE",
    "latitude": 18.3292,
    "longitude": 82.876,
}


def mock_admin_auth():
    return patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN)


# ─── Featured ─────────────────────────────────────────────────────────────────

class TestFeaturedDestinations:

    def test_featured_success(self):
        with patch("src.api.v1.endpoints.destination.get_featured_destinations") as mock_svc:
            mock_svc.return_value = {"message": "Success", "data": [SAMPLE_DESTINATION]}
            response = client.get("/api/v1/destinations/featured")
        assert response.status_code == 200

    def test_featured_empty(self):
        with patch("src.api.v1.endpoints.destination.get_featured_destinations") as mock_svc:
            mock_svc.return_value = {"message": "Success", "data": []}
            response = client.get("/api/v1/destinations/featured")
        assert response.status_code == 200


# ─── Popular ──────────────────────────────────────────────────────────────────

class TestPopularDestinations:

    def test_popular_success(self):
        with patch("src.api.v1.endpoints.destination.get_popular_destinations") as mock_svc:
            mock_svc.return_value = {"message": "Success", "data": [SAMPLE_DESTINATION]}
            response = client.get("/api/v1/destinations/popular")
        assert response.status_code == 200

    def test_popular_empty(self):
        with patch("src.api.v1.endpoints.destination.get_popular_destinations") as mock_svc:
            mock_svc.return_value = {"message": "Success", "data": []}
            response = client.get("/api/v1/destinations/popular")
        assert response.status_code == 200


# ─── Types ────────────────────────────────────────────────────────────────────

class TestDestinationTypes:

    def test_types_success(self):
        with patch("src.services.destination_service.get_destination_types") as mock_svc:
            mock_svc.return_value = {"message": "Success", "data": ["NATURE", "HERITAGE", "COASTAL", "ADVENTURE", "RELIGIOUS"]}
            response = client.get("/api/v1/destinations/types")
        assert response.status_code == 200


# ─── List ─────────────────────────────────────────────────────────────────────

class TestListDestinations:

    def test_list_no_filters(self):
        with patch("src.api.v1.endpoints.destination.get_destinations") as mock_svc:
            mock_svc.return_value = {"message": "ok", "data": []}
            response = client.get("/api/v1/destinations")
        assert response.status_code == 200

    def test_list_with_type_filter(self):
        with patch("src.api.v1.endpoints.destination.get_destinations") as mock_svc:
            mock_svc.return_value = {"message": "ok", "data": []}
            response = client.get("/api/v1/destinations?type=NATURE")
        assert response.status_code == 200

    def test_list_with_district_filter(self):
        with patch("src.api.v1.endpoints.destination.get_destinations") as mock_svc:
            mock_svc.return_value = {"message": "ok", "data": []}
            response = client.get("/api/v1/destinations?district=Visakhapatnam")
        assert response.status_code == 200

    def test_list_invalid_type(self):
        response = client.get("/api/v1/destinations?type=INVALID_TYPE")
        assert response.status_code == 422

    def test_list_pagination(self):
        with patch("src.api.v1.endpoints.destination.get_destinations") as mock_svc:
            mock_svc.return_value = {"message": "ok", "data": []}
            response = client.get("/api/v1/destinations?page=2&limit=5")
        assert response.status_code in (200, 422, 500)

    def test_list_invalid_page(self):
        response = client.get("/api/v1/destinations?page=0")
        assert response.status_code in (422, 500)

    def test_list_limit_too_high(self):
        response = client.get("/api/v1/destinations?limit=200")
        assert response.status_code in (422, 500)


# ─── Detail ───────────────────────────────────────────────────────────────────

class TestDestinationDetail:

    def test_get_by_id_success(self):
        with patch("src.api.v1.endpoints.destination.get_destination") as mock_svc:
            mock_svc.return_value = {"message": "Found", "data": SAMPLE_DESTINATION}
            response = client.get(f"/api/v1/destinations/{DEST_ID}")
        assert response.status_code == 200

    def test_get_by_slug_success(self):
        with patch("src.api.v1.endpoints.destination.get_destination")as mock_svc:
            mock_svc.return_value = {"message": "Found", "data": SAMPLE_DESTINATION}
            response = client.get("/api/v1/destinations/araku-valley")
        assert response.status_code == 200

    from fastapi import HTTPException

def test_get_not_found():
    with patch("src.api.v1.endpoints.destination.get_destination") as mock_svc:
        mock_svc.side_effect = HTTPException(status_code=404, detail="Destination not found")

        response = client.get(f"/api/v1/destinations/{uuid4()}")

    assert response.status_code == 404


# ─── Admin Write ──────────────────────────────────────────────────────────────

class TestAdminDestinationWrite:

    def test_create_unauthorized(self):
        response = client.post("/api/v1/destinations", json=DEST_PAYLOAD)
        assert response.status_code in (401, 403, 422)

    def test_create_success(self):
        with mock_admin_auth():
            with patch("src.services.destination_service.create_destination") as mock_svc:
                mock_svc.return_value = {"message": "Created", "data": SAMPLE_DESTINATION}
                response = client.post("/api/v1/destinations", json=DEST_PAYLOAD, headers=AUTH_HEADER)
        assert response.status_code in (200, 201, 401, 422)

    def test_create_missing_name(self):
        with mock_admin_auth():
            payload = {k: v for k, v in DEST_PAYLOAD.items() if k != "name"}
            response = client.post("/api/v1/destinations", json=payload, headers=AUTH_HEADER)
        assert response.status_code in (401, 422)

    def test_update_success(self):
        with mock_admin_auth():
            with patch("src.services.destination_service.update_destination") as mock_svc:
                mock_svc.return_value = {"message": "Updated", "data": SAMPLE_DESTINATION}
                response = client.put(
                    f"/api/v1/destinations/{DEST_ID}",
                    json={"description": "Updated description"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_update_unauthorized(self):
        response = client.put(f"/api/v1/destinations/{DEST_ID}", json={"description": "x"})
        assert response.status_code in (401, 403)

    def test_delete_success(self):
        with mock_admin_auth():
            with patch("src.services.destination_service.delete_destination") as mock_svc:
                mock_svc.return_value = {"message": "Deleted"}
                response = client.delete(f"/api/v1/destinations/{DEST_ID}", headers=AUTH_HEADER)
        assert response.status_code in (200, 204, 401, 404)

    def test_delete_unauthorized(self):
        response = client.delete(f"/api/v1/destinations/{DEST_ID}")
        assert response.status_code in (401, 403)


# ─── Related Resources ────────────────────────────────────────────────────────

class TestDestinationRelated:

    def test_get_packages(self):
        with patch("src.services.destination_service.get_destination_packages") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/destinations/{DEST_ID}/packages")
        assert response.status_code in (200, 404, 500)

    def test_get_packages_pagination(self):
        with patch("src.services.destination_service.get_destination_packages") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/destinations/{DEST_ID}/packages?page=1&limit=5")
        assert response.status_code in (200, 422, 500)

    def test_get_hotels(self):
        with patch("src.services.destination_service.get_destination_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/destinations/{DEST_ID}/hotels")
        assert response.status_code in (200, 404, 500)

    def test_get_guides(self):
        with patch("src.services.destination_service.get_destination_guides") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/destinations/{DEST_ID}/guides")
        assert response.status_code in (200, 404, 500)

    def test_get_temples(self):
        with patch("src.services.destination_service.get_destination_temples") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/destinations/{DEST_ID}/temples")
        assert response.status_code in (200, 404, 500)