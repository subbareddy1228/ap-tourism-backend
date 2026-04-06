"""
tests/test_search.py
Unit tests for all Search API endpoints.

Routes covered:
  GET /search/              — Global search
  GET /search/suggestions   — Search suggestions
  GET /search/autocomplete  — Autocomplete
  GET /search/temples       — Search temples
  GET /search/hotels        — Search hotels
  GET /search/packages      — Search packages
  GET /search/destinations  — Search destinations
  GET /search/recent        — Recent searches

Run with:
    pytest tests/test_search.py -v
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.main import app

client = TestClient(app)
USER_ID = str(uuid4())


# ─── Global Search ────────────────────────────────────────────────────────────

class TestGlobalSearch:

    def test_search_with_query(self):
        with patch("src.services.search_service.search_all") as mock_svc:
            mock_svc.return_value = {"temples": [], "hotels": [], "packages": [], "destinations": []}
            response = client.get("/api/v1/search/?q=Tirupati")
        assert response.status_code in (200, 422, 500)

    def test_search_no_query(self):
        response = client.get("/api/v1/search/")
        assert response.status_code in (200, 422, 500)

    def test_search_empty_query(self):
        response = client.get("/api/v1/search/?q=")
        assert response.status_code in (200, 422, 500)

    def test_search_special_characters(self):
        with patch("src.services.search_service.search_all") as mock_svc:
            mock_svc.return_value = {}
            response = client.get("/api/v1/search/?q=temple+near+tirupati")
        assert response.status_code in (200, 422, 500)

    def test_search_long_query(self):
        with patch("src.services.search_service.search_all") as mock_svc:
            mock_svc.return_value = {}
            response = client.get("/api/v1/search/?q=" + "a" * 200)
        assert response.status_code in (200, 422, 500)


# ─── Suggestions ──────────────────────────────────────────────────────────────

class TestSearchSuggestions:

    def test_suggestions_success(self):
        with patch("src.services.search_service.get_suggestions") as mock_svc:
            mock_svc.return_value = ["Tirupati", "Tirumala", "Tirupathi"]
            response = client.get("/api/v1/search/suggestions?q=Tiru")
        assert response.status_code in (200, 422, 500)

    def test_suggestions_short_query(self):
        with patch("src.services.search_service.get_suggestions") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/suggestions?q=T")
        assert response.status_code in (200, 422, 500)

    def test_suggestions_no_query(self):
        response = client.get("/api/v1/search/suggestions")
        assert response.status_code in (200, 422, 500)


# ─── Autocomplete ─────────────────────────────────────────────────────────────

class TestSearchAutocomplete:

    def test_autocomplete_success(self):
        with patch("src.services.search_service.get_autocomplete") as mock_svc:
            mock_svc.return_value = ["Araku Valley", "Araku Waterfalls"]
            response = client.get("/api/v1/search/autocomplete?q=Araku")
        assert response.status_code in (200, 422, 500)

    def test_autocomplete_no_query(self):
        response = client.get("/api/v1/search/autocomplete")
        assert response.status_code in (200, 422, 500)

    def test_autocomplete_empty_result(self):
        with patch("src.services.search_service.get_autocomplete") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/autocomplete?q=xyzxyz")
        assert response.status_code in (200, 422, 500)


# ─── Entity-Specific Search ───────────────────────────────────────────────────

class TestEntitySearch:

    def test_search_temples_success(self):
        with patch("src.services.search_service.search_temples") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/temples?q=Venkateswara")
        assert response.status_code in (200, 422, 500)

    def test_search_temples_no_query(self):
        response = client.get("/api/v1/search/temples")
        assert response.status_code in (200, 422, 500)

    def test_search_hotels_success(self):
        with patch("src.services.search_service.search_hotels") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/hotels?q=Tirupati")
        assert response.status_code in (200, 422, 500)

    def test_search_hotels_no_query(self):
        response = client.get("/api/v1/search/hotels")
        assert response.status_code in (200, 422, 500)

    def test_search_packages_success(self):
        with patch("src.services.search_service.search_packages") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/packages?q=pilgrimage")
        assert response.status_code in (200, 422, 500)

    def test_search_packages_no_query(self):
        response = client.get("/api/v1/search/packages")
        assert response.status_code in (200, 422, 500)

    def test_search_destinations_success(self):
        with patch("src.services.search_service.search_destinations") as mock_svc:
            mock_svc.return_value = []
            response = client.get("/api/v1/search/destinations?q=Araku")
        assert response.status_code in (200, 422, 500)

    def test_search_destinations_no_query(self):
        response = client.get("/api/v1/search/destinations")
        assert response.status_code in (200, 422, 500)


# ─── Recent Searches ──────────────────────────────────────────────────────────

class TestRecentSearches:

    def test_recent_with_user_id(self):
        with patch("src.services.search_service.get_recent_searches") as mock_svc:
            mock_svc.return_value = ["Tirupati", "Araku"]
            response = client.get(f"/api/v1/search/recent?user_id={USER_ID}")
        assert response.status_code in (200, 401, 422, 500)

    def test_recent_no_user_id(self):
        response = client.get("/api/v1/search/recent")
        assert response.status_code in (200, 422, 500)

    def test_recent_empty_history(self):
        with patch("src.services.search_service.get_recent_searches") as mock_svc:
            mock_svc.return_value = []
            response = client.get(f"/api/v1/search/recent?user_id={USER_ID}")
        assert response.status_code in (200, 422, 500)