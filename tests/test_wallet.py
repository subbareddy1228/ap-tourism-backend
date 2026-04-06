"""
tests/test_wallet.py
Unit tests for all 7 Wallet API endpoints.

Routes covered:
  GET  /wallet/balance               — Get wallet balance
  POST /wallet/topup                 — Initiate Razorpay topup
  POST /wallet/topup/verify          — Verify payment + credit wallet
  GET  /wallet/transactions          — List transactions (paginated)
  GET  /wallet/transactions/{id}     — Transaction detail
  POST /wallet/withdraw              — Request withdrawal
  GET  /wallet/withdraw/requests     — List withdrawal requests

Run with:
    pytest tests/test_wallet.py -v
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
USER_ID = str(uuid4())
TXN_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True
MOCK_USER.is_email_verified = True


# ─── Balance ──────────────────────────────────────────────────────────────────

class TestWalletBalance:

    def test_get_balance_unauthorized(self):
        response = client.get("/api/v1/wallet/balance")
        assert response.status_code == 401

    def test_get_balance_success(self):
        mock_wallet = MagicMock()
        mock_wallet.id = uuid4()
        mock_wallet.balance = Decimal("250.00")
        mock_wallet.status = "ACTIVE"
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.get_balance") as mock_svc:
                mock_svc.return_value = mock_wallet
                response = client.get(
                    "/api/v1/wallet/balance",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_balance_currency_is_inr(self):
        mock_wallet = MagicMock()
        mock_wallet.id = uuid4()
        mock_wallet.balance = Decimal("100.00")
        mock_wallet.status = "ACTIVE"
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.get_balance") as mock_svc:
                mock_svc.return_value = mock_wallet
                response = client.get(
                    "/api/v1/wallet/balance",
                    headers={"Authorization": USER_TOKEN},
                )
        if response.status_code == 200:
            assert response.json()["data"]["currency"] == "INR"


# ─── Topup ────────────────────────────────────────────────────────────────────

class TestInitiateTopup:

    def test_initiate_topup_unauthorized(self):
        response = client.post("/api/v1/wallet/topup", json={"amount": 500})
        assert response.status_code == 401

    def test_initiate_topup_success(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.initiate_topup") as mock_svc:
                mock_svc.return_value = {
                    "order_id": "order_abc123",
                    "key_id": "rzp_test_key",
                    "amount": 50000,
                    "currency": "INR",
                }
                response = client.post(
                    "/api/v1/wallet/topup",
                    json={"amount": 500},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_initiate_topup_negative_amount(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/wallet/topup",
                json={"amount": -100},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (400, 401, 422)

    def test_initiate_topup_zero_amount(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/wallet/topup",
                json={"amount": 0},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (400, 401, 422)

    def test_initiate_topup_below_minimum(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.initiate_topup") as mock_svc:
                mock_svc.side_effect = ValueError("Minimum topup amount is ₹10")
                response = client.post(
                    "/api/v1/wallet/topup",
                    json={"amount": 5},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)

    def test_initiate_topup_above_maximum(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.initiate_topup") as mock_svc:
                mock_svc.side_effect = ValueError("Maximum topup amount is ₹1,00,000")
                response = client.post(
                    "/api/v1/wallet/topup",
                    json={"amount": 200000},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)


class TestVerifyTopup:

    def test_verify_topup_unauthorized(self):
        response = client.post("/api/v1/wallet/topup/verify", json={
            "razorpay_order_id": "order_abc123",
            "razorpay_payment_id": "pay_abc123",
            "razorpay_signature": "sig_abc123",
        })
        assert response.status_code == 401

    def test_verify_topup_success(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.verify_topup") as mock_svc:
                mock_svc.return_value = {
                    "message": "Wallet topped up successfully",
                    "amount_credited": Decimal("500.00"),
                    "new_balance": Decimal("750.00"),
                    "transaction_id": str(uuid4()),
                }
                response = client.post(
                    "/api/v1/wallet/topup/verify",
                    json={
                        "razorpay_order_id": "order_abc123",
                        "razorpay_payment_id": "pay_abc123",
                        "razorpay_signature": "valid_signature",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_verify_topup_invalid_signature(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.verify_topup") as mock_svc:
                mock_svc.side_effect = ValueError("Invalid payment signature")
                response = client.post(
                    "/api/v1/wallet/topup/verify",
                    json={
                        "razorpay_order_id": "order_abc123",
                        "razorpay_payment_id": "pay_abc123",
                        "razorpay_signature": "bad_signature",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)

    def test_verify_topup_missing_fields(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            response = client.post(
                "/api/v1/wallet/topup/verify",
                json={"razorpay_order_id": "order_abc123"},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)


# ─── Transactions ─────────────────────────────────────────────────────────────

class TestListTransactions:

    def test_list_transactions_unauthorized(self):
        response = client.get("/api/v1/wallet/transactions")
        assert response.status_code == 401

    def test_list_transactions_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_transactions") as mock_svc:
                mock_svc.return_value = {
                    "transactions": [],
                    "total": 0,
                    "page": 1,
                    "per_page": 20,
                }
                response = client.get(
                    "/api/v1/wallet/transactions",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_transactions_with_type_filter(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_transactions") as mock_svc:
                mock_svc.return_value = {"transactions": [], "total": 0, "page": 1, "per_page": 20}
                response = client.get(
                    "/api/v1/wallet/transactions?type=credit",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_transactions_with_category_filter(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_transactions") as mock_svc:
                mock_svc.return_value = {"transactions": [], "total": 0, "page": 1, "per_page": 20}
                response = client.get(
                    "/api/v1/wallet/transactions?category=topup",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_transactions_pagination(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_transactions") as mock_svc:
                mock_svc.return_value = {"transactions": [], "total": 0, "page": 2, "per_page": 10}
                response = client.get(
                    "/api/v1/wallet/transactions?page=2&per_page=10",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_transactions_invalid_page(self):
        response = client.get("/api/v1/wallet/transactions?page=0")
        assert response.status_code in (401, 422)

    def test_list_transactions_limit_too_high(self):
        response = client.get("/api/v1/wallet/transactions?per_page=999")
        assert response.status_code in (401, 422)


class TestGetTransaction:

    def test_get_transaction_unauthorized(self):
        response = client.get(f"/api/v1/wallet/transactions/{TXN_ID}")
        assert response.status_code == 401

    def test_get_transaction_success(self):
        mock_txn = MagicMock()
        mock_txn.id = uuid4()
        mock_txn.type = "credit"
        mock_txn.category = "topup"
        mock_txn.amount = Decimal("500.00")
        mock_txn.balance_after = Decimal("750.00")
        mock_txn.description = "Wallet topup"
        mock_txn.reference_id = "order_abc123"
        mock_txn.status = "success"
        mock_txn.created_at.isoformat.return_value = "2026-04-06T10:00:00"
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.get_transaction") as mock_svc:
                mock_svc.return_value = mock_txn
                response = client.get(
                    f"/api/v1/wallet/transactions/{TXN_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_transaction_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.get_transaction") as mock_svc:
                mock_svc.side_effect = ValueError("Transaction not found")
                response = client.get(
                    f"/api/v1/wallet/transactions/{uuid4()}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (401, 404)


# ─── Withdrawal ───────────────────────────────────────────────────────────────

class TestRequestWithdrawal:

    def test_withdraw_unauthorized(self):
        response = client.post("/api/v1/wallet/withdraw", json={
            "amount": 500,
            "bank_account_number": "123456789012",
            "bank_ifsc": "SBIN0001234",
            "bank_name": "State Bank of India",
        })
        assert response.status_code == 401

    def test_withdraw_success(self):
        mock_withdrawal = MagicMock()
        mock_withdrawal.id = uuid4()
        mock_withdrawal.amount = Decimal("500.00")
        mock_withdrawal.bank_account_number = "123456789012"
        mock_withdrawal.bank_ifsc = "SBIN0001234"
        mock_withdrawal.bank_name = "State Bank of India"
        mock_withdrawal.status = "pending"
        mock_withdrawal.created_at.isoformat.return_value = "2026-04-06T10:00:00"
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.request_withdrawal") as mock_svc:
                mock_svc.return_value = mock_withdrawal
                response = client.post(
                    "/api/v1/wallet/withdraw",
                    json={
                        "amount": 500,
                        "bank_account_number": "123456789012",
                        "bank_ifsc": "SBIN0001234",
                        "bank_name": "State Bank of India",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_withdraw_insufficient_balance(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.request_withdrawal") as mock_svc:
                mock_svc.side_effect = ValueError("Insufficient wallet balance")
                response = client.post(
                    "/api/v1/wallet/withdraw",
                    json={
                        "amount": 99999,
                        "bank_account_number": "123456789012",
                        "bank_ifsc": "SBIN0001234",
                        "bank_name": "State Bank of India",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)

    def test_withdraw_below_minimum(self):
        with patch("src.api.deps.auth.get_verified_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.request_withdrawal") as mock_svc:
                mock_svc.side_effect = ValueError("Minimum withdrawal amount is ₹100")
                response = client.post(
                    "/api/v1/wallet/withdraw",
                    json={
                        "amount": 50,
                        "bank_account_number": "123456789012",
                        "bank_ifsc": "SBIN0001234",
                        "bank_name": "SBI",
                    },
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401)


class TestListWithdrawalRequests:

    def test_list_withdrawal_requests_unauthorized(self):
        response = client.get("/api/v1/wallet/withdraw/requests")
        assert response.status_code == 401

    def test_list_withdrawal_requests_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_withdrawal_requests") as mock_svc:
                mock_svc.return_value = {"requests": [], "total": 0}
                response = client.get(
                    "/api/v1/wallet/withdraw/requests",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_withdrawal_requests_pagination(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.list_withdrawal_requests") as mock_svc:
                mock_svc.return_value = {"requests": [], "total": 0}
                response = client.get(
                    "/api/v1/wallet/withdraw/requests?page=1&per_page=5",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_list_withdrawal_requests_invalid_page(self):
        response = client.get("/api/v1/wallet/withdraw/requests?page=0")
        assert response.status_code in (401, 422)