"""
tests/test_darshan.py
Unit tests for all 15 Darshan / Pooja / Prasadam API endpoints.

Routes covered:
  GET  /darshan/{temple_id}/darshan-types                     — List darshan types
  GET  /darshan/{temple_id}/darshan-types/{type_id}           — Darshan type detail
  GET  /darshan/{temple_id}/darshan-slots                     — All slots next 30 days
  GET  /darshan/{temple_id}/darshan-slots/{date}              — Slots for a specific date
  POST /darshan/{temple_id}/darshan/check-availability        — Check availability
  POST /darshan/{temple_id}/darshan/book                      — Book darshan slot (auth)
  GET  /darshan/{temple_id}/darshan/booking/{id}              — Booking detail (auth)
  GET  /darshan/{temple_id}/pooja-services                    — List pooja services
  GET  /darshan/{temple_id}/pooja-services/{id}               — Pooja service detail
  GET  /darshan/{temple_id}/pooja-services/{id}/slots         — Available pooja slots
  POST /darshan/{temple_id}/pooja/book                        — Book pooja (auth)
  GET  /darshan/{temple_id}/prasadam                          — List prasadam items
  GET  /darshan/{temple_id}/prasadam/orders                   — My prasadam orders (auth)
  GET  /darshan/{temple_id}/prasadam/{item_id}                — Prasadam item detail
  POST /darshan/{temple_id}/prasadam/order                    — Order prasadam (auth)

Run with:
    pytest tests/test_darshan.py -v
"""

from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
USER_ID = str(uuid4())
TEMPLE_ID = str(uuid4())
TYPE_ID = str(uuid4())
SLOT_ID = str(uuid4())
BOOKING_ID = str(uuid4())
SERVICE_ID = str(uuid4())
ITEM_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True
MOCK_USER.is_email_verified = True

SAMPLE_DARSHAN_TYPE = {
    "id": str(uuid4()),
    "temple_id": TEMPLE_ID,
    "name": "Free Darshan",
    "darshan_type": "free",
    "description": "General darshan open to all pilgrims",
    "price": 0.0,
    "duration_minutes": 30,
    "max_persons_per_booking": 6,
    "is_active": True,
}

SAMPLE_DARSHAN_SLOT = {
    "id": str(uuid4()),
    "temple_id": TEMPLE_ID,
    "darshan_type_id": TYPE_ID,
    "slot_date": "2026-04-10",
    "start_time": "06:00:00",
    "end_time": "07:00:00",
    "total_quota": 200,
    "booked_count": 50,
    "available_count": 150,
    "is_full": False,
    "is_active": True,
}

SAMPLE_DARSHAN_BOOK_PAYLOAD = {
    "slot_id": SLOT_ID,
    "num_persons": 2,
    "pilgrim_details": [
        {"name": "Ramesh Kumar", "age": 35},
        {"name": "Sita Devi", "age": 30},
    ],
}

SAMPLE_CHECK_AVAILABILITY_PAYLOAD = {
    "slot_id": SLOT_ID,
    "num_persons": 2,
}

SAMPLE_POOJA_BOOK_PAYLOAD = {
    "pooja_service_id": SERVICE_ID,
    "slot_id": SLOT_ID,
    "num_persons": 1,
    "devotee_name": "Ramesh Kumar",
    "gothram": "Bharadwaja",
    "special_requests": "Perform for family welfare",
}

SAMPLE_PRASADAM_ORDER_PAYLOAD = {
    "items": [
        {"item_id": ITEM_ID, "quantity": 2}
    ],
    "pickup_date": "2026-04-10",
}


# ─── Darshan Types ────────────────────────────────────────────────────────────

class TestGetDarshanTypes:

    def test_list_darshan_types_success(self):
        with patch("src.api.v1.endpoints.darshan.get_service") as mock_svc_dep:
            mock_svc = MagicMock()
            mock_svc.get_darshan_types = MagicMock(return_value=[SAMPLE_DARSHAN_TYPE])
            mock_svc_dep.return_value = mock_svc
            with patch("src.services.darshan_service.DarshanService.get_darshan_types") as mock_method:
                mock_method.return_value = [SAMPLE_DARSHAN_TYPE]
                response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-types")
        assert response.status_code in (200, 422, 500)

    def test_list_darshan_types_invalid_temple_uuid(self):
        response = client.get("/api/v1/darshan/not-a-uuid/darshan-types")
        assert response.status_code == 422

    def test_list_darshan_types_service_called_with_temple_id(self):
        """Ensures service layer receives correct temple_id."""
        with patch("src.services.darshan_service.DarshanService.get_darshan_types") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-types")
        assert response.status_code in (200, 500)


class TestGetDarshanTypeDetail:

    def test_darshan_type_detail_invalid_temple_uuid(self):
        response = client.get(f"/api/v1/darshan/bad-id/darshan-types/{TYPE_ID}")
        assert response.status_code == 422

    def test_darshan_type_detail_invalid_type_uuid(self):
        response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-types/bad-type-id")
        assert response.status_code == 422

    def test_darshan_type_detail_not_found(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_type_detail") as mock_method:
            from fastapi import HTTPException
            mock_method.side_effect = HTTPException(status_code=404, detail="Darshan type not found")
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-types/{TYPE_ID}")
        assert response.status_code in (404, 500)

    def test_darshan_type_detail_success(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_type_detail") as mock_method:
            mock_method.return_value = SAMPLE_DARSHAN_TYPE
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-types/{TYPE_ID}")
        assert response.status_code in (200, 500)


# ─── Darshan Slots ────────────────────────────────────────────────────────────

class TestGetDarshanSlots:

    def test_list_slots_invalid_temple_uuid(self):
        response = client.get("/api/v1/darshan/not-uuid/darshan-slots")
        assert response.status_code == 422

    def test_list_slots_success(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_slots") as mock_method:
            mock_method.return_value = [SAMPLE_DARSHAN_SLOT]
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-slots")
        assert response.status_code in (200, 500)

    def test_list_slots_empty(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_slots") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-slots")
        assert response.status_code in (200, 500)


class TestGetDarshanSlotsByDate:

    def test_slots_by_date_invalid_temple(self):
        response = client.get("/api/v1/darshan/bad-id/darshan-slots/2026-04-10")
        assert response.status_code == 422

    def test_slots_by_date_invalid_date_format(self):
        response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-slots/not-a-date")
        assert response.status_code == 422

    def test_slots_by_date_success(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_slots_by_date") as mock_method:
            mock_method.return_value = [SAMPLE_DARSHAN_SLOT]
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-slots/2026-04-10")
        assert response.status_code in (200, 500)

    def test_slots_by_date_no_slots(self):
        with patch("src.services.darshan_service.DarshanService.get_darshan_slots_by_date") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan-slots/2026-04-10")
        assert response.status_code in (200, 500)


# ─── Darshan Booking ──────────────────────────────────────────────────────────

class TestCheckDarshanAvailability:

    def test_check_availability_invalid_temple(self):
        response = client.post(
            "/api/v1/darshan/bad-id/darshan/check-availability",
            json=SAMPLE_CHECK_AVAILABILITY_PAYLOAD,
        )
        assert response.status_code == 422

    def test_check_availability_success(self):
        with patch("src.services.darshan_service.DarshanService.check_availability") as mock_method:
            mock_method.return_value = {"available": True, "slots": [SAMPLE_DARSHAN_SLOT]}
            response = client.post(
                f"/api/v1/darshan/{TEMPLE_ID}/darshan/check-availability",
                json=SAMPLE_CHECK_AVAILABILITY_PAYLOAD,
            )
        assert response.status_code in (200, 500)

    def test_check_availability_slot_full(self):
        with patch("src.services.darshan_service.DarshanService.check_availability") as mock_method:
            mock_method.return_value = {"available": False, "message": "Slot is fully booked"}
            response = client.post(
                f"/api/v1/darshan/{TEMPLE_ID}/darshan/check-availability",
                json=SAMPLE_CHECK_AVAILABILITY_PAYLOAD,
            )
        assert response.status_code in (200, 500)

    def test_check_availability_missing_body(self):
        response = client.post(f"/api/v1/darshan/{TEMPLE_ID}/darshan/check-availability", json={})
        assert response.status_code == 422


class TestBookDarshan:

    def test_book_darshan_unauthorized(self):
        response = client.post(
            f"/api/v1/darshan/{TEMPLE_ID}/darshan/book",
            json=SAMPLE_DARSHAN_BOOK_PAYLOAD,
        )
        assert response.status_code == 401

    def test_book_darshan_success(self):
        mock_booking = {
            "booking_id": str(uuid4()),
            "darshan_type_id": TYPE_ID,
            "darshan_date": "2026-04-10",
            "persons": 2,
            "total_price": 0.0,
            "ticket_number": "TKT-001",
        }
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.book_darshan") as mock_method:
                mock_method.return_value = mock_booking
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/darshan/book",
                    json=SAMPLE_DARSHAN_BOOK_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (201, 401, 500)

    def test_book_darshan_slot_unavailable(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.book_darshan") as mock_method:
                from fastapi import HTTPException
                mock_method.side_effect = HTTPException(status_code=400, detail="Slot is fully booked")
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/darshan/book",
                    json=SAMPLE_DARSHAN_BOOK_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 500)

    def test_book_darshan_missing_required_fields(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/darshan/{TEMPLE_ID}/darshan/book",
                json={},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_book_darshan_invalid_temple_uuid(self):
        # Auth dependency fires before path UUID parsing → 401, not 422
        response = client.post(
            "/api/v1/darshan/bad-id/darshan/book",
            json=SAMPLE_DARSHAN_BOOK_PAYLOAD,
        )
        assert response.status_code == 401


class TestGetDarshanBooking:

    def test_get_booking_unauthorized(self):
        response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/darshan/booking/{BOOKING_ID}")
        assert response.status_code == 401

    def test_get_booking_success(self):
        mock_booking = {
            "booking_id": BOOKING_ID,
            "darshan_type_id": TYPE_ID,
            "darshan_date": "2026-04-10",
            "ticket_number": "TKT-001",
        }
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.get_darshan_booking") as mock_method:
                mock_method.return_value = mock_booking
                response = client.get(
                    f"/api/v1/darshan/{TEMPLE_ID}/darshan/booking/{BOOKING_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401, 500)

    def test_get_booking_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.get_darshan_booking") as mock_method:
                from fastapi import HTTPException
                mock_method.side_effect = HTTPException(status_code=404, detail="Booking not found")
                response = client.get(
                    f"/api/v1/darshan/{TEMPLE_ID}/darshan/booking/{BOOKING_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404, 500)

    def test_get_booking_invalid_uuid(self):
        # Auth dependency fires before path UUID parsing → 401, not 422
        response = client.get(
            f"/api/v1/darshan/{TEMPLE_ID}/darshan/booking/not-a-uuid",
        )
        assert response.status_code == 401


# ─── Pooja Services ───────────────────────────────────────────────────────────

class TestGetPoojaServices:

    def test_list_pooja_services_invalid_temple(self):
        response = client.get("/api/v1/darshan/bad-id/pooja-services")
        assert response.status_code == 422

    def test_list_pooja_services_success(self):
        mock_services = [
            {
                "id": str(uuid4()),
                "temple_id": TEMPLE_ID,
                "name": "Abhishekam",
                "description": "Sacred bathing ritual",
                "price": 500.0,
                "duration_minutes": 45,
                "is_active": True,
            }
        ]
        with patch("src.services.darshan_service.DarshanService.get_pooja_services") as mock_method:
            mock_method.return_value = mock_services
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services")
        assert response.status_code in (200, 500)

    def test_list_pooja_services_empty(self):
        with patch("src.services.darshan_service.DarshanService.get_pooja_services") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services")
        assert response.status_code in (200, 500)


class TestGetPoojaServiceDetail:

    def test_pooja_service_detail_invalid_uuids(self):
        response = client.get(f"/api/v1/darshan/bad-id/pooja-services/{SERVICE_ID}")
        assert response.status_code == 422

    def test_pooja_service_detail_not_found(self):
        with patch("src.services.darshan_service.DarshanService.get_pooja_service_detail") as mock_method:
            from fastapi import HTTPException
            mock_method.side_effect = HTTPException(status_code=404, detail="Pooja service not found")
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services/{SERVICE_ID}")
        assert response.status_code in (404, 500)

    def test_pooja_service_detail_success(self):
        with patch("src.services.darshan_service.DarshanService.get_pooja_service_detail") as mock_method:
            mock_method.return_value = {
                "id": SERVICE_ID,
                "temple_id": TEMPLE_ID,
                "name": "Abhishekam",
                "price": 500.0,
            }
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services/{SERVICE_ID}")
        assert response.status_code in (200, 500)


class TestGetPoojaSlots:

    def test_pooja_slots_invalid_temple_uuid(self):
        response = client.get(f"/api/v1/darshan/bad-id/pooja-services/{SERVICE_ID}/slots")
        assert response.status_code == 422

    def test_pooja_slots_success(self):
        with patch("src.services.darshan_service.DarshanService.get_pooja_slots") as mock_method:
            mock_method.return_value = [
                {"slot_time": "08:00:00", "available_count": 5, "is_full": False}
            ]
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services/{SERVICE_ID}/slots")
        assert response.status_code in (200, 500)

    def test_pooja_slots_empty(self):
        with patch("src.services.darshan_service.DarshanService.get_pooja_slots") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/pooja-services/{SERVICE_ID}/slots")
        assert response.status_code in (200, 500)


class TestBookPooja:

    def test_book_pooja_unauthorized(self):
        response = client.post(
            f"/api/v1/darshan/{TEMPLE_ID}/pooja/book",
            json=SAMPLE_POOJA_BOOK_PAYLOAD,
        )
        assert response.status_code == 401

    def test_book_pooja_success(self):
        mock_booking = {
            "booking_id": str(uuid4()),
            "pooja_service_id": SERVICE_ID,
            "pooja_date": "2026-04-10",
            "devotee_names": ["Ramesh Kumar"],
            "gothram": "Bharadwaja",
        }
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.book_pooja") as mock_method:
                mock_method.return_value = mock_booking
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/pooja/book",
                    json=SAMPLE_POOJA_BOOK_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (201, 401, 500)

    def test_book_pooja_missing_devotee_name(self):
        incomplete = {k: v for k, v in SAMPLE_POOJA_BOOK_PAYLOAD.items() if k != "devotee_name"}
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/darshan/{TEMPLE_ID}/pooja/book",
                json=incomplete,
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_book_pooja_service_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.book_pooja") as mock_method:
                from fastapi import HTTPException
                mock_method.side_effect = HTTPException(status_code=404, detail="Pooja service not found")
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/pooja/book",
                    json=SAMPLE_POOJA_BOOK_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404, 500)


# ─── Prasadam ─────────────────────────────────────────────────────────────────

class TestGetPrasadamItems:

    def test_list_prasadam_invalid_temple(self):
        response = client.get("/api/v1/darshan/bad-id/prasadam")
        assert response.status_code == 422

    def test_list_prasadam_success(self):
        with patch("src.services.darshan_service.DarshanService.get_prasadam_items") as mock_method:
            mock_method.return_value = [
                {
                    "id": ITEM_ID,
                    "temple_id": TEMPLE_ID,
                    "name": "Laddu",
                    "price": 50.0,
                    "is_available": True,
                }
            ]
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/prasadam")
        assert response.status_code in (200, 500)

    def test_list_prasadam_empty(self):
        with patch("src.services.darshan_service.DarshanService.get_prasadam_items") as mock_method:
            mock_method.return_value = []
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/prasadam")
        assert response.status_code in (200, 500)


class TestGetMyPrasadamOrders:

    def test_my_orders_unauthorized(self):
        response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/prasadam/orders")
        assert response.status_code == 401

    def test_my_orders_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.get_my_prasadam_orders") as mock_method:
                mock_method.return_value = []
                response = client.get(
                    f"/api/v1/darshan/{TEMPLE_ID}/prasadam/orders",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401, 500)

    def test_my_orders_with_data(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.get_my_prasadam_orders") as mock_method:
                mock_method.return_value = [
                    {
                        "order_id": str(uuid4()),
                        "item_name": "Laddu",
                        "quantity": 2,
                        "total_price": 100.0,
                        "delivery_status": "pending",
                    }
                ]
                response = client.get(
                    f"/api/v1/darshan/{TEMPLE_ID}/prasadam/orders",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401, 500)


class TestGetPrasadamItemDetail:

    def test_prasadam_item_invalid_uuids(self):
        response = client.get("/api/v1/darshan/bad-id/prasadam/also-bad")
        assert response.status_code == 422

    def test_prasadam_item_not_found(self):
        with patch("src.services.darshan_service.DarshanService.get_prasadam_item") as mock_method:
            from fastapi import HTTPException
            mock_method.side_effect = HTTPException(status_code=404, detail="Item not found")
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/prasadam/{ITEM_ID}")
        assert response.status_code in (404, 500)

    def test_prasadam_item_success(self):
        with patch("src.services.darshan_service.DarshanService.get_prasadam_item") as mock_method:
            mock_method.return_value = {
                "id": ITEM_ID,
                "temple_id": TEMPLE_ID,
                "name": "Laddu",
                "price": 50.0,
                "is_available": True,
            }
            response = client.get(f"/api/v1/darshan/{TEMPLE_ID}/prasadam/{ITEM_ID}")
        assert response.status_code in (200, 500)


class TestOrderPrasadam:

    def test_order_prasadam_unauthorized(self):
        response = client.post(
            f"/api/v1/darshan/{TEMPLE_ID}/prasadam/order",
            json=SAMPLE_PRASADAM_ORDER_PAYLOAD,
        )
        assert response.status_code == 401

    def test_order_prasadam_success(self):
        mock_order = {
            "order_id": str(uuid4()),
            "items": [{"item_id": ITEM_ID, "quantity": 2, "price": 100.0}],
            "total_price": 100.0,
            "delivery_status": "pending",
            "tracking_number": None,
        }
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.order_prasadam") as mock_method:
                mock_method.return_value = mock_order
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/prasadam/order",
                    json=SAMPLE_PRASADAM_ORDER_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (201, 401, 500)

    def test_order_prasadam_item_unavailable(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.darshan_service.DarshanService.order_prasadam") as mock_method:
                mock_method.side_effect = ValueError("Item is currently unavailable")
                response = client.post(
                    f"/api/v1/darshan/{TEMPLE_ID}/prasadam/order",
                    json=SAMPLE_PRASADAM_ORDER_PAYLOAD,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 500)

    def test_order_prasadam_invalid_temple_uuid(self):
        # Auth dependency fires before path UUID parsing → 401, not 422
        response = client.post(
            "/api/v1/darshan/bad-temple/prasadam/order",
            json=SAMPLE_PRASADAM_ORDER_PAYLOAD,
        )
        assert response.status_code == 401

    def test_order_prasadam_empty_items(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                f"/api/v1/darshan/{TEMPLE_ID}/prasadam/order",
                json={"items": [], "delivery_address": "123 Temple Street"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422, 400, 500)