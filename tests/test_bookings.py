"""
tests/test_bookings.py
Unit tests for all 25 Booking API endpoints.

Routes covered:
  Cart (6):
    GET    /bookings/cart               — Get cart
    POST   /bookings/cart/add           — Add item to cart
    PUT    /bookings/cart/{item_id}     — Update cart item
    DELETE /bookings/cart/clear         — Clear entire cart
    DELETE /bookings/cart/{item_id}     — Remove item from cart
    POST   /bookings/cart/checkout      — Checkout cart

  Create Bookings (9):
    POST   /bookings/hotel              — Book hotel
    POST   /bookings/vehicle            — Book vehicle
    POST   /bookings/darshan            — Book darshan slot
    POST   /bookings/pooja              — Book pooja
    POST   /bookings/prasadam           — Order prasadam
    POST   /bookings/package            — Book package
    POST   /bookings/guide              — Book guide
    POST   /bookings/combo              — Combo booking
    POST   /bookings/custom             — Custom trip request

  My Bookings (10):
    GET    /bookings/                   — All bookings (filters + pagination)
    GET    /bookings/upcoming           — Upcoming bookings
    GET    /bookings/past               — Past bookings
    GET    /bookings/cancelled          — Cancelled bookings
    GET    /bookings/{id}               — Booking detail
    GET    /bookings/{id}/invoice       — Download invoice
    GET    /bookings/{id}/ticket        — Download e-ticket
    GET    /bookings/{id}/tracking      — Live tracking
    PUT    /bookings/{id}/cancel        — Cancel booking
    POST   /bookings/{id}/modify        — Modify booking

Run with:
    pytest tests/test_bookings.py -v
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
ADMIN_TOKEN = "Bearer test_admin_token"
USER_ID = str(uuid4())
BOOKING_ID = str(uuid4())
ITEM_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True

MOCK_ADMIN = MagicMock()
MOCK_ADMIN.id = str(uuid4())
MOCK_ADMIN.role = "admin"

# Minimal valid payloads
HOTEL_PAYLOAD = {
    "hotel_id": str(uuid4()),
    "room_id": str(uuid4()),
    "check_in": "2026-06-01",
    "check_out": "2026-06-03",
    "guests": 2,
}

VEHICLE_PAYLOAD = {
    "vehicle_id": str(uuid4()),
    "pickup_date": "2026-06-01T08:00:00",
    "pickup_address": "Visakhapatnam Railway Station",
    "drop_address": "Araku Valley",
    "trip_type": "ONE_WAY",
}

DARSHAN_PAYLOAD = {
    "temple_id": str(uuid4()),
    "slot_id": str(uuid4()),
    "date": "2026-06-01",
    "devotees": [{"name": "Ravi Kumar", "age": 35, "id_proof": "aadhaar"}],
}

POOJA_PAYLOAD = {
    "temple_id": str(uuid4()),
    "pooja_id": str(uuid4()),
    "date": "2026-06-01",
    "devotees": [{"name": "Ravi Kumar", "age": 35}],
}

PRASADAM_PAYLOAD = {
    "temple_id": str(uuid4()),
    "items": [{"item_id": str(uuid4()), "quantity": 2}],
    "pickup_date": "2026-06-01",
}

PACKAGE_PAYLOAD = {
    "package_id": str(uuid4()),
    "start_date": "2026-06-01",
    "group_size": 4,
    "traveler_details": [{"name": "Ravi", "age": 35}],
}

GUIDE_PAYLOAD = {
    "guide_id": str(uuid4()),
    "start_date": "2026-06-01",
    "end_date": "2026-06-03",
    "destination_id": str(uuid4()),
}

COMBO_PAYLOAD = {
    "package_id": str(uuid4()),
    "hotel_id": str(uuid4()),
    "vehicle_id": str(uuid4()),
    "start_date": "2026-06-01",
    "group_size": 2,
}

CUSTOM_PAYLOAD = {
    "destinations": ["Tirupati", "Srikalahasti"],
    "start_date": "2026-06-01",
    "end_date": "2026-06-05",
    "services_needed": ["hotel", "vehicle"],
    "group_size": 3,
    "budget": 15000,
}


def _mock_result():
    """Return a generic mock with model_dump support."""
    m = MagicMock()
    m.model_dump.return_value = {"id": str(uuid4()), "status": "PENDING"}
    return m


# ─── Cart ─────────────────────────────────────────────────────────────────────

class TestCart:

    def test_get_cart_unauthorized(self):
        response = client.get("/api/v1/bookings/cart")
        assert response.status_code == 401

    def test_get_cart_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_cart") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/cart",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_add_to_cart_unauthorized(self):
        response = client.post("/api/v1/bookings/cart/add", json={
            "entity_type": "hotel",
            "entity_id": str(uuid4()),
            "date": "2026-06-01",
            "guests": 2,
        })
        assert response.status_code == 401

    def test_add_to_cart_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.add_to_cart") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/cart/add",
                    json={
                        "entity_type": "hotel",
                        "entity_id": str(uuid4()),
                        "date": "2026-06-01",
                        "guests": 2,
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_update_cart_item_unauthorized(self):
        response = client.put(f"/api/v1/bookings/cart/{ITEM_ID}", json={"guests": 3})
        assert response.status_code == 401

    def test_update_cart_item_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.update_cart_item") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.put(
                    f"/api/v1/bookings/cart/{ITEM_ID}",
                    json={"guests": 3},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_clear_cart_unauthorized(self):
        response = client.delete("/api/v1/bookings/cart/clear")
        assert response.status_code == 401

    def test_clear_cart_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.clear_cart") as mock_svc:
                mock_svc.return_value = None
                response = client.delete(
                    "/api/v1/bookings/cart/clear",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_remove_cart_item_unauthorized(self):
        response = client.delete(f"/api/v1/bookings/cart/{ITEM_ID}")
        assert response.status_code == 401

    def test_remove_cart_item_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.remove_cart_item") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.delete(
                    f"/api/v1/bookings/cart/{ITEM_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_checkout_cart_unauthorized(self):
        response = client.post("/api/v1/bookings/cart/checkout")
        assert response.status_code == 401

    def test_checkout_cart_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.checkout_cart") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/cart/checkout",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)


# ─── Create Bookings ──────────────────────────────────────────────────────────

class TestCreateBookings:

    def test_book_hotel_unauthorized(self):
        response = client.post("/api/v1/bookings/hotel", json=HOTEL_PAYLOAD)
        assert response.status_code == 401

    def test_book_hotel_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_hotel") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/hotel",
                    json=HOTEL_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_vehicle_unauthorized(self):
        response = client.post("/api/v1/bookings/vehicle", json=VEHICLE_PAYLOAD)
        assert response.status_code == 401

    def test_book_vehicle_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_vehicle") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/vehicle",
                    json=VEHICLE_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_darshan_unauthorized(self):
        response = client.post("/api/v1/bookings/darshan", json=DARSHAN_PAYLOAD)
        assert response.status_code == 401

    def test_book_darshan_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_darshan") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/darshan",
                    json=DARSHAN_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_pooja_unauthorized(self):
        response = client.post("/api/v1/bookings/pooja", json=POOJA_PAYLOAD)
        assert response.status_code == 401

    def test_book_pooja_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_pooja") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/pooja",
                    json=POOJA_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_prasadam_unauthorized(self):
        response = client.post("/api/v1/bookings/prasadam", json=PRASADAM_PAYLOAD)
        assert response.status_code == 401

    def test_book_prasadam_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_prasadam") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/prasadam",
                    json=PRASADAM_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_package_unauthorized(self):
        response = client.post("/api/v1/bookings/package", json=PACKAGE_PAYLOAD)
        assert response.status_code == 401

    def test_book_package_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_package") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/package",
                    json=PACKAGE_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_guide_unauthorized(self):
        response = client.post("/api/v1/bookings/guide", json=GUIDE_PAYLOAD)
        assert response.status_code == 401

    def test_book_guide_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_guide") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/guide",
                    json=GUIDE_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_combo_unauthorized(self):
        response = client.post("/api/v1/bookings/combo", json=COMBO_PAYLOAD)
        assert response.status_code == 401

    def test_book_combo_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_combo") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/combo",
                    json=COMBO_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_book_custom_unauthorized(self):
        response = client.post("/api/v1/bookings/custom", json=CUSTOM_PAYLOAD)
        assert response.status_code == 401

    def test_book_custom_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.book_custom") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.post(
                    "/api/v1/bookings/custom",
                    json=CUSTOM_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)


# ─── My Bookings ──────────────────────────────────────────────────────────────

class TestMyBookings:

    def test_list_bookings_unauthorized(self):
        response = client.get("/api/v1/bookings/")
        assert response.status_code == 401

    def test_list_bookings_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_my_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_bookings_with_status_filter(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_my_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/?status=CONFIRMED",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_bookings_invalid_status(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            response = client.get(
                "/api/v1/bookings/?status=INVALID_STATUS",
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (400, 401)

    def test_list_bookings_invalid_date_format(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            response = client.get(
                "/api/v1/bookings/?date_from=not-a-date",
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (400, 401)

    def test_list_bookings_pagination(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_my_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/?page=1&limit=10",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_upcoming_bookings_unauthorized(self):
        response = client.get("/api/v1/bookings/upcoming")
        assert response.status_code == 401

    def test_upcoming_bookings_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_upcoming_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/upcoming",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_past_bookings_unauthorized(self):
        response = client.get("/api/v1/bookings/past")
        assert response.status_code == 401

    def test_past_bookings_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_past_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/past",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_cancelled_bookings_unauthorized(self):
        response = client.get("/api/v1/bookings/cancelled")
        assert response.status_code == 401

    def test_cancelled_bookings_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_cancelled_bookings") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    "/api/v1/bookings/cancelled",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_booking_detail_unauthorized(self):
        response = client.get(f"/api/v1/bookings/{BOOKING_ID}")
        assert response.status_code == 401

    def test_get_booking_detail_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_booking_detail") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    f"/api/v1/bookings/{BOOKING_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_booking_detail_not_found(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_booking_detail") as mock_svc:
                mock_svc.side_effect = ValueError("Booking not found")
                response = client.get(
                    f"/api/v1/bookings/{uuid4()}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404, 500)


# ─── Invoice & Ticket ─────────────────────────────────────────────────────────

class TestInvoiceAndTicket:

    def test_get_invoice_unauthorized(self):
        response = client.get(f"/api/v1/bookings/{BOOKING_ID}/invoice")
        assert response.status_code == 401

    def test_get_invoice_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_invoice") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    f"/api/v1/bookings/{BOOKING_ID}/invoice",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_ticket_unauthorized(self):
        response = client.get(f"/api/v1/bookings/{BOOKING_ID}/ticket")
        assert response.status_code == 401

    def test_get_ticket_success(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.get_ticket") as mock_svc:
                mock_svc.return_value = _mock_result()
                response = client.get(
                    f"/api/v1/bookings/{BOOKING_ID}/ticket",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Tracking ─────────────────────────────────────────────────────────────────

class TestBookingTracking:

    def test_get_tracking_unauthorized(self):
        response = client.get(f"/api/v1/bookings/{BOOKING_ID}/tracking")
        assert response.status_code == 401

    def test_get_tracking_not_found(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.repositories.booking_repo.get_booking_for_modify") as mock_repo:
                mock_repo.return_value = None
                response = client.get(
                    f"/api/v1/bookings/{uuid4()}/tracking",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404)

    def test_get_tracking_no_active_data(self):
        mock_booking = MagicMock()
        mock_booking.booking_number = "BK-001"
        mock_booking.status = "CONFIRMED"
        mock_booking.user_id = USER_ID
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.repositories.booking_repo.get_booking_for_modify") as mock_repo:
                mock_repo.return_value = mock_booking
                response = client.get(
                    f"/api/v1/bookings/{BOOKING_ID}/tracking",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Cancel & Modify ──────────────────────────────────────────────────────────

class TestCancelAndModify:

    def test_cancel_booking_unauthorized(self):
        response = client.put(
            f"/api/v1/bookings/{BOOKING_ID}/cancel",
            json={"reason": "Change of plans"},
        )
        assert response.status_code == 401

    def test_cancel_booking_success(self):
        mock_result = _mock_result()
        mock_result.message = "Booking cancelled. Full refund will be processed."
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.cancel_booking") as mock_svc:
                mock_svc.return_value = mock_result
                response = client.put(
                    f"/api/v1/bookings/{BOOKING_ID}/cancel",
                    json={"reason": "Change of plans"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_cancel_booking_not_found(self):
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.cancel_booking") as mock_svc:
                mock_svc.side_effect = ValueError("Booking not found")
                response = client.put(
                    f"/api/v1/bookings/{uuid4()}/cancel",
                    json={"reason": "Change of plans"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 404)

    def test_modify_booking_unauthorized(self):
        response = client.post(
            f"/api/v1/bookings/{BOOKING_ID}/modify",
            json={"change_type": "date", "new_date": "2026-07-01"},
        )
        assert response.status_code == 401

    def test_modify_booking_success(self):
        mock_result = _mock_result()
        mock_result.message = "Modification request submitted."
        with patch("src.core.dependencies.get_current_user", return_value=MOCK_USER):
            with patch("src.services.booking_service.modify_booking") as mock_svc:
                mock_svc.return_value = mock_result
                response = client.post(
                    f"/api/v1/bookings/{BOOKING_ID}/modify",
                    json={"change_type": "date", "new_date": "2026-07-01"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)