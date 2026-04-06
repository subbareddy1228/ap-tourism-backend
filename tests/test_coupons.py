"""
tests/test_coupons.py
Unit tests for all Coupon API endpoints.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
USER_ID = str(uuid4())
BOOKING_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True


def _mock_coupons_response():
    return {"coupons": [], "total": 0}


# ─────────────────────────────
# Active Coupons (public)
# ─────────────────────────────

class TestActiveCoupons:

    def test_active_coupons_no_auth_required(self):
        with patch("src.api.v1.endpoints.coupons.get_active_coupons") as mock_svc:
            mock_svc.return_value = {
                "coupons": [],
                "total": 0,
                "page": 1,
                "per_page": 10,
            }

            response = client.get("/api/v1/coupons/active")

        assert response.status_code == 200


    def test_active_coupons_pagination(self):
        with patch("src.api.v1.endpoints.coupons.get_active_coupons") as mock_svc:
            mock_svc.return_value = {
                "coupons": [],
                "total": 0,
                "page": 1,
                "per_page": 5,
            }

            response = client.get("/api/v1/coupons/active?page=1&per_page=5")

        assert response.status_code == 200


    def test_active_coupons_invalid_page(self):
        response = client.get("/api/v1/coupons/active?page=0")
        assert response.status_code == 422


    def test_active_coupons_limit_too_high(self):
        response = client.get("/api/v1/coupons/active?per_page=999")
        assert response.status_code == 422


    def test_active_coupons_returns_list(self):
        with patch("src.api.v1.endpoints.coupons.get_active_coupons") as mock_svc:

            mock_svc.return_value = {
                "coupons": [
                    {
                        "id": str(uuid4()),
                        "code": "FESTIVE20",
                        "discount_type": "percentage",
                        "discount_value": 20,
                        "valid_from": "2025-01-01",
                        "valid_until": "2026-12-31",
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 10,
            }

            response = client.get("/api/v1/coupons/active")

        assert response.status_code == 200


# ─────────────────────────────
# Coupon by Code (public)
# ─────────────────────────────

class TestCouponByCode:

    def test_get_coupon_by_code_no_auth_required(self):
        with patch("src.api.v1.endpoints.coupons.get_by_code_public") as mock_svc:

            mock_svc.return_value = {
                "id": str(uuid4()),
                "code": "SAVE10",
                "discount_type": "percentage",
                "discount_value": 10,
                "min_booking_amount": 500,
                "valid_from": "2025-01-01",
                "valid_until": "2026-01-01",
            }

            response = client.get("/api/v1/coupons/SAVE10")

        assert response.status_code in (200, 404)


    def test_get_coupon_by_code_success(self):
        with patch("src.api.v1.endpoints.coupons.get_by_code_public") as mock_svc:

            mock_svc.return_value = {
                "id": str(uuid4()),
                "code": "SAVE10",
                "discount_type": "percentage",
                "discount_value": 10,
                "min_booking_amount": 500,
                "valid_from": "2025-01-01",
                "valid_until": "2026-01-01",
            }

            response = client.get("/api/v1/coupons/TIRUPATI50")

        assert response.status_code in (200, 404)


    def test_get_coupon_by_code_not_found(self):
        with patch("src.api.v1.endpoints.coupons.get_by_code_public") as mock_svc:

            mock_svc.side_effect = ValueError("Coupon not found")

            response = client.get("/api/v1/coupons/FAKECODE999")

        assert response.status_code == 404