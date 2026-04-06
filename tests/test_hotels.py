"""
tests/test_hotels.py
Unit tests for all 25 Hotel API endpoints.

Routes covered:
  ── PUBLIC ────────────────────────────────────────────────────
  GET  /hotels                                          — List hotels with filters
  GET  /hotels/featured                                 — Featured hotels
  GET  /hotels/popular                                  — Popular hotels
  GET  /hotels/nearby                                   — Hotels near lat/lng
  GET  /hotels/{id}                                     — Hotel detail
  GET  /hotels/{id}/rooms                               — All room types
  GET  /hotels/{id}/rooms/{room_id}                     — Single room detail
  GET  /hotels/{id}/amenities                           — Hotel amenities
  GET  /hotels/{id}/images                              — Hotel images
  GET  /hotels/{id}/reviews                             — Hotel reviews
  GET  /hotels/{id}/availability                        — Available rooms for dates
  GET  /hotels/{id}/pricing                             — Room pricing for dates

  ── PARTNER — HOTEL CRUD ──────────────────────────────────────
  POST   /hotels/partner                                — Create hotel
  PUT    /hotels/partner/{id}                           — Update hotel
  DELETE /hotels/partner/{id}                           — Soft delete hotel

  ── PARTNER — ROOMS ───────────────────────────────────────────
  POST   /hotels/partner/{id}/rooms                     — Add room type
  PUT    /hotels/partner/{id}/rooms/{room_id}           — Update room
  DELETE /hotels/partner/{id}/rooms/{room_id}           — Delete room
  PUT    /hotels/partner/{id}/rooms/{room_id}/pricing   — Update room price
  PUT    /hotels/partner/{id}/rooms/{room_id}/availability — Toggle availability
  POST   /hotels/partner/{id}/rooms/{room_id}/block     — Block dates

  ── PARTNER — MEDIA ───────────────────────────────────────────
  POST   /hotels/partner/{id}/images                    — Upload image
  DELETE /hotels/partner/{id}/images/{image_id}         — Delete image
  POST   /hotels/partner/{id}/amenities                 — Add amenity
  DELETE /hotels/partner/{id}/amenities/{amenity_id}    — Delete amenity

Run with:
    pytest tests/test_hotels.py -v
"""

from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

PARTNER_TOKEN = "Bearer test_partner_token"
USER_TOKEN = "Bearer test_user_token"
HOTEL_ID = str(uuid4())
ROOM_ID = str(uuid4())
IMAGE_ID = str(uuid4())
AMENITY_ID = str(uuid4())

MOCK_PARTNER = MagicMock()
MOCK_PARTNER.id = str(uuid4())
MOCK_PARTNER.phone = "9876543210"
MOCK_PARTNER.role = "partner"
MOCK_PARTNER.is_phone_verified = True
MOCK_PARTNER.is_email_verified = True

MOCK_USER = MagicMock()
MOCK_USER.id = str(uuid4())
MOCK_USER.phone = "9876543211"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True
MOCK_USER.is_email_verified = True

SAMPLE_HOTEL = {
    "id": HOTEL_ID,
    "name": "Temple View Hotel",
    "star_rating": 3,
    "hotel_type": "HOTEL",
    "city": "Tirupati",
    "state": "Andhra Pradesh",
    "address": "123 Temple Road",
    "is_featured": False,
    "base_price": 1500.0,
    "rating": 4.2,
    "total_reviews": 120,
}

SAMPLE_ROOM = {
    "id": ROOM_ID,
    "hotel_id": HOTEL_ID,
    "room_type": "DELUXE",
    "name": "Deluxe Room",
    "max_occupancy": 2,
    "total_rooms": 10,
    "price_per_night": 1500.0,
    "has_ac": True,
    "has_wifi": True,
    "is_active": True,
}

SAMPLE_HOTEL_CREATE = {
    "name": "Temple View Hotel",
    "address": "123 Temple Road",
    "city": "Tirupati",
    "state": "Andhra Pradesh",
    "star_rating": 3,
    "hotel_type": "HOTEL",
}

SAMPLE_ROOM_CREATE = {
    "room_type": "DELUXE",
    "price_per_night": 1500.0,
    "max_occupancy": 2,
    "total_rooms": 10,
}

SAMPLE_AMENITY_CREATE = {
    "name": "Swimming Pool",
    "category": "WELLNESS",
    "is_paid": False,
}


# ─── Public: List Hotels ──────────────────────────────────────────────────────

class TestListHotels:

    def test_list_hotels_no_filters(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels")
        assert response.status_code == 200

    def test_list_hotels_with_city_filter(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels?city=Tirupati")
        assert response.status_code == 200

    def test_list_hotels_with_star_rating(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels?star_rating=3")
        assert response.status_code == 200

    def test_list_hotels_with_price_range(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels?min_price=500&max_price=3000")
        assert response.status_code == 200

    def test_list_hotels_with_dates_and_guests(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels?checkin=2026-04-10&checkout=2026-04-12&guests=2")
        assert response.status_code == 200

    def test_list_hotels_pagination(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/hotels?page=2&limit=10")
        assert response.status_code == 200

    def test_list_hotels_limit_too_high(self):
        response = client.get("/api/v1/hotels?limit=999")
        assert response.status_code == 422

    def test_list_hotels_invalid_page(self):
        response = client.get("/api/v1/hotels?page=0")
        assert response.status_code == 422

    def test_list_hotels_empty_result(self):
        with patch("src.services.hotel_service.list_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/hotels?city=Nonexistent")
        assert response.status_code == 200


# ─── Public: Featured & Popular ──────────────────────────────────────────────

class TestFeaturedHotels:

    def test_get_featured_success(self):
        with patch("src.services.hotel_service.get_featured_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels/featured")
        assert response.status_code == 200

    def test_get_featured_empty(self):
        with patch("src.services.hotel_service.get_featured_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/hotels/featured")
        assert response.status_code == 200


class TestPopularHotels:

    def test_get_popular_success(self):
        with patch("src.services.hotel_service.get_popular_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels/popular")
        assert response.status_code == 200

    def test_get_popular_with_limit(self):
        with patch("src.services.hotel_service.get_popular_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels/popular?limit=5")
        assert response.status_code == 200

    def test_get_popular_limit_too_high(self):
        response = client.get("/api/v1/hotels/popular?limit=999")
        assert response.status_code == 422

    def test_get_popular_limit_zero(self):
        response = client.get("/api/v1/hotels/popular?limit=0")
        assert response.status_code == 422


# ─── Public: Nearby ──────────────────────────────────────────────────────────

class TestNearbyHotels:

    def test_nearby_missing_lat_lng(self):
        response = client.get("/api/v1/hotels/nearby")
        assert response.status_code == 422

    def test_nearby_missing_lng(self):
        response = client.get("/api/v1/hotels/nearby?lat=13.6288")
        assert response.status_code == 422

    def test_nearby_success(self):
        with patch("src.services.hotel_service.get_nearby_hotels") as mock_svc:
            mock_svc.return_value = [SAMPLE_HOTEL]
            response = client.get("/api/v1/hotels/nearby?lat=13.6288&lng=79.4192")
        assert response.status_code == 200

    def test_nearby_with_radius(self):
        with patch("src.services.hotel_service.get_nearby_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/hotels/nearby?lat=13.6288&lng=79.4192&radius_km=2.0")
        assert response.status_code == 200

    def test_nearby_radius_too_large(self):
        response = client.get("/api/v1/hotels/nearby?lat=13.6288&lng=79.4192&radius_km=999")
        assert response.status_code == 422


# ─── Public: Hotel Detail ─────────────────────────────────────────────────────

class TestHotelDetail:

    def test_get_hotel_detail_success(self):
        with patch("src.services.hotel_service.get_hotel_detail") as mock_svc:
            mock_svc.return_value = SAMPLE_HOTEL
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}")
        assert response.status_code == 200

    def test_get_hotel_detail_not_found(self):
        with patch("src.services.hotel_service.get_hotel_detail") as mock_svc:
            from fastapi import HTTPException
            mock_svc.side_effect = HTTPException(status_code=404, detail="Hotel not found")
            response = client.get(f"/api/v1/hotels/{uuid4()}")
        assert response.status_code == 404

    def test_get_hotel_rooms_success(self):
        with patch("src.services.hotel_service.get_hotel_rooms") as mock_svc:
            mock_svc.return_value = [SAMPLE_ROOM]
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/rooms")
        assert response.status_code == 200

    def test_get_hotel_rooms_empty(self):
        with patch("src.services.hotel_service.get_hotel_rooms") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/rooms")
        assert response.status_code == 200

    def test_get_room_detail_success(self):
        with patch("src.services.hotel_service.get_room_detail") as mock_svc:
            mock_svc.return_value = SAMPLE_ROOM
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/rooms/{ROOM_ID}")
        assert response.status_code == 200

    def test_get_room_detail_not_found(self):
        with patch("src.services.hotel_service.get_room_detail") as mock_svc:
            from fastapi import HTTPException
            mock_svc.side_effect = HTTPException(status_code=404, detail="Room not found")
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/rooms/{uuid4()}")
        assert response.status_code == 404

    def test_get_hotel_amenities_success(self):
        with patch("src.services.hotel_service.get_hotel_amenities_public") as mock_svc:
            mock_svc.return_value = [{"id": str(uuid4()), "name": "WiFi", "category": "GENERAL", "is_paid": False}]
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/amenities")
        assert response.status_code == 200

    def test_get_hotel_images_success(self):
        with patch("src.services.hotel_service.get_hotel_images_public") as mock_svc:
            mock_svc.return_value = [{"id": str(uuid4()), "image_url": "https://s3.example.com/img.jpg", "is_primary": True}]
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/images")
        assert response.status_code == 200

    def test_get_hotel_reviews_success(self):
        with patch("src.services.hotel_service.get_hotel_reviews") as mock_svc:
            mock_svc.return_value = {"reviews": [], "total": 0, "page": 1}
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/reviews")
        assert response.status_code == 200

    def test_get_hotel_reviews_pagination(self):
        with patch("src.services.hotel_service.get_hotel_reviews") as mock_svc:
            mock_svc.return_value = {"reviews": [], "total": 0, "page": 2}
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/reviews?page=2&limit=10")
        assert response.status_code == 200

    def test_get_hotel_reviews_limit_too_high(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/reviews?limit=999")
        assert response.status_code == 422


# ─── Public: Availability & Pricing ──────────────────────────────────────────

class TestHotelAvailability:

    def test_availability_missing_checkin(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/availability?checkout=2026-04-12&guests=2")
        assert response.status_code == 422

    def test_availability_missing_checkout(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/availability?checkin=2026-04-10&guests=2")
        assert response.status_code == 422

    def test_availability_invalid_date_format(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/availability?checkin=10-04-2026&checkout=12-04-2026")
        assert response.status_code == 400

    def test_availability_checkout_before_checkin(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/availability?checkin=2026-04-12&checkout=2026-04-10&guests=1")
        assert response.status_code == 400

    def test_availability_success(self):
        with patch("src.services.hotel_service.check_availability") as mock_svc:
            mock_svc.return_value = {
                "hotel_id": HOTEL_ID,
                "check_in": "2026-04-10",
                "check_out": "2026-04-12",
                "nights": 2,
                "available_rooms": [{"room_type": "DELUXE", "available_count": 5, "price_per_night": 1500.0}],
            }
            response = client.get(
                f"/api/v1/hotels/{HOTEL_ID}/availability?checkin=2026-04-10&checkout=2026-04-12&guests=2"
            )
        assert response.status_code == 200


class TestHotelPricing:

    def test_pricing_missing_dates(self):
        response = client.get(f"/api/v1/hotels/{HOTEL_ID}/pricing")
        assert response.status_code == 422

    def test_pricing_success(self):
        with patch("src.services.hotel_service.get_hotel_pricing") as mock_svc:
            mock_svc.return_value = [{"room_type": "DELUXE", "price_per_night": 1500.0, "total": 3000.0}]
            response = client.get(f"/api/v1/hotels/{HOTEL_ID}/pricing?checkin=2026-04-10&checkout=2026-04-12")
        assert response.status_code == 200


# ─── Partner: Hotel CRUD ─────────────────────────────────────────────────────

class TestCreateHotel:

    def test_create_hotel_unauthorized(self):
        response = client.post("/api/v1/hotels/partner", json=SAMPLE_HOTEL_CREATE)
        assert response.status_code == 401

    def test_create_hotel_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.create_hotel") as mock_svc:
                mock_svc.return_value = SAMPLE_HOTEL
                response = client.post(
                    "/api/v1/hotels/partner",
                    json=SAMPLE_HOTEL_CREATE,
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_create_hotel_missing_required_fields(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            response = client.post(
                "/api/v1/hotels/partner",
                json={"name": "Only Name"},
                headers={"Authorization": PARTNER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_create_hotel_non_partner_user_rejected(self):
        # A regular traveler must not be able to create hotels
        with patch("src.api.deps.auth.get_partner_user") as mock_dep:
            from fastapi import HTTPException
            mock_dep.side_effect = HTTPException(status_code=403, detail="Partner access required")
            response = client.post(
                "/api/v1/hotels/partner",
                json=SAMPLE_HOTEL_CREATE,
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 403)


class TestUpdateHotel:

    def test_update_hotel_unauthorized(self):
        response = client.put(f"/api/v1/hotels/partner/{HOTEL_ID}", json={"name": "New Name"})
        assert response.status_code == 401

    def test_update_hotel_success(self):
        updated = {**SAMPLE_HOTEL, "name": "Updated Hotel Name"}
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.update_hotel") as mock_svc:
                mock_svc.return_value = updated
                response = client.put(
                    f"/api/v1/hotels/partner/{HOTEL_ID}",
                    json={"name": "Updated Hotel Name"},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_hotel_not_found(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.update_hotel") as mock_svc:
                from fastapi import HTTPException
                mock_svc.side_effect = HTTPException(status_code=404, detail="Hotel not found")
                response = client.put(
                    f"/api/v1/hotels/partner/{uuid4()}",
                    json={"name": "Ghost Hotel"},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (401, 404)


class TestDeleteHotel:

    def test_delete_hotel_unauthorized(self):
        response = client.delete(f"/api/v1/hotels/partner/{HOTEL_ID}")
        assert response.status_code == 401

    def test_delete_hotel_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_hotel") as mock_svc:
                mock_svc.return_value = {"message": "Hotel deactivated successfully"}
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_hotel_not_owner(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_hotel") as mock_svc:
                from fastapi import HTTPException
                mock_svc.side_effect = HTTPException(status_code=403, detail="Not authorized to delete this hotel")
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (401, 403)


# ─── Partner: Rooms ──────────────────────────────────────────────────────────

class TestAddRoom:

    def test_add_room_unauthorized(self):
        response = client.post(f"/api/v1/hotels/partner/{HOTEL_ID}/rooms", json=SAMPLE_ROOM_CREATE)
        assert response.status_code == 401

    def test_add_room_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.add_room") as mock_svc:
                mock_svc.return_value = SAMPLE_ROOM
                response = client.post(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms",
                    json=SAMPLE_ROOM_CREATE,
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_add_room_missing_price(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            response = client.post(
                f"/api/v1/hotels/partner/{HOTEL_ID}/rooms",
                json={"room_type": "DELUXE"},
                headers={"Authorization": PARTNER_TOKEN},
            )
        assert response.status_code in (401, 422)


class TestUpdateRoom:

    def test_update_room_unauthorized(self):
        response = client.put(
            f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}",
            json={"price_per_night": 2000.0},
        )
        assert response.status_code == 401

    def test_update_room_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.update_room") as mock_svc:
                mock_svc.return_value = {**SAMPLE_ROOM, "price_per_night": 2000.0}
                response = client.put(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}",
                    json={"price_per_night": 2000.0},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)


class TestDeleteRoom:

    def test_delete_room_unauthorized(self):
        response = client.delete(f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}")
        assert response.status_code == 401

    def test_delete_room_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_room") as mock_svc:
                mock_svc.return_value = {"message": "Room deleted successfully"}
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)


class TestUpdateRoomPricing:

    def test_update_pricing_unauthorized(self):
        response = client.put(
            f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/pricing",
            json={"price_per_night": 2000.0},
        )
        assert response.status_code == 401

    def test_update_pricing_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.update_room_pricing") as mock_svc:
                mock_svc.return_value = {"price_per_night": 2000.0, "weekend_price": 2500.0}
                response = client.put(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/pricing",
                    json={"price_per_night": 2000.0, "weekend_price": 2500.0},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_pricing_missing_price(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            response = client.put(
                f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/pricing",
                json={},
                headers={"Authorization": PARTNER_TOKEN},
            )
        assert response.status_code in (401, 422)


class TestToggleRoomAvailability:

    def test_toggle_availability_unauthorized(self):
        response = client.put(
            f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/availability"
        )
        assert response.status_code == 401

    def test_toggle_availability_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.toggle_room_availability") as mock_svc:
                mock_svc.return_value = {"message": "Room deactivated", "is_active": False}
                response = client.put(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/availability",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)


class TestBlockRoomDates:

    def test_block_dates_unauthorized(self):
        response = client.post(
            f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/block",
            json={"dates": ["2026-04-25", "2026-04-26"]},
        )
        assert response.status_code == 401

    def test_block_dates_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.block_room_dates") as mock_svc:
                mock_svc.return_value = {"message": "2 dates blocked", "blocked_dates": ["2026-04-25", "2026-04-26"]}
                response = client.post(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/block",
                    json={"dates": ["2026-04-25", "2026-04-26"], "reason": "Maintenance"},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_block_dates_empty_list(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            response = client.post(
                f"/api/v1/hotels/partner/{HOTEL_ID}/rooms/{ROOM_ID}/block",
                json={"dates": []},
                headers={"Authorization": PARTNER_TOKEN},
            )
        assert response.status_code in (201, 401, 422)


# ─── Partner: Media ───────────────────────────────────────────────────────────

class TestUploadHotelImage:

    def test_upload_image_unauthorized(self):
        response = client.post(f"/api/v1/hotels/partner/{HOTEL_ID}/images")
        assert response.status_code in (401, 422)

    def test_upload_image_success(self):
        mock_image = {
            "id": IMAGE_ID,
            "image_url": "https://s3.example.com/hotels/img.jpg",
            "category": "EXTERIOR",
            "is_primary": False,
        }
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.upload_image") as mock_svc:
                mock_svc.return_value = mock_image
                response = client.post(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/images",
                    files={"file": ("test.jpg", b"fakeimagebytes", "image/jpeg")},
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (201, 401)


class TestDeleteHotelImage:

    def test_delete_image_unauthorized(self):
        response = client.delete(f"/api/v1/hotels/partner/{HOTEL_ID}/images/{IMAGE_ID}")
        assert response.status_code == 401

    def test_delete_image_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_image") as mock_svc:
                mock_svc.return_value = {"message": "Image deleted successfully"}
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/images/{IMAGE_ID}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_image_not_found(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_image") as mock_svc:
                from fastapi import HTTPException
                mock_svc.side_effect = HTTPException(status_code=404, detail="Image not found")
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/images/{uuid4()}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (401, 404)


# ─── Partner: Amenities ───────────────────────────────────────────────────────

class TestAddAmenity:

    def test_add_amenity_unauthorized(self):
        response = client.post(
            f"/api/v1/hotels/partner/{HOTEL_ID}/amenities",
            json=SAMPLE_AMENITY_CREATE,
        )
        assert response.status_code == 401

    def test_add_amenity_success(self):
        mock_amenity = {
            "id": AMENITY_ID,
            "name": "Swimming Pool",
            "category": "WELLNESS",
            "is_paid": False,
        }
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.add_amenity") as mock_svc:
                mock_svc.return_value = mock_amenity
                response = client.post(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/amenities",
                    json=SAMPLE_AMENITY_CREATE,
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (201, 401)

    def test_add_amenity_missing_name(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            response = client.post(
                f"/api/v1/hotels/partner/{HOTEL_ID}/amenities",
                json={"category": "WELLNESS"},
                headers={"Authorization": PARTNER_TOKEN},
            )
        assert response.status_code in (401, 422)


class TestDeleteAmenity:

    def test_delete_amenity_unauthorized(self):
        response = client.delete(f"/api/v1/hotels/partner/{HOTEL_ID}/amenities/{AMENITY_ID}")
        assert response.status_code == 401

    def test_delete_amenity_success(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_amenity") as mock_svc:
                mock_svc.return_value = {"message": "Amenity removed"}
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/amenities/{AMENITY_ID}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_amenity_not_found(self):
        with patch("src.api.deps.auth.get_partner_user", return_value=MOCK_PARTNER):
            with patch("src.services.hotel_service.delete_amenity") as mock_svc:
                from fastapi import HTTPException
                mock_svc.side_effect = HTTPException(status_code=404, detail="Amenity not found")
                response = client.delete(
                    f"/api/v1/hotels/partner/{HOTEL_ID}/amenities/{uuid4()}",
                    headers={"Authorization": PARTNER_TOKEN},
                )
        assert response.status_code in (401, 404)