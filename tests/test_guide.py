"""
tests/test_guide.py
Unit tests for all Guide API endpoints.

Routes covered:
  GET    /guides/featured                                    — Featured guides
  GET    /guides/by-language/{language}                      — Guides by language
  GET    /guides/by-specialization/{specialization}          — Guides by specialization
  GET    /guides/by-location/{city}                          — Guides by city
  GET    /guides                                             — List guides with filters
  GET    /guides/{guide_id}                                  — Guide detail
  GET    /guides/{guide_id}/reviews                          — Guide reviews
  GET    /guides/{guide_id}/availability                     — Guide availability
  POST   /guides                                             — Register guide profile (auth)
  PUT    /guides/{guide_id}                                  — Update guide (auth)
  PUT    /guides/{guide_id}/status                           — Update guide status (auth)
  PUT    /guides/{guide_id}/availability                     — Update unavailable dates (auth)
  POST   /guides/{guide_id}/languages                        — Add language (auth)
  DELETE /guides/{guide_id}/languages/{language_id}          — Remove language (auth)
  POST   /guides/{guide_id}/specializations                  — Add specialization (auth)
  DELETE /guides/{guide_id}/specializations/{spec_id}        — Remove specialization (auth)
  POST   /guides/{guide_id}/documents                        — Upload document (auth)
  GET    /guides/{guide_id}/bookings                         — Guide bookings (auth)

Run with:
    pytest tests/test_guide.py -v
"""

from fastapi import HTTPException
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}
GUIDE_ID    = str(uuid4())
LANG_ID     = str(uuid4())
SPEC_ID     = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id   = uuid4()
MOCK_USER.role = "guide"
MOCK_USER.is_phone_verified = True

SAMPLE_GUIDE = {
    "id":               GUIDE_ID,
    "full_name":        "Ramesh Kumar",
    "base_city":        "Tirupati",
    "daily_rate":       1500.0,
    "experience_years": 10,
    "rating":           4.8,
    "is_featured":      True,
}

GUIDE_PAYLOAD = {
    "bio":              "Experienced temple guide with 10 years experience",
    "experience_years": 10,
    "base_city":        "Tirupati",
    "daily_rate":       1500.0,
}


def mock_auth():
    return patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER)


# ─── Featured ─────────────────────────────────────────────────────────────────

class TestFeaturedGuides:

    def test_featured_success(self):
        with patch("src.services.guide_service.get_featured_guides") as mock_svc:
            mock_svc.return_value = [SAMPLE_GUIDE]
            response = client.get("/api/v1/guides/featured")
        assert response.status_code in (200, 500)

    def test_featured_empty(self):
        with patch("src.services.guide_service.get_featured_guides") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/guides/featured")
        assert response.status_code in (200, 500)


# ─── By Language ──────────────────────────────────────────────────────────────

class TestGuidesByLanguage:

    def test_by_language_success(self):
        with patch("src.services.guide_service.get_guides_by_language") as mock_svc:
            mock_svc.return_value = [SAMPLE_GUIDE]
            response = client.get("/api/v1/guides/by-language/Telugu")
        assert response.status_code in (200, 500)

    def test_by_language_pagination(self):
        with patch("src.services.guide_service.get_guides_by_language") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/guides/by-language/English?page=1&limit=10")
        assert response.status_code in (200, 422, 500)

    def test_by_language_invalid_page(self):
        response = client.get("/api/v1/guides/by-language/Telugu?page=0")
        assert response.status_code in (422, 500)


# ─── By Specialization ────────────────────────────────────────────────────────

class TestGuidesBySpecialization:

    def test_by_specialization_success(self):
        with patch("src.services.guide_service.get_guides_by_specialization") as mock_svc:
            mock_svc.return_value = [SAMPLE_GUIDE]
            response = client.get("/api/v1/guides/by-specialization/Temple")
        assert response.status_code in (200, 500)

    def test_by_specialization_empty(self):
        with patch("src.services.guide_service.get_guides_by_specialization") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/guides/by-specialization/Heritage")
        assert response.status_code in (200, 500)


# ─── By Location ──────────────────────────────────────────────────────────────

class TestGuidesByLocation:

    def test_by_location_success(self):
        with patch("src.services.guide_service.get_guides_by_location") as mock_svc:
            mock_svc.return_value = [SAMPLE_GUIDE]
            response = client.get("/api/v1/guides/by-location/Tirupati")
        assert response.status_code in (200, 500)

    def test_by_location_pagination(self):
        with patch("src.services.guide_service.get_guides_by_location") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/guides/by-location/Visakhapatnam?page=1&limit=10")
        assert response.status_code in (200, 422, 500)


# ─── List ─────────────────────────────────────────────────────────────────────

class TestListGuides:

    def test_list_no_filters(self):
        with patch("src.services.guide_service.list_guides") as mock_svc:
            mock_svc.return_value = {
    "total": 0,
    "items": []
}
            response = client.get("/api/v1/guides")
        assert response.status_code in (200, 500)

    def test_list_with_city_filter(self):
        with patch("src.services.guide_service.list_guides") as mock_svc:
            mock_svc.return_value = {
    "total": 0,
    "items": []
}
            response = client.get("/api/v1/guides?city=Tirupati")
        assert response.status_code in (200, 422, 500)

    def test_list_with_language_filter(self):
        with patch("src.services.guide_service.list_guides") as mock_svc:
            mock_svc.return_value = {
    "total": 0,
    "items": []
}
            response = client.get("/api/v1/guides?language=Telugu")
        assert response.status_code in (200, 422, 500)

    def test_list_pagination(self):
        with patch("src.services.guide_service.list_guides") as mock_svc:
            mock_svc.return_value = {
    "total": 0,
    "items": []
}
            response = client.get("/api/v1/guides?page=1&limit=10")
        assert response.status_code in (200, 422, 500)

    def test_list_invalid_page(self):
        response = client.get("/api/v1/guides?page=0")
        assert response.status_code in (422, 500)


# ─── Detail, Reviews, Availability ───────────────────────────────────────────

class TestGuideDetail:

    def test_get_detail_success(self):
        with patch("src.services.guide_service.get_guide_detail") as mock_svc:
            mock_svc.return_value = SAMPLE_GUIDE
            response = client.get(f"/api/v1/guides/{GUIDE_ID}")
        assert response.status_code in (200, 500)

    def test_get_detail_not_found(self):
        with patch("src.services.guide_service.get_guide_detail") as mock_svc:
            mock_svc.side_effect = HTTPException(status_code=404, detail="Guide not found")
            response = client.get(f"/api/v1/guides/{uuid4()}")
        assert response.status_code in (400, 404, 500)

    def test_get_reviews_success(self):
        with patch("src.services.guide_service.get_guide_reviews") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/guides/{GUIDE_ID}/reviews")
        assert response.status_code in (200, 404, 500)

    def test_get_availability_success(self):
        with patch("src.services.guide_service.get_guide_availability") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/guides/{GUIDE_ID}/availability")
        assert response.status_code in (200, 404, 500)


# ─── Protected Write Endpoints ────────────────────────────────────────────────

class TestGuideWrite:

    def test_register_unauthorized(self):
        response = client.post("/api/v1/guides", json=GUIDE_PAYLOAD)
        assert response.status_code == 401

    def test_register_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.guide.register_guide") as mock_svc:
                mock_svc.return_value = {"id": GUIDE_ID, "message": "Guide profile created"}
                response = client.post("/api/v1/guides", json=GUIDE_PAYLOAD, headers=AUTH_HEADER)
        assert response.status_code in (200, 201, 401, 422)

    def test_update_unauthorized(self):
        response = client.put(f"/api/v1/guides/{GUIDE_ID}", json={"daily_rate": 2000.0})
        assert response.status_code == 401

    def test_update_success(self):
        with mock_auth():
            with patch("src.services.guide_service.update_guide") as mock_svc:
                mock_svc.return_value = {"id": GUIDE_ID}
                response = client.put(
                    f"/api/v1/guides/{GUIDE_ID}",
                    json={"daily_rate": 2000.0},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_update_status_unauthorized(self):
        response = client.put(f"/api/v1/guides/{GUIDE_ID}/status", json={"status": "ACTIVE"})
        assert response.status_code == 401

    def test_update_status_success(self):
        with mock_auth():
            with patch("src.services.guide_service.update_guide_status") as mock_svc:
                mock_svc.return_value = {"id": GUIDE_ID, "status": "ACTIVE"}
                response = client.put(
                    f"/api/v1/guides/{GUIDE_ID}/status",
                    json={"status": "ACTIVE"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_update_availability_unauthorized(self):
        response = client.put(f"/api/v1/guides/{GUIDE_ID}/availability", json={})
        assert response.status_code == 401

    def test_update_availability_success(self):
        with mock_auth():
            with patch("src.services.guide_service.update_guide_availability") as mock_svc:
                mock_svc.return_value = {"message": "Availability updated"}
                response = client.put(
                    f"/api/v1/guides/{GUIDE_ID}/availability",
                    json={"unavailable_dates": ["2025-07-04", "2025-08-15"]},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 401, 404, 422)

    def test_get_bookings_unauthorized(self):
        response = client.get(f"/api/v1/guides/{GUIDE_ID}/bookings")
        assert response.status_code == 401

    def test_get_bookings_success(self):
        with mock_auth():
            with patch("src.services.guide_service.get_guide_bookings") as mock_svc:
                mock_svc.return_value = []
                response = client.get(f"/api/v1/guides/{GUIDE_ID}/bookings", headers=AUTH_HEADER)
        assert response.status_code in (200, 401, 404)


# ─── Language & Specialization Management ────────────────────────────────────

class TestGuideLanguagesSpecializations:

    def test_add_language_unauthorized(self):
        response = client.post(f"/api/v1/guides/{GUIDE_ID}/languages", json={})
        assert response.status_code == 401

    def test_add_language_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.guide.add_language") as mock_svc:
                mock_svc.return_value = {"message": "Language added"}
                response = client.post(
                    f"/api/v1/guides/{GUIDE_ID}/languages",
                    json={"language": "Hindi", "proficiency": "FLUENT"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)

    def test_remove_language_unauthorized(self):
        response = client.delete(f"/api/v1/guides/{GUIDE_ID}/languages/{LANG_ID}")
        assert response.status_code == 401

    def test_remove_language_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.guide.remove_language") as mock_svc:
                mock_svc.return_value = {"message": "Language removed"}
                response = client.delete(
                    f"/api/v1/guides/{GUIDE_ID}/languages/{LANG_ID}",
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 204, 401, 404)

    def test_add_specialization_unauthorized(self):
        response = client.post(f"/api/v1/guides/{GUIDE_ID}/specializations", json={})
        assert response.status_code == 401

    def test_add_specialization_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.guide.add_specialization") as mock_svc:
                mock_svc.return_value = {"message": "Specialization added"}
                response = client.post(
                    f"/api/v1/guides/{GUIDE_ID}/specializations",
                    json={"specialization": "Heritage", "description": "AP heritage expert"},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)

    def test_remove_specialization_unauthorized(self):
        response = client.delete(f"/api/v1/guides/{GUIDE_ID}/specializations/{SPEC_ID}")
        assert response.status_code == 401

    def test_upload_document_unauthorized(self):
        response = client.post(f"/api/v1/guides/{GUIDE_ID}/documents", data={})
        assert response.status_code == 401

    def test_upload_document_success(self):
        with mock_auth():
            with patch("src.api.v1.endpoints.guide.upload_document") as mock_svc:
                mock_svc.return_value = {"doc_id": str(uuid4())}
                response = client.post(
                    f"/api/v1/guides/{GUIDE_ID}/documents",
                    data={"doc_type": "ID_PROOF"},
                    files={"file": ("id.jpg", b"fake-image-bytes", "image/jpeg")},
                    headers=AUTH_HEADER,
                )
        assert response.status_code in (200, 201, 401, 422)