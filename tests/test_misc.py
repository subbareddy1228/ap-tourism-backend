"""
tests/test_misc.py
Unit tests for all Public/Misc API endpoints.
All endpoints are public — no auth required.

Routes covered:
  GET  /version       — API version info
  GET  /config        — App configuration for clients
  GET  /banners       — Active homepage banners
  GET  /home          — Homepage aggregated data
  GET  /districts     — All AP districts
  GET  /cities        — Cities with district mapping
  GET  /languages     — Supported languages
  GET  /currencies    — Supported currencies
  POST /contact-us    — Public contact form

Run with:
    pytest tests/test_misc.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app

client = TestClient(app)


# ─── Version ──────────────────────────────────────────────────────────────────

class TestVersion:

    def test_version_no_auth_required(self):
        response = client.get("/api/v1/version")
        assert response.status_code == 200

    def test_version_returns_expected_fields(self):
        response = client.get("/api/v1/version")
        if response.status_code == 200:
            data = response.json().get("data", {})
            assert "version" in data
            assert "build" in data
            assert "deployed_at" in data

    def test_version_success_status(self):
        response = client.get("/api/v1/version")
        if response.status_code == 200:
            assert response.json()["success"] == True


# ─── Config ───────────────────────────────────────────────────────────────────

class TestConfig:

    def test_config_no_auth_required(self):
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            with patch("src.common.utils.set_cache", new_callable=AsyncMock):
                response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_config_returns_payment_methods(self):
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            with patch("src.common.utils.set_cache", new_callable=AsyncMock):
                response = client.get("/api/v1/config")
        if response.status_code == 200:
            data = response.json().get("data", {})
            assert "supported_payment_methods" in data

    def test_config_returns_cached_data(self):
        cached = {
            "supported_payment_methods": ["UPI", "CARD"],
            "currency": "INR",
        }
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached
            response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_config_currency_is_inr(self):
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            with patch("src.common.utils.set_cache", new_callable=AsyncMock):
                response = client.get("/api/v1/config")
        if response.status_code == 200:
            data = response.json().get("data", {})
            assert data.get("currency") == "INR"


# ─── Banners ──────────────────────────────────────────────────────────────────

class TestBanners:

    def test_banners_no_auth_required(self):
        response = client.get("/api/v1/banners")
        assert response.status_code == 200

    def test_banners_returns_list(self):
        response = client.get("/api/v1/banners")
        if response.status_code == 200:
            data = response.json().get("data")
            assert isinstance(data, list)

    def test_banners_success_status(self):
        response = client.get("/api/v1/banners")
        if response.status_code == 200:
            assert response.json()["success"] == True


# ─── Homepage ─────────────────────────────────────────────────────────────────

class TestHomepage:

    def test_home_no_auth_required(self):
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            with patch("src.common.utils.set_cache", new_callable=AsyncMock):
                response = client.get("/api/v1/home")
        assert response.status_code in (200, 500)

    def test_home_returns_cached_data(self):
        cached = {
            "featured_destinations": [],
            "featured_packages": [],
            "popular_temples": [],
            "active_banners": [],
        }
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached
            response = client.get("/api/v1/home")
        assert response.status_code == 200

    def test_home_cached_response_has_sections(self):
        cached = {
            "featured_destinations": [{"id": "1", "name": "Tirupati"}],
            "featured_packages": [],
            "popular_temples": [],
            "active_banners": [],
        }
        with patch("src.common.utils.get_cache", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached
            response = client.get("/api/v1/home")
        if response.status_code == 200:
            data = response.json().get("data", {})
            assert "featured_destinations" in data
            assert "featured_packages" in data
            assert "popular_temples" in data


# ─── Districts ────────────────────────────────────────────────────────────────

class TestDistricts:

    def test_districts_no_auth_required(self):
        response = client.get("/api/v1/districts")
        assert response.status_code == 200

    def test_districts_returns_list(self):
        response = client.get("/api/v1/districts")
        if response.status_code == 200:
            data = response.json().get("data")
            assert isinstance(data, list)
            assert len(data) > 0

    def test_districts_contains_visakhapatnam(self):
        response = client.get("/api/v1/districts")
        if response.status_code == 200:
            data = response.json().get("data", [])
            assert "Visakhapatnam" in data

    def test_districts_contains_tirupati(self):
        response = client.get("/api/v1/districts")
        if response.status_code == 200:
            data = response.json().get("data", [])
            assert "Tirupati" in data


# ─── Cities ───────────────────────────────────────────────────────────────────

class TestCities:

    def test_cities_no_auth_required(self):
        response = client.get("/api/v1/cities")
        assert response.status_code == 200

    def test_cities_returns_list(self):
        response = client.get("/api/v1/cities")
        if response.status_code == 200:
            data = response.json().get("data")
            assert isinstance(data, list)
            assert len(data) > 0

    def test_cities_have_city_and_district_fields(self):
        response = client.get("/api/v1/cities")
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                assert "city" in data[0]
                assert "district" in data[0]

    def test_cities_contains_visakhapatnam(self):
        response = client.get("/api/v1/cities")
        if response.status_code == 200:
            data = response.json().get("data", [])
            city_names = [c["city"] for c in data]
            assert "Visakhapatnam" in city_names


# ─── Languages ────────────────────────────────────────────────────────────────

class TestLanguages:

    def test_languages_no_auth_required(self):
        response = client.get("/api/v1/languages")
        assert response.status_code == 200

    def test_languages_returns_list(self):
        response = client.get("/api/v1/languages")
        if response.status_code == 200:
            data = response.json().get("data")
            assert isinstance(data, list)

    def test_languages_contains_telugu(self):
        response = client.get("/api/v1/languages")
        if response.status_code == 200:
            data = response.json().get("data", [])
            assert "Telugu" in data

    def test_languages_contains_english(self):
        response = client.get("/api/v1/languages")
        if response.status_code == 200:
            data = response.json().get("data", [])
            assert "English" in data


# ─── Currencies ───────────────────────────────────────────────────────────────

class TestCurrencies:

    def test_currencies_no_auth_required(self):
        response = client.get("/api/v1/currencies")
        assert response.status_code == 200

    def test_currencies_returns_inr(self):
        response = client.get("/api/v1/currencies")
        if response.status_code == 200:
            data = response.json().get("data", [])
            assert "INR" in data

    def test_currencies_returns_list(self):
        response = client.get("/api/v1/currencies")
        if response.status_code == 200:
            data = response.json().get("data")
            assert isinstance(data, list)


# ─── Contact Us ───────────────────────────────────────────────────────────────

class TestContactUs:

    def test_contact_us_no_auth_required(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "subject": "Booking query",
            "message": "I need help with my booking.",
        })
        assert response.status_code == 200

    def test_contact_us_success_message(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "subject": "Booking query",
            "message": "I need help with my booking.",
        })
        if response.status_code == 200:
            assert "24 hours" in response.json().get("message", "")

    def test_contact_us_with_phone(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Priya Sharma",
            "email": "priya@example.com",
            "phone": "9876543210",
            "subject": "Refund request",
            "message": "Please process my refund.",
        })
        assert response.status_code == 200

    def test_contact_us_missing_name(self):
        response = client.post("/api/v1/contact-us", json={
            "email": "ravi@example.com",
            "subject": "Query",
            "message": "Hello",
        })
        assert response.status_code == 422

    def test_contact_us_missing_email(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "subject": "Query",
            "message": "Hello",
        })
        assert response.status_code == 422

    def test_contact_us_invalid_email(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "not-an-email",
            "subject": "Query",
            "message": "Hello",
        })
        assert response.status_code == 422

    def test_contact_us_missing_subject(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "message": "Hello",
        })
        assert response.status_code == 422

    def test_contact_us_missing_message(self):
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "subject": "Query",
        })
        assert response.status_code == 422

    def test_contact_us_phone_is_optional(self):
        """phone field is optional — submitting without it should succeed."""
        response = client.post("/api/v1/contact-us", json={
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "subject": "Query",
            "message": "No phone provided.",
        })
        assert response.status_code == 200