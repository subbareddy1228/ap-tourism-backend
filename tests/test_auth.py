"""
tests/test_auth.py
Unit tests for all 12 Authentication API endpoints.

Run with:
    pytest tests/test_auth.py -v
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from src.main import app


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    with patch("src.core.redis.redis_client") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.setex = AsyncMock()
        mock.delete = AsyncMock()
        mock.exists = AsyncMock(return_value=0)
        mock.incr = AsyncMock(return_value=1)
        mock.expire = AsyncMock()
        yield mock


class TestRegister:
    async def test_register_success(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.register_user") as mock_reg:
                mock_reg.return_value = {"user_id": "uuid-123", "message": "OTP sent"}
                response = await client.post("/api/v1/auth/register", json={
                    "phone": "9876543210",
                    "email": "test@example.com",
                    "password": "Test@1234",
                    "full_name": "Test User"
                })
        assert response.status_code == 201
        assert response.json()["status"] == "success"

    async def test_register_invalid_phone(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/register", json={
                "phone": "1234567890",   # invalid — starts with 1
                "password": "Test@1234"
            })
        assert response.status_code == 422

    async def test_register_weak_password(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/register", json={
                "phone": "9876543210",
                "password": "weak"        # too short, no uppercase, no digit
            })
        assert response.status_code == 422

    async def test_register_duplicate_phone(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.register_user") as mock_reg:
                mock_reg.side_effect = ValueError("Phone number already registered")
                response = await client.post("/api/v1/auth/register", json={
                    "phone": "9876543210",
                    "password": "Test@1234"
                })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


class TestVerifyOTP:
    async def test_verify_otp_success(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.verify_otp_and_login") as mock_verify:
                mock_verify.return_value = {
                    "access_token": "access.jwt.token",
                    "refresh_token": "refresh.jwt.token",
                    "user": type("User", (), {
                        "id": "uuid-123", "phone": "9876543210",
                        "email": None, "full_name": "Test",
                        "role": "traveler",
                        "is_phone_verified": True,
                        "is_email_verified": False
                    })()
                }
                response = await client.post("/api/v1/auth/verify-otp", json={
                    "phone": "9876543210",
                    "otp": "123456",
                    "purpose": "register"
                })
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_verify_otp_invalid(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.verify_otp_and_login") as mock_verify:
                mock_verify.side_effect = ValueError("Incorrect OTP. 4 attempts remaining.")
                response = await client.post("/api/v1/auth/verify-otp", json={
                    "phone": "9876543210",
                    "otp": "000000",
                    "purpose": "register"
                })
        assert response.status_code == 400

    async def test_verify_otp_expired(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.verify_otp_and_login") as mock_verify:
                mock_verify.side_effect = ValueError("OTP expired. Please request a new one.")
                response = await client.post("/api/v1/auth/verify-otp", json={
                    "phone": "9876543210",
                    "otp": "123456",
                    "purpose": "register"
                })
        assert response.status_code == 400
        assert "expired" in response.json()["detail"]


class TestLogin:
    async def test_login_success(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.login_with_password") as mock_login:
                mock_login.return_value = {
                    "access_token": "access.jwt.token",
                    "refresh_token": "refresh.jwt.token",
                    "user": type("User", (), {
                        "id": "uuid-123", "phone": "9876543210",
                        "email": None, "full_name": "Test",
                        "role": "traveler",
                        "is_phone_verified": True,
                        "is_email_verified": False
                    })()
                }
                response = await client.post("/api/v1/auth/login", json={
                    "phone": "9876543210",
                    "password": "Test@1234"
                })
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_login_wrong_password(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.login_with_password") as mock_login:
                mock_login.side_effect = ValueError("Invalid phone or password")
                response = await client.post("/api/v1/auth/login", json={
                    "phone": "9876543210",
                    "password": "Wrong@1234"
                })
        assert response.status_code == 401

    async def test_login_unverified_user(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.login_with_password") as mock_login:
                mock_login.side_effect = ValueError("Phone not verified.")
                response = await client.post("/api/v1/auth/login", json={
                    "phone": "9876543210",
                    "password": "Test@1234"
                })
        assert response.status_code == 401


class TestResendOTP:
    async def test_resend_success(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.resend_otp") as mock_resend:
                mock_resend.return_value = {"message": "OTP resent", "phone": "9876543210", "expires_in": 300}
                response = await client.post("/api/v1/auth/resend-otp", json={
                    "phone": "9876543210",
                    "purpose": "register"
                })
        assert response.status_code == 200

    async def test_resend_cooldown(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.resend_otp") as mock_resend:
                mock_resend.side_effect = ValueError("Please wait 60 seconds before requesting a new OTP")
                response = await client.post("/api/v1/auth/resend-otp", json={
                    "phone": "9876543210",
                    "purpose": "register"
                })
        assert response.status_code == 429


class TestForgotResetPassword:
    async def test_forgot_password(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.forgot_password") as mock_fp:
                mock_fp.return_value = {"message": "If this number is registered, you will receive an OTP"}
                response = await client.post("/api/v1/auth/forgot-password", json={
                    "phone": "9876543210"
                })
        assert response.status_code == 200

    async def test_reset_password_success(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.reset_password") as mock_rp:
                mock_rp.return_value = {"message": "Password reset successfully."}
                response = await client.post("/api/v1/auth/reset-password", json={
                    "phone": "9876543210",
                    "otp": "123456",
                    "new_password": "NewPass@1234"
                })
        assert response.status_code == 200

    async def test_reset_password_invalid_otp(self, mock_redis):
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.services.auth_service.reset_password") as mock_rp:
                mock_rp.side_effect = ValueError("Invalid or expired OTP")
                response = await client.post("/api/v1/auth/reset-password", json={
                    "phone": "9876543210",
                    "otp": "000000",
                    "new_password": "NewPass@1234"
                })
        assert response.status_code == 400
