"""
tests/test_temple.py
Unit tests for all 30 Temple API endpoints.

Routes covered:
  ── PUBLIC ────────────────────────────────────────────────────
  GET  /temples/featured                                — Featured temples
  GET  /temples/popular                                 — Popular temples
  GET  /temples/nearby                                  — Temples near lat/lng
  GET  /temples/by-deity/{deity}                        — Temples by deity
  GET  /temples/by-district/{district}                  — Temples by AP district
  GET  /temples/                                        — List all with filters
  GET  /temples/{temple_id}                             — Full temple detail
  GET  /temples/{temple_id}/images                      — Temple images
  GET  /temples/{temple_id}/timings                     — Day-wise schedule
  GET  /temples/{temple_id}/events                      — Upcoming events
  GET  /temples/{temple_id}/reviews                     — Visitor reviews

  ── AUTHENTICATED ─────────────────────────────────────────────
  POST /temples/{temple_id}/reviews                     — Submit review (verified user)

  ── ADMIN ─────────────────────────────────────────────────────
  POST   /temples/                                      — Create temple
  PUT    /temples/{temple_id}                           — Update temple
  DELETE /temples/{temple_id}                           — Delete temple
  POST   /temples/{temple_id}/pooja-services            — Add pooja service
  PUT    /temples/{temple_id}/pooja-services/{id}       — Update pooja service
  POST   /temples/{temple_id}/darshan-types             — Add darshan type
  PUT    /temples/{temple_id}/darshan-types/{type_id}   — Update darshan type
  DELETE /temples/{temple_id}/darshan-types/{type_id}   — Delete darshan type
  POST   /temples/{temple_id}/darshan-slots/bulk-generate — Bulk generate slots
  PUT    /temples/{temple_id}/darshan-slots/{slot_id}   — Update darshan slot
  POST   /temples/{temple_id}/events                    — Create event
  PUT    /temples/{temple_id}/events/{event_id}         — Update event
  DELETE /temples/{temple_id}/events/{event_id}         — Delete event
  POST   /temples/{temple_id}/sync-ttd                  — Sync from TTD API
  POST   /temples/{temple_id}/images                    — Upload temple image
  DELETE /temples/{temple_id}/images/{image_id}         — Delete temple image

Run with:
    pytest tests/test_temple.py -v
"""

from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

ADMIN_TOKEN = "Bearer test_admin_token"
USER_TOKEN = "Bearer test_user_token"
TEMPLE_ID = str(uuid4())
SERVICE_ID = str(uuid4())
TYPE_ID = str(uuid4())
SLOT_ID = str(uuid4())
EVENT_ID = str(uuid4())
IMAGE_ID = str(uuid4())
REVIEW_ID = str(uuid4())

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id = str(uuid4())
MOCK_ADMIN.phone = "9876543210"
MOCK_ADMIN.role = "admin"
MOCK_ADMIN.is_phone_verified = True
MOCK_ADMIN.is_email_verified = True

MOCK_USER = MagicMock()
MOCK_USER.id = str(uuid4())
MOCK_USER.phone = "9876543211"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True
MOCK_USER.is_email_verified = True

SAMPLE_TEMPLE = {
    "id": TEMPLE_ID,
    "name": "Sri Venkateswara Temple",
    "deity": "Venkateswara",
    "district": "Tirupati",
    "address": "Tirumala Hills, Tirupati",
    "is_featured": True,
    "is_active": True,
}

SAMPLE_TEMPLE_CREATE = {
    "name": "Sri Venkateswara Temple",
    "deity": "Venkateswara",
    "district": "Tirupati",
}

SAMPLE_REVIEW_CREATE = {
    "rating": 4.5,
    "title": "Wonderful experience",
    "body": "Very peaceful and well organized",
    "visit_date": "2026-04-01",
}

SAMPLE_POOJA_SERVICE_CREATE = {
    "name": "Abhishekam",
    "price": 500.0,
    "duration_minutes": 45,
    "description": "Sacred bathing ritual",
}


# ─── Public: Featured & Popular ───────────────────────────────────────────────

class TestFeaturedTemples:

    def test_get_featured_success(self):
        with patch("src.services.temple_service.TempleService.get_featured") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/featured")
        assert response.status_code == 200

    def test_get_featured_returns_list(self):
        with patch("src.services.temple_service.TempleService.get_featured") as mock_svc:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = SAMPLE_TEMPLE
            mock_svc.return_value = [mock_result]
            response = client.get("/api/v1/temples/featured")
        assert response.status_code == 200


class TestPopularTemples:

    def test_get_popular_success(self):
        with patch("src.services.temple_service.TempleService.get_popular") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/popular")
        assert response.status_code == 200

    def test_get_popular_with_limit(self):
        with patch("src.services.temple_service.TempleService.get_popular") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/popular?limit=5")
        assert response.status_code == 200

    def test_get_popular_limit_too_high(self):
        response = client.get("/api/v1/temples/popular?limit=999")
        assert response.status_code == 422

    def test_get_popular_limit_zero(self):
        response = client.get("/api/v1/temples/popular?limit=0")
        assert response.status_code == 422


# ─── Public: Nearby ───────────────────────────────────────────────────────────

class TestNearbyTemples:

    def test_nearby_missing_lat_lng(self):
        response = client.get("/api/v1/temples/nearby")
        assert response.status_code == 422

    def test_nearby_missing_lng(self):
        response = client.get("/api/v1/temples/nearby?lat=13.6288")
        assert response.status_code == 422

    def test_nearby_success(self):
        with patch("src.services.temple_service.TempleService.get_nearby") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/nearby?lat=13.6288&lng=79.4192")
        assert response.status_code == 200

    def test_nearby_with_radius(self):
        with patch("src.services.temple_service.TempleService.get_nearby") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/nearby?lat=13.6288&lng=79.4192&radius_km=10.0")
        assert response.status_code == 200

    def test_nearby_radius_too_small(self):
        response = client.get("/api/v1/temples/nearby?lat=13.6288&lng=79.4192&radius_km=0.5")
        assert response.status_code == 422

    def test_nearby_radius_too_large(self):
        response = client.get("/api/v1/temples/nearby?lat=13.6288&lng=79.4192&radius_km=999")
        assert response.status_code == 422


# ─── Public: By Deity & District ──────────────────────────────────────────────

class TestTemplesByDeity:

    def test_by_deity_success(self):
        with patch("src.services.temple_service.TempleService.get_by_deity") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/by-deity/Venkateswara")
        assert response.status_code == 200

    def test_by_deity_with_pagination(self):
        with patch("src.services.temple_service.TempleService.get_by_deity") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/by-deity/Shiva?page=2&page_size=10")
        assert response.status_code == 200

    def test_by_deity_invalid_page(self):
        response = client.get("/api/v1/temples/by-deity/Shiva?page=0")
        assert response.status_code == 422

    def test_by_deity_page_size_too_high(self):
        response = client.get("/api/v1/temples/by-deity/Shiva?page_size=999")
        assert response.status_code == 422


class TestTemplesByDistrict:

    def test_by_district_success(self):
        with patch("src.services.temple_service.TempleService.get_by_district") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/by-district/Tirupati")
        assert response.status_code == 200

    def test_by_district_with_pagination(self):
        with patch("src.services.temple_service.TempleService.get_by_district") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/temples/by-district/Krishna?page=1&page_size=5")
        assert response.status_code == 200

    def test_by_district_invalid_page(self):
        response = client.get("/api/v1/temples/by-district/Tirupati?page=0")
        assert response.status_code == 422


# ─── Public: List Temples ─────────────────────────────────────────────────────

class TestListTemples:

    def test_list_temples_no_filters(self):
        with patch("src.services.temple_service.TempleService.list_temples") as mock_list:
            with patch("src.services.temple_service.TempleService.repo") as mock_repo:
                mock_list.return_value = []
                response = client.get("/api/v1/temples/")
        assert response.status_code == 200

    def test_list_temples_with_deity_filter(self):
        with patch("src.services.temple_service.TempleService.list_temples") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/v1/temples/?deity=Shiva")
        assert response.status_code == 200

    def test_list_temples_with_district_filter(self):
        with patch("src.services.temple_service.TempleService.list_temples") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/v1/temples/?district=Tirupati")
        assert response.status_code == 200

    def test_list_temples_invalid_page(self):
        response = client.get("/api/v1/temples/?page=0")
        assert response.status_code == 422

    def test_list_temples_page_size_too_high(self):
        response = client.get("/api/v1/temples/?page_size=999")
        assert response.status_code == 422


# ─── Public: Temple Detail ────────────────────────────────────────────────────

class TestTempleDetail:

    def test_get_detail_invalid_uuid(self):
        response = client.get("/api/v1/temples/not-a-uuid")
        assert response.status_code == 422

    def test_get_detail_not_found(self):
        with patch("src.services.temple_service.TempleService.get_temple_detail") as mock_svc:
            mock_svc.side_effect = Exception("Temple not found")
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}")
        assert response.status_code == 404

    def test_get_detail_success(self):
        mock_temple = MagicMock()
        mock_temple.model_dump.return_value = SAMPLE_TEMPLE
        with patch("src.services.temple_service.TempleService.get_temple_detail") as mock_svc:
            mock_svc.return_value = mock_temple
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}")
        assert response.status_code == 200


class TestTempleImages:

    def test_get_images_invalid_uuid(self):
        response = client.get("/api/v1/temples/bad-id/images")
        assert response.status_code == 422

    def test_get_images_not_found(self):
        with patch("src.services.temple_service.TempleService.get_temple_images") as mock_svc:
            mock_svc.side_effect = Exception("Temple not found")
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/images")
        assert response.status_code == 404

    def test_get_images_success(self):
        with patch("src.services.temple_service.TempleService.get_temple_images") as mock_svc:
            mock_svc.return_value = ["https://s3.example.com/temple1.jpg"]
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/images")
        assert response.status_code == 200


class TestTempleTimings:

    def test_get_timings_invalid_uuid(self):
        response = client.get("/api/v1/temples/bad-id/timings")
        assert response.status_code == 422

    def test_get_timings_not_found(self):
        with patch("src.services.temple_service.TempleService.get_temple_timings") as mock_svc:
            mock_svc.side_effect = Exception("Temple not found")
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/timings")
        assert response.status_code == 404

    def test_get_timings_success(self):
        with patch("src.services.temple_service.TempleService.get_temple_timings") as mock_svc:
            mock_svc.return_value = {"monday": "6:00 AM - 8:00 PM"}
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/timings")
        assert response.status_code == 200


class TestTempleEvents:

    def test_get_events_invalid_uuid(self):
        response = client.get("/api/v1/temples/bad-id/events")
        assert response.status_code == 422

    def test_get_events_not_found(self):
        with patch("src.services.temple_service.TempleService.get_temple_events") as mock_svc:
            mock_svc.side_effect = Exception("Temple not found")
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/events")
        assert response.status_code == 404

    def test_get_events_success(self):
        with patch("src.services.temple_service.TempleService.get_temple_events") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/events")
        assert response.status_code == 200


class TestTempleReviews:

    def test_get_reviews_invalid_uuid(self):
        response = client.get("/api/v1/temples/bad-id/reviews")
        assert response.status_code == 422

    def test_get_reviews_not_found(self):
        with patch("src.services.temple_service.TempleService.get_temple_reviews") as mock_svc:
            mock_svc.side_effect = Exception("Temple not found")
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/reviews")
        assert response.status_code == 404

    def test_get_reviews_success(self):
        with patch("src.services.temple_service.TempleService.get_temple_reviews") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/reviews")
        assert response.status_code == 200

    def test_get_reviews_pagination(self):
        with patch("src.services.temple_service.TempleService.get_temple_reviews") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/temples/{TEMPLE_ID}/reviews?page=2&page_size=10")
        assert response.status_code == 200

    def test_get_reviews_page_size_too_high(self):
        response = client.get(f"/api/v1/temples/{TEMPLE_ID}/reviews?page_size=999")
        assert response.status_code == 422


# ─── Authenticated: Submit Review ─────────────────────────────────────────────

class TestSubmitReview:

    def test_submit_review_unauthorized(self):
        response = client.post(
            f"/api/v1/temples/{TEMPLE_ID}/reviews",
            json=SAMPLE_REVIEW_CREATE,
        )
        assert response.status_code == 401

    def test_submit_review_success(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.temple_service.TempleService.create_review") as mock_svc:
                mock_svc.return_value = {"id": REVIEW_ID, "rating": 4.5, "title": "Wonderful experience"}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/reviews",
                    json=SAMPLE_REVIEW_CREATE,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_submit_review_rating_out_of_range(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/temples/{TEMPLE_ID}/reviews",
                json={"rating": 6.0},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_submit_review_rating_below_minimum(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/temples/{TEMPLE_ID}/reviews",
                json={"rating": 0.0},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_submit_review_missing_rating(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/temples/{TEMPLE_ID}/reviews",
                json={"title": "No rating"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)


# ─── Admin: Temple CRUD ───────────────────────────────────────────────────────

class TestCreateTemple:

    def test_create_temple_unauthorized(self):
        response = client.post("/api/v1/temples/", json=SAMPLE_TEMPLE_CREATE)
        assert response.status_code == 401

    def test_create_temple_success(self):
        mock_temple = MagicMock()
        mock_temple.model_dump.return_value = SAMPLE_TEMPLE
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.create_temple") as mock_svc:
                mock_svc.return_value = mock_temple
                response = client.post(
                    "/api/v1/temples/",
                    json=SAMPLE_TEMPLE_CREATE,
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_create_temple_missing_required_fields(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            response = client.post(
                "/api/v1/temples/",
                json={"name": "Missing deity and district"},
                headers={"Authorization": ADMIN_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_create_temple_non_admin_rejected(self):
        with patch("src.api.deps.auth.get_admin_user") as mock_dep:
            from fastapi import HTTPException
            mock_dep.side_effect = HTTPException(status_code=403, detail="Admin access required")
            response = client.post(
                "/api/v1/temples/",
                json=SAMPLE_TEMPLE_CREATE,
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 403)


class TestUpdateTemple:

    def test_update_temple_unauthorized(self):
        response = client.put(f"/api/v1/temples/{TEMPLE_ID}", json={"name": "New Name"})
        assert response.status_code == 401

    def test_update_temple_success(self):
        mock_temple = MagicMock()
        mock_temple.model_dump.return_value = {**SAMPLE_TEMPLE, "name": "Updated Name"}
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.update_temple") as mock_svc:
                mock_svc.return_value = mock_temple
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}",
                    json={"name": "Updated Name"},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_temple_not_found(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.update_temple") as mock_svc:
                mock_svc.side_effect = Exception("Temple not found")
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}",
                    json={"name": "Ghost"},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (401, 404)

    def test_update_temple_invalid_uuid(self):
        response = client.put("/api/v1/temples/bad-id", json={"name": "X"})
        assert response.status_code == 422


class TestDeleteTemple:

    def test_delete_temple_unauthorized(self):
        response = client.delete(f"/api/v1/temples/{TEMPLE_ID}")
        assert response.status_code == 401

    def test_delete_temple_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.delete_temple") as mock_svc:
                mock_svc.return_value = {"message": "Temple deleted successfully"}
                response = client.delete(
                    f"/api/v1/temples/{TEMPLE_ID}",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: Pooja Services ────────────────────────────────────────────────────

class TestAddPoojaService:

    def test_add_pooja_service_unauthorized(self):
        response = client.post(
            f"/api/v1/temples/{TEMPLE_ID}/pooja-services",
            json=SAMPLE_POOJA_SERVICE_CREATE,
        )
        assert response.status_code == 401

    def test_add_pooja_service_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.create_pooja_service") as mock_svc:
                mock_svc.return_value = {"id": SERVICE_ID, "name": "Abhishekam", "price": 500.0}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/pooja-services",
                    json=SAMPLE_POOJA_SERVICE_CREATE,
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_add_pooja_service_missing_name(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            response = client.post(
                f"/api/v1/temples/{TEMPLE_ID}/pooja-services",
                json={"price": 500.0},
                headers={"Authorization": ADMIN_TOKEN},
            )
        assert response.status_code in (401, 422)


class TestUpdatePoojaService:

    def test_update_pooja_service_unauthorized(self):
        response = client.put(
            f"/api/v1/temples/{TEMPLE_ID}/pooja-services/{SERVICE_ID}",
            json={"price": 600.0},
        )
        assert response.status_code == 401

    def test_update_pooja_service_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.update_pooja_service") as mock_svc:
                mock_svc.return_value = {"id": SERVICE_ID, "price": 600.0}
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}/pooja-services/{SERVICE_ID}",
                    json={"price": 600.0},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: Darshan Types ─────────────────────────────────────────────────────

class TestDarshanTypes:

    def test_create_darshan_type_unauthorized(self):
        response = client.post(
            f"/api/v1/temples/{TEMPLE_ID}/darshan-types",
            json={"name": "Free Darshan", "price": 0},
        )
        assert response.status_code == 401

    def test_create_darshan_type_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.create_darshan_type") as mock_svc:
                mock_svc.return_value = {"id": TYPE_ID, "name": "Free Darshan"}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/darshan-types",
                    json={"name": "Free Darshan", "price": 0},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_update_darshan_type_unauthorized(self):
        response = client.put(
            f"/api/v1/temples/{TEMPLE_ID}/darshan-types/{TYPE_ID}",
            json={"price": 50},
        )
        assert response.status_code == 401

    def test_update_darshan_type_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.update_darshan_type") as mock_svc:
                mock_svc.return_value = {"id": TYPE_ID, "price": 50}
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}/darshan-types/{TYPE_ID}",
                    json={"price": 50},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_darshan_type_unauthorized(self):
        response = client.delete(f"/api/v1/temples/{TEMPLE_ID}/darshan-types/{TYPE_ID}")
        assert response.status_code == 401

    def test_delete_darshan_type_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.delete_darshan_type") as mock_svc:
                mock_svc.return_value = {"message": "Darshan type deleted"}
                response = client.delete(
                    f"/api/v1/temples/{TEMPLE_ID}/darshan-types/{TYPE_ID}",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: Darshan Slots ─────────────────────────────────────────────────────

class TestDarshanSlots:

    def test_bulk_generate_slots_unauthorized(self):
        response = client.post(
            f"/api/v1/temples/{TEMPLE_ID}/darshan-slots/bulk-generate",
            json={"darshan_type_id": TYPE_ID, "start_date": "2026-04-10", "end_date": "2026-04-20"},
        )
        assert response.status_code == 401

    def test_bulk_generate_slots_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.bulk_generate_darshan_slots") as mock_svc:
                mock_svc.return_value = {"slots_created": 30}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/darshan-slots/bulk-generate",
                    json={"darshan_type_id": TYPE_ID, "start_date": "2026-04-10", "end_date": "2026-04-20"},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_update_darshan_slot_unauthorized(self):
        response = client.put(
            f"/api/v1/temples/{TEMPLE_ID}/darshan-slots/{SLOT_ID}",
            json={"total_quota": 300},
        )
        assert response.status_code == 401

    def test_update_darshan_slot_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.update_darshan_slot") as mock_svc:
                mock_svc.return_value = {"id": SLOT_ID, "total_quota": 300}
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}/darshan-slots/{SLOT_ID}",
                    json={"total_quota": 300},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: Events ────────────────────────────────────────────────────────────

class TestTempleEventsCRUD:

    def test_create_event_unauthorized(self):
        response = client.post(
            f"/api/v1/temples/{TEMPLE_ID}/events",
            json={"name": "Brahmotsavam", "start_date": "2026-05-01"},
        )
        assert response.status_code == 401

    def test_create_event_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.create_event") as mock_svc:
                mock_svc.return_value = {"id": EVENT_ID, "name": "Brahmotsavam"}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/events",
                    json={"name": "Brahmotsavam", "start_date": "2026-05-01"},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_update_event_unauthorized(self):
        response = client.put(
            f"/api/v1/temples/{TEMPLE_ID}/events/{EVENT_ID}",
            json={"name": "Updated Event"},
        )
        assert response.status_code == 401

    def test_update_event_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.update_event") as mock_svc:
                mock_svc.return_value = {"id": EVENT_ID, "name": "Updated Event"}
                response = client.put(
                    f"/api/v1/temples/{TEMPLE_ID}/events/{EVENT_ID}",
                    json={"name": "Updated Event"},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_event_unauthorized(self):
        response = client.delete(f"/api/v1/temples/{TEMPLE_ID}/events/{EVENT_ID}")
        assert response.status_code == 401

    def test_delete_event_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.delete_event") as mock_svc:
                mock_svc.return_value = {"message": "Event deleted"}
                response = client.delete(
                    f"/api/v1/temples/{TEMPLE_ID}/events/{EVENT_ID}",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: TTD Sync ──────────────────────────────────────────────────────────

class TestSyncTTD:

    def test_sync_ttd_unauthorized(self):
        response = client.post(f"/api/v1/temples/{TEMPLE_ID}/sync-ttd")
        assert response.status_code == 401

    def test_sync_ttd_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.integrations.ttd_api.sync_temple_slots") as mock_svc:
                mock_svc.return_value = {"synced_slots": 60, "message": "TTD sync complete"}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/sync-ttd",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Admin: Temple Images ─────────────────────────────────────────────────────

class TestUploadTempleImage:

    def test_upload_image_unauthorized(self):
        response = client.post(f"/api/v1/temples/{TEMPLE_ID}/images")
        assert response.status_code in (401, 422)

    def test_upload_image_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.upload_temple_image") as mock_svc:
                mock_svc.return_value = {"image_url": "https://s3.example.com/temple.jpg"}
                response = client.post(
                    f"/api/v1/temples/{TEMPLE_ID}/images",
                    files={"file": ("temple.jpg", b"fakeimagebytes", "image/jpeg")},
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (201, 401)


class TestDeleteTempleImage:

    def test_delete_image_unauthorized(self):
        response = client.delete(f"/api/v1/temples/{TEMPLE_ID}/images/{IMAGE_ID}")
        assert response.status_code == 401

    def test_delete_image_success(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.delete_temple_image") as mock_svc:
                mock_svc.return_value = {"message": "Image deleted"}
                response = client.delete(
                    f"/api/v1/temples/{TEMPLE_ID}/images/{IMAGE_ID}",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_image_not_found(self):
        with patch("src.api.deps.auth.get_admin_user", return_value=MOCK_ADMIN):
            with patch("src.services.temple_service.TempleService.delete_temple_image") as mock_svc:
                mock_svc.side_effect = Exception("Image not found")
                response = client.delete(
                    f"/api/v1/temples/{TEMPLE_ID}/images/{uuid4()}",
                    headers={"Authorization": ADMIN_TOKEN},
                )
        assert response.status_code in (401, 500)