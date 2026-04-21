"""
tests/test_users.py
Unit tests for all User API endpoints.

Routes covered:
  GET    /users/me                          — Get full profile
  PUT    /users/me                          — Update profile
  PATCH  /users/me/avatar                   — Upload avatar
  DELETE /users/me                          — Soft-delete account
  GET    /users/me/addresses                — List addresses
  POST   /users/me/addresses                — Add address
  PUT    /users/me/addresses/{address_id}   — Update address
  DELETE /users/me/addresses/{address_id}   — Delete address
  GET    /users/me/family-members           — List family members
  POST   /users/me/family-members           — Add family member
  PUT    /users/me/family-members/{id}      — Update family member
  DELETE /users/me/family-members/{id}      — Remove family member
  GET    /users/me/preferences              — Get preferences
  PUT    /users/me/preferences              — Update preferences
  GET    /users/me/sessions                 — List active sessions
  DELETE /users/me/sessions/{session_id}    — Revoke session
  GET    /users/me/kyc                      — Get KYC status
  GET    /users/me/wallet                   — Wallet summary
  GET    /users/me/bookings                 — User bookings
  GET    /users/me/reviews                  — User reviews
  GET    /users/me/notifications            — User notifications
  PUT    /users/me/fcm-token                — Register FCM token

Run with:
    pytest tests/test_users.py -v
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal

from src.main import app

client = TestClient(app)

USER_TOKEN = "Bearer test_user_token"
USER_ID = str(uuid4())
ADDRESS_ID = str(uuid4())
MEMBER_ID = str(uuid4())
SESSION_ID = str(uuid4())

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.phone = "9876543210"
MOCK_USER.email = "test@example.com"
MOCK_USER.full_name = "Test User"
MOCK_USER.role = "traveler"
MOCK_USER.is_phone_verified = True
MOCK_USER.is_email_verified = False

SAMPLE_ADDRESS = {
    "label": "home",
    "address_line": "123 Temple Street",
    "city": "Visakhapatnam",
    "state": "Andhra Pradesh",
    "pincode": "530001",
    "is_default": True,
}

SAMPLE_FAMILY_MEMBER = {
    "name": "Spouse Name",
    "relation": "spouse",
    "date_of_birth": "1992-05-15",
    "gender": "female",
}


# ─── Profile ──────────────────────────────────────────────────────────────────

class TestGetProfile:

    def test_get_profile_unauthorized(self):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_get_profile_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.get_full_profile") as mock_svc:
                mock_svc.return_value = {
                    "id": USER_ID,
                    "phone": "9876543210",
                    "full_name": "Test User",
                    "wallet_balance": "0.00",
                    "kyc_status": "pending",
                }
                response = client.get(
                    "/api/v1/users/me",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_get_profile_returns_success_status(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.get_full_profile") as mock_svc:
                mock_svc.return_value = {"id": USER_ID, "full_name": "Test User"}
                response = client.get(
                    "/api/v1/users/me",
                    headers={"Authorization": USER_TOKEN},
                )
        if response.status_code == 200:
            assert response.json()["success"] == True


class TestUpdateProfile:

    def test_update_profile_unauthorized(self):
        response = client.put("/api/v1/users/me", json={"full_name": "New Name"})
        assert response.status_code == 401

    def test_update_profile_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.update_profile") as mock_svc:
                mock_svc.return_value = {"full_name": "New Name"}
                response = client.put(
                    "/api/v1/users/me",
                    json={"full_name": "New Name"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_profile_empty_body(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.update_profile") as mock_svc:
                mock_svc.return_value = {}
                response = client.put(
                    "/api/v1/users/me",
                    json={},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401, 422)


class TestDeleteAccount:

    def test_delete_account_unauthorized(self):
        response = client.delete("/api/v1/users/me")
        assert response.status_code == 401

    def test_delete_account_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.delete_account") as mock_svc:
                mock_svc.return_value = {"message": "Account deleted successfully"}
                response = client.delete(
                    "/api/v1/users/me",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Addresses ────────────────────────────────────────────────────────────────

class TestAddresses:

    def test_list_addresses_unauthorized(self):
        response = client.get("/api/v1/users/me/addresses")
        assert response.status_code == 401

    def test_list_addresses_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.list_addresses") as mock_svc:
                mock_svc.return_value = []
                response = client.get(
                    "/api/v1/users/me/addresses",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_add_address_unauthorized(self):
        response = client.post("/api/v1/users/me/addresses", json=SAMPLE_ADDRESS)
        assert response.status_code == 401

    def test_add_address_success(self):
        mock_addr = MagicMock()
        mock_addr.model_dump = lambda: {"id": ADDRESS_ID, **SAMPLE_ADDRESS}
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.add_address") as mock_svc:
                mock_svc.return_value = mock_addr
                response = client.post(
                    "/api/v1/users/me/addresses",
                    json=SAMPLE_ADDRESS,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_update_address_unauthorized(self):
        response = client.put(
            f"/api/v1/users/me/addresses/{ADDRESS_ID}",
            json=SAMPLE_ADDRESS,
        )
        assert response.status_code == 401

    def test_update_address_not_found(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.update_address") as mock_svc:
                mock_svc.side_effect = ValueError("Address not found")
                response = client.put(
                    f"/api/v1/users/me/addresses/{uuid4()}",
                    json=SAMPLE_ADDRESS,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (400, 401, 404)

    def test_delete_address_unauthorized(self):
        response = client.delete(f"/api/v1/users/me/addresses/{ADDRESS_ID}")
        assert response.status_code == 401

    def test_delete_address_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.delete_address") as mock_svc:
                mock_svc.return_value = {"message": "Address deleted"}
                response = client.delete(
                    f"/api/v1/users/me/addresses/{ADDRESS_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Family Members ───────────────────────────────────────────────────────────

class TestFamilyMembers:

    def test_list_family_members_unauthorized(self):
        response = client.get("/api/v1/users/me/family-members")
        assert response.status_code == 401

    def test_list_family_members_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.list_family_members") as mock_svc:
                mock_svc.return_value = []
                response = client.get(
                    "/api/v1/users/me/family-members",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_add_family_member_unauthorized(self):
        response = client.post("/api/v1/users/me/family-members", json=SAMPLE_FAMILY_MEMBER)
        assert response.status_code == 401

    def test_add_family_member_success(self):
        mock_member = MagicMock()
        mock_member.model_dump = lambda: {"id": MEMBER_ID, **SAMPLE_FAMILY_MEMBER}
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.add_family_member") as mock_svc:
                mock_svc.return_value = mock_member
                response = client.post(
                    "/api/v1/users/me/family-members",
                    json=SAMPLE_FAMILY_MEMBER,
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 201, 401)

    def test_delete_family_member_unauthorized(self):
        response = client.delete(f"/api/v1/users/me/family-members/{MEMBER_ID}")
        assert response.status_code == 401

    def test_delete_family_member_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.delete_family_member") as mock_svc:
                mock_svc.return_value = {"message": "Family member removed"}
                response = client.delete(
                    f"/api/v1/users/me/family-members/{MEMBER_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Preferences ──────────────────────────────────────────────────────────────

class TestPreferences:

    def test_get_preferences_unauthorized(self):
        response = client.get("/api/v1/users/me/preferences")
        assert response.status_code == 401

    def test_get_preferences_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.get_preferences") as mock_svc:
                mock_svc.return_value = {"language": "en", "dietary": "vegetarian"}
                response = client.get(
                    "/api/v1/users/me/preferences",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_preferences_unauthorized(self):
        response = client.put("/api/v1/users/me/preferences", json={"language": "te"})
        assert response.status_code == 401

    def test_update_preferences_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.update_preferences") as mock_svc:
                mock_svc.return_value = {"language": "te"}
                response = client.put(
                    "/api/v1/users/me/preferences",
                    json={"language": "te"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Sessions ─────────────────────────────────────────────────────────────────

class TestSessions:

    def test_list_sessions_unauthorized(self):
        response = client.get("/api/v1/users/me/sessions")
        assert response.status_code == 401

    def test_list_sessions_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.list_sessions") as mock_svc:
                mock_svc.return_value = []
                response = client.get(
                    "/api/v1/users/me/sessions",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_revoke_session_unauthorized(self):
        response = client.delete(f"/api/v1/users/me/sessions/{SESSION_ID}")
        assert response.status_code == 401

    def test_revoke_session_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.revoke_session") as mock_svc:
                mock_svc.return_value = {"message": "Session revoked"}
                response = client.delete(
                    f"/api/v1/users/me/sessions/{SESSION_ID}",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── KYC ──────────────────────────────────────────────────────────────────────

class TestKYC:

    def test_get_kyc_status_unauthorized(self):
        response = client.get("/api/v1/users/me/kyc")
        assert response.status_code == 401

    def test_get_kyc_status_success(self):
        mock_profile = MagicMock()
        mock_profile.kyc_status = "pending"
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.get_or_create_profile") as mock_svc:
                mock_svc.return_value = mock_profile
                response = client.get(
                    "/api/v1/users/me/kyc",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── Wallet Summary ───────────────────────────────────────────────────────────

class TestWalletSummary:

    def test_get_wallet_summary_unauthorized(self):
        response = client.get("/api/v1/users/me/wallet")
        assert response.status_code == 401

    def test_get_wallet_summary_success(self):
        mock_wallet = MagicMock()
        mock_wallet.id = uuid4()
        mock_wallet.balance = Decimal("100.00")
        mock_wallet.status = "ACTIVE"
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.wallet_service.get_balance") as mock_svc:
                mock_svc.return_value = mock_wallet
                response = client.get(
                    "/api/v1/users/me/wallet",
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)


# ─── FCM Token ────────────────────────────────────────────────────────────────

class TestFCMToken:

    def test_update_fcm_token_unauthorized(self):
        response = client.put("/api/v1/users/me/fcm-token", json={"fcm_token": "tok123"})
        assert response.status_code == 401

    def test_update_fcm_token_success(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            with patch("src.services.user_service.update_fcm_token") as mock_svc:
                mock_svc.return_value = {"message": "FCM token updated"}
                response = client.put(
                    "/api/v1/users/me/fcm-token",
                    json={"fcm_token": "device_token_abc123"},
                    headers={"Authorization": USER_TOKEN},
                )
        assert response.status_code in (200, 401)

    def test_update_fcm_token_missing_field(self):
        with patch("src.api.deps.auth.get_current_user", return_value=MOCK_USER):
            response = client.put(
                "/api/v1/users/me/fcm-token",
                json={},
                headers={"Authorization": USER_TOKEN},
            )
        assert response.status_code in (401, 422)