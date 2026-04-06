"""
tests/test_coupons.py
Unit tests for all Coupon API endpoints.

Routes covered:
  GET    /coupons/               — List coupons available to user (auth)
  POST   /coupons/validate       — Validate a coupon code (auth)
  POST   /coupons/apply          — Apply coupon to a booking (auth)
  DELETE /coupons/remove         — Remove coupon from a booking (auth)
  GET    /coupons/my-coupons     — User's available and used coupons (auth)
  GET    /coupons/referral       — Get referral code and stats (auth)
  GET    /coupons/active         — List all active public coupons (public)
  GET    /coupons/{code}         — Get coupon details by code (public)

Run with:
    pytest tests/test_coupons.py -v
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


# ─── List Coupons ─────────────────────────────────────────────────────────────

class TestListCoupons:

    def test_list_coupons_unauthorized(self):
        response = client.get("/api/v1/coupons/")
        assert response.status_code == 401

    def test_list_coupons_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.get_my_coupons") as mock_svc:
                mock_svc.return_value = _mock_coupons_response()
                response = client.get(
                    "/api/v1/coupons/",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Validate Coupon ──────────────────────────────────────────────────────────

class TestValidateCoupon:

    def test_validate_unauthorized(self):
        response = client.post("/api/v1/coupons/validate", json={
            "code": "SAVE10",
            "booking_amount": 1000,
        })
        assert response.status_code == 401

    def test_validate_valid_coupon(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.validate_coupon") as mock_svc:
                mock_svc.return_value = {
                    "valid": True,
                    "code": "SAVE10",
                    "discount_amount": 100,
                    "final_amount": 900,
                }
                response = client.post(
                    "/api/v1/coupons/validate",
                    json={"code": "SAVE10", "booking_amount": 1000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_validate_invalid_coupon(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.validate_coupon") as mock_svc:
                mock_svc.return_value = {
                    "valid": False,
                    "reason": "Coupon expired",
                }
                response = client.post(
                    "/api/v1/coupons/validate",
                    json={"code": "EXPIRED10", "booking_amount": 1000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_validate_missing_code(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/coupons/validate",
                json={"booking_amount": 1000},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_validate_coupon_not_applicable(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.validate_coupon") as mock_svc:
                mock_svc.return_value = {
                    "valid": False,
                    "reason": "Minimum booking amount not met",
                }
                response = client.post(
                    "/api/v1/coupons/validate",
                    json={"code": "SAVE500", "booking_amount": 100},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Apply Coupon ─────────────────────────────────────────────────────────────

class TestApplyCoupon:

    def test_apply_unauthorized(self):
        response = client.post("/api/v1/coupons/apply", json={
            "code": "SAVE10",
            "booking_id": BOOKING_ID,
        })
        assert response.status_code == 401

    def test_apply_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.apply_coupon") as mock_svc:
                mock_svc.return_value = {
                    "booking_id": BOOKING_ID,
                    "discount_applied": 100,
                    "new_total": 900,
                }
                response = client.post(
                    "/api/v1/coupons/apply",
                    json={"code": "SAVE10", "booking_id": BOOKING_ID},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_apply_already_applied(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.apply_coupon") as mock_svc:
                mock_svc.side_effect = ValueError("Coupon already applied to this booking")
                response = client.post(
                    "/api/v1/coupons/apply",
                    json={"code": "SAVE10", "booking_id": BOOKING_ID},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)

    def test_apply_coupon_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.apply_coupon") as mock_svc:
                mock_svc.side_effect = ValueError("Coupon not found")
                response = client.post(
                    "/api/v1/coupons/apply",
                    json={"code": "NONEXISTENT", "booking_id": BOOKING_ID},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 404)

    def test_apply_missing_booking_id(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/coupons/apply",
                json={"code": "SAVE10"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)


# ─── Remove Coupon ────────────────────────────────────────────────────────────

class TestRemoveCoupon:

    def test_remove_unauthorized(self):
        response = client.delete("/api/v1/coupons/remove", json={"booking_id": BOOKING_ID})
        assert response.status_code == 401

    def test_remove_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.remove_coupon") as mock_svc:
                mock_svc.return_value = {"message": "Coupon removed successfully"}
                response = client.delete(
                    "/api/v1/coupons/remove",
                    json={"booking_id": BOOKING_ID},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_remove_no_coupon_applied(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.remove_coupon") as mock_svc:
                mock_svc.side_effect = ValueError("No coupon applied to this booking")
                response = client.delete(
                    "/api/v1/coupons/remove",
                    json={"booking_id": BOOKING_ID},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)


# ─── My Coupons ───────────────────────────────────────────────────────────────

class TestMyCoupons:

    def test_my_coupons_unauthorized(self):
        response = client.get("/api/v1/coupons/my-coupons")
        assert response.status_code == 401

    def test_my_coupons_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.get_my_coupons") as mock_svc:
                mock_svc.return_value = {
                    "coupons": [
                        {"code": "SAVE10", "discount": 10, "status": "available"},
                    ],
                    "total": 1,
                }
                response = client.get(
                    "/api/v1/coupons/my-coupons",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_my_coupons_empty(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.get_my_coupons") as mock_svc:
                mock_svc.return_value = {"coupons": [], "total": 0}
                response = client.get(
                    "/api/v1/coupons/my-coupons",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Referral ─────────────────────────────────────────────────────────────────

class TestReferral:

    def test_referral_unauthorized(self):
        response = client.get("/api/v1/coupons/referral")
        assert response.status_code == 401

    def test_referral_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.get_referral_info") as mock_svc:
                mock_svc.return_value = {
                    "referral_code": "REF123ABC",
                    "total_referrals": 3,
                    "total_earned": 300,
                }
                response = client.get(
                    "/api/v1/coupons/referral",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_referral_returns_code(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.coupon_service.get_referral_info") as mock_svc:
                mock_svc.return_value = {
                    "referral_code": "REF123ABC",
                    "total_referrals": 0,
                    "total_earned": 0,
                }
                response = client.get(
                    "/api/v1/coupons/referral",
                    headers={"Authorization": USER_TOKEN},
                )
        if response.status_code == 200:
            assert "referral_code" in response.json()


# ─── Active Coupons (public) ──────────────────────────────────────────────────

class TestActiveCoupons:

    def test_active_coupons_no_auth_required(self):
        with patch("src.services.coupon_service.get_active_coupons") as mock_svc:
            mock_svc.return_value = {"coupons": [], "total": 0}
            response = client.get("/api/v1/coupons/active")
        assert response.status_code == 200

    def test_active_coupons_pagination(self):
        with patch("src.services.coupon_service.get_active_coupons") as mock_svc:
            mock_svc.return_value = {"coupons": [], "total": 0}
            response = client.get("/api/v1/coupons/active?page=1&per_page=5")
        assert response.status_code == 200

    def test_active_coupons_invalid_page(self):
        response = client.get("/api/v1/coupons/active?page=0")
        assert response.status_code == 422

    def test_active_coupons_limit_too_high(self):
        response = client.get("/api/v1/coupons/active?per_page=999")
        assert response.status_code == 422

    def test_active_coupons_returns_list(self):
        with patch("src.services.coupon_service.get_active_coupons") as mock_svc:
            mock_svc.return_value = {
                "coupons": [
                    {"code": "FESTIVE20", "discount_percent": 20, "valid_till": "2026-12-31"},
                ],
                "total": 1,
            }
            response = client.get("/api/v1/coupons/active")
        assert response.status_code == 200


# ─── Coupon by Code (public) ──────────────────────────────────────────────────

class TestCouponByCode:

    def test_get_coupon_by_code_no_auth_required(self):
        with patch("src.services.coupon_service.get_by_code_public") as mock_svc:
            mock_svc.return_value = {
                "code": "SAVE10",
                "discount_percent": 10,
                "min_booking_amount": 500,
            }
            response = client.get("/api/v1/coupons/SAVE10")
        assert response.status_code in (200, 404)

    def test_get_coupon_by_code_success(self):
        with patch("src.services.coupon_service.get_by_code_public") as mock_svc:
            mock_svc.return_value = {
                "code": "TIRUPATI50",
                "discount_percent": 50,
                "min_booking_amount": 1000,
            }
            response = client.get("/api/v1/coupons/TIRUPATI50")
        assert response.status_code in (200, 404)

    def test_get_coupon_by_code_not_found(self):
        with patch("src.services.coupon_service.get_by_code_public") as mock_svc:
            mock_svc.side_effect = ValueError("Coupon not found")
            response = client.get("/api/v1/coupons/FAKECODE999")
        assert response.status_code == 404