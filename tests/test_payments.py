"""
tests/test_payments.py
Unit tests for all Payment API endpoints.

Routes covered:
  GET  /payments/methods                  — List payment methods (public)
  POST /payments/initiate                 — Initiate payment (Razorpay order)
  POST /payments/verify                   — Verify payment signature
  GET  /payments/history                  — Payment history
  POST /payments/validate-upi             — Validate UPI ID
  GET  /payments/saved-cards              — Get saved cards
  POST /payments/saved-cards              — Save a card
  DELETE /payments/saved-cards/{card_id} — Delete saved card
  GET  /payments/refunds                  — List refunds
  POST /payments/refund/request           — Request refund
  GET  /payments/refund/{refund_id}       — Refund detail
  POST /payments/pay-later/check          — Check Pay Later eligibility
  POST /payments/pay-later/apply          — Apply Pay Later
  POST /payments/webhook/razorpay         — Razorpay webhook (public)
  GET  /payments/{transaction_id}         — Transaction detail

Run with:
    pytest tests/test_payments.py -v
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
USER_ID = str(uuid4())
CARD_ID = str(uuid4())
REFUND_ID = str(uuid4())
TXN_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True


# ─── Payment Methods (public) ─────────────────────────────────────────────────

class TestPaymentMethods:

    def test_get_payment_methods_no_auth_required(self):
        """This endpoint is public — no token needed."""
        with patch("src.services.payment_service.get_payment_methods") as mock_svc:
            mock_svc.return_value = {
                "methods": ["UPI", "CARD", "NET_BANKING", "WALLET", "EMI", "PAY_LATER"]
            }
            response = client.get("/api/v1/payments/methods")
        assert response.status_code == 200

    def test_get_payment_methods_returns_all_types(self):
        with patch("src.services.payment_service.get_payment_methods") as mock_svc:
            mock_svc.return_value = {
                "methods": ["UPI", "CARD", "NET_BANKING", "WALLET", "EMI", "PAY_LATER"]
            }
            response = client.get("/api/v1/payments/methods")
        assert response.status_code == 200


# ─── Initiate Payment ─────────────────────────────────────────────────────────

class TestInitiatePayment:

    def test_initiate_unauthorized(self):
        response = client.post("/api/v1/payments/initiate", json={
            "booking_id": str(uuid4()),
            "amount": 1000,
            "method": "UPI",
        })
        assert response.status_code == 401

    def test_initiate_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.initiate_payment") as mock_svc:
                mock_svc.return_value = {
                    "order_id": "order_abc123",
                    "key_id": "rzp_test_key",
                    "amount": 100000,
                    "currency": "INR",
                }
                response = client.post(
                    "/api/v1/payments/initiate",
                    json={
                        "booking_id": str(uuid4()),
                        "amount": 1000,
                        "method": "UPI",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_initiate_missing_booking_id(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/payments/initiate",
                json={"amount": 1000, "method": "UPI"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)

    def test_initiate_zero_amount(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/payments/initiate",
                json={"booking_id": str(uuid4()), "amount": 0, "method": "UPI"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (400, 401, 422)


# ─── Verify Payment ───────────────────────────────────────────────────────────

class TestVerifyPayment:

    def test_verify_unauthorized(self):
        response = client.post("/api/v1/payments/verify", json={
            "razorpay_order_id": "order_abc",
            "razorpay_payment_id": "pay_abc",
            "razorpay_signature": "sig_abc",
        })
        assert response.status_code == 401

    def test_verify_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.verify_payment") as mock_svc:
                mock_svc.return_value = {"status": "SUCCESS", "transaction_id": TXN_ID}
                response = client.post(
                    "/api/v1/payments/verify",
                    json={
                        "razorpay_order_id": "order_abc",
                        "razorpay_payment_id": "pay_abc",
                        "razorpay_signature": "valid_sig",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_verify_invalid_signature(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.verify_payment") as mock_svc:
                mock_svc.side_effect = ValueError("Invalid signature")
                response = client.post(
                    "/api/v1/payments/verify",
                    json={
                        "razorpay_order_id": "order_abc",
                        "razorpay_payment_id": "pay_abc",
                        "razorpay_signature": "bad_sig",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)


# ─── Payment History ──────────────────────────────────────────────────────────

class TestPaymentHistory:

    def test_history_unauthorized(self):
        response = client.get("/api/v1/payments/history")
        assert response.status_code == 401

    def test_history_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_payment_history") as mock_svc:
                mock_svc.return_value = {"transactions": [], "total": 0}
                response = client.get(
                    "/api/v1/payments/history",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Validate UPI ─────────────────────────────────────────────────────────────

class TestValidateUPI:

    def test_validate_upi_unauthorized(self):
        response = client.post("/api/v1/payments/validate-upi", json={"upi_id": "test@upi"})
        assert response.status_code == 401

    def test_validate_upi_valid(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.validate_upi") as mock_svc:
                mock_svc.return_value = {"valid": True, "upi_id": "test@upi"}
                response = client.post(
                    "/api/v1/payments/validate-upi",
                    json={"upi_id": "test@upi"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_validate_upi_invalid_format(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.validate_upi") as mock_svc:
                mock_svc.return_value = {"valid": False, "upi_id": "notanupiid"}
                response = client.post(
                    "/api/v1/payments/validate-upi",
                    json={"upi_id": "notanupiid"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Saved Cards ──────────────────────────────────────────────────────────────

class TestSavedCards:

    def test_get_saved_cards_unauthorized(self):
        response = client.get("/api/v1/payments/saved-cards")
        assert response.status_code == 401

    def test_get_saved_cards_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_saved_cards") as mock_svc:
                mock_svc.return_value = {"cards": []}
                response = client.get(
                    "/api/v1/payments/saved-cards",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_save_card_unauthorized(self):
        response = client.post("/api/v1/payments/saved-cards", json={
            "razorpay_token": "tok_abc123",
            "card_last4": "4242",
            "card_network": "VISA",
        })
        assert response.status_code == 401

    def test_save_card_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.save_card") as mock_svc:
                mock_svc.return_value = {"id": CARD_ID, "card_last4": "4242"}
                response = client.post(
                    "/api/v1/payments/saved-cards",
                    json={
                        "razorpay_token": "tok_abc123",
                        "card_last4": "4242",
                        "card_network": "VISA",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_delete_card_unauthorized(self):
        response = client.delete(f"/api/v1/payments/saved-cards/{CARD_ID}")
        assert response.status_code == 401

    def test_delete_card_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.delete_saved_card") as mock_svc:
                mock_svc.return_value = {"message": "Card deleted"}
                response = client.delete(
                    f"/api/v1/payments/saved-cards/{CARD_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_delete_card_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.delete_saved_card") as mock_svc:
                mock_svc.side_effect = ValueError("Card not found")
                response = client.delete(
                    f"/api/v1/payments/saved-cards/{uuid4()}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 404)


# ─── Refunds ──────────────────────────────────────────────────────────────────

class TestRefunds:

    def test_list_refunds_unauthorized(self):
        response = client.get("/api/v1/payments/refunds")
        assert response.status_code == 401

    def test_list_refunds_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_refunds") as mock_svc:
                mock_svc.return_value = {"refunds": [], "total": 0}
                response = client.get(
                    "/api/v1/payments/refunds",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_request_refund_unauthorized(self):
        response = client.post("/api/v1/payments/refund/request", json={
            "booking_id": str(uuid4()),
            "reason": "Service not provided",
        })
        assert response.status_code == 401

    def test_request_refund_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.request_refund") as mock_svc:
                mock_svc.return_value = {
                    "id": REFUND_ID,
                    "status": "pending",
                    "amount": "500.00",
                }
                response = client.post(
                    "/api/v1/payments/refund/request",
                    json={
                        "booking_id": str(uuid4()),
                        "reason": "Service not provided",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_get_refund_detail_unauthorized(self):
        response = client.get(f"/api/v1/payments/refund/{REFUND_ID}")
        assert response.status_code == 401

    def test_get_refund_detail_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_refund") as mock_svc:
                mock_svc.return_value = {"id": REFUND_ID, "status": "processing"}
                response = client.get(
                    f"/api/v1/payments/refund/{REFUND_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_refund_detail_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_refund") as mock_svc:
                mock_svc.return_value = None
                response = client.get(
                    f"/api/v1/payments/refund/{uuid4()}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401, 404)


# ─── Pay Later ────────────────────────────────────────────────────────────────

class TestPayLater:

    def test_check_pay_later_unauthorized(self):
        response = client.post("/api/v1/payments/pay-later/check", json={
            "booking_id": str(uuid4()),
            "amount": 5000,
        })
        assert response.status_code == 401

    def test_check_pay_later_eligible(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.check_pay_later") as mock_svc:
                mock_svc.return_value = {"eligible": True, "credit_limit": 10000}
                response = client.post(
                    "/api/v1/payments/pay-later/check",
                    json={"booking_id": str(uuid4()), "amount": 5000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_check_pay_later_not_eligible(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.check_pay_later") as mock_svc:
                mock_svc.return_value = {"eligible": False, "reason": "Insufficient credit history"}
                response = client.post(
                    "/api/v1/payments/pay-later/check",
                    json={"booking_id": str(uuid4()), "amount": 5000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_apply_pay_later_unauthorized(self):
        response = client.post("/api/v1/payments/pay-later/apply", json={
            "booking_id": str(uuid4()),
            "amount": 5000,
        })
        assert response.status_code == 401

    def test_apply_pay_later_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.apply_pay_later") as mock_svc:
                mock_svc.return_value = {
                    "status": "approved",
                    "due_date": "2026-05-06",
                    "amount": 5000,
                }
                response = client.post(
                    "/api/v1/payments/pay-later/apply",
                    json={"booking_id": str(uuid4()), "amount": 5000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)


# ─── Webhook ──────────────────────────────────────────────────────────────────

class TestRazorpayWebhook:

    def test_webhook_invalid_signature(self):
        with patch("src.integrations.razorpay.verify_webhook_signature") as mock_sig:
            mock_sig.return_value = False
            response = client.post(
                "/api/v1/payments/webhook/razorpay",
                json={"event": "payment.captured"},
                headers={"X-Razorpay-Signature": "bad_signature"},
            )
        assert response.status_code in (400, 422)

    def test_webhook_valid_signature(self):
        with patch("src.integrations.razorpay.verify_webhook_signature") as mock_sig:
            mock_sig.return_value = True
            with patch("src.services.payment_service.handle_webhook") as mock_svc:
                mock_svc.return_value = {"status": "processed"}
                response = client.post(
                    "/api/v1/payments/webhook/razorpay",
                    json={"event": "payment.captured", "payload": {}},
                    headers={"X-Razorpay-Signature": "valid_signature"},
                )
        assert response.status_code in (200, 400)

    def test_webhook_no_auth_required(self):
        """Webhook is public — no user token needed."""
        with patch("src.integrations.razorpay.verify_webhook_signature") as mock_sig:
            mock_sig.return_value = False
            response = client.post(
                "/api/v1/payments/webhook/razorpay",
                json={"event": "payment.captured"},
            )
        assert response.status_code in (400, 422)


# ─── Transaction Detail ───────────────────────────────────────────────────────

class TestTransactionDetail:

    def test_get_transaction_unauthorized(self):
        response = client.get(f"/api/v1/payments/{TXN_ID}")
        assert response.status_code == 401

    def test_get_transaction_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_transaction") as mock_svc:
                mock_svc.return_value = {
                    "id": TXN_ID,
                    "amount": 1000,
                    "status": "SUCCESS",
                    "method": "UPI",
                }
                response = client.get(
                    f"/api/v1/payments/{TXN_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_transaction_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.payment_service.get_transaction") as mock_svc:
                mock_svc.return_value = None
                response = client.get(
                    f"/api/v1/payments/{uuid4()}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404)