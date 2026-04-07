import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app

client = TestClient(app)


class TestGlobalSearch:

    @patch("src.api.v1.endpoints.search.global_search", new_callable=AsyncMock)
    def test_search_with_query(self, mock_search):
        mock_search.return_value = {"destinations": [], "packages": []}

        response = client.get("/api/v1/search?q=tirupati")

        assert response.status_code == 200

    @patch("src.api.v1.endpoints.search.global_search", new_callable=AsyncMock)
    def test_search_empty_query(self, mock_search):
        mock_search.return_value = {"destinations": [], "packages": []}

        response = client.get("/api/v1/search?q=")

        assert response.status_code == 200

    @patch("src.api.v1.endpoints.search.global_search", new_callable=AsyncMock)
    def test_search_special_characters(self, mock_search):
        mock_search.return_value = {"destinations": [], "packages": []}

        response = client.get("/api/v1/search?q=@#$")

        assert response.status_code == 200

    @patch("src.api.v1.endpoints.search.global_search", new_callable=AsyncMock)
    def test_search_long_query(self, mock_search):
        mock_search.return_value = {"destinations": [], "packages": []}

        response = client.get("/api/v1/search?q=" + "tirupati" * 20)

        assert response.status_code == 200


class TestSearchSuggestions:

    @patch("src.api.v1.endpoints.search.get_suggestions", new_callable=AsyncMock)
    def test_suggestions_success(self, mock_svc):
        mock_svc.return_value = ["Tirupati", "Tirumala"]

        response = client.get("/api/v1/search/suggestions?q=Tiru")

        assert response.status_code == 200

    @patch("src.api.v1.endpoints.search.get_suggestions", new_callable=AsyncMock)
    def test_suggestions_short_query(self, mock_svc):
        mock_svc.return_value = []

        response = client.get("/api/v1/search/suggestions?q=T")

        assert response.status_code == 200


class TestSearchAutocomplete:

    @patch("src.api.v1.endpoints.search.get_autocomplete", new_callable=AsyncMock)
    def test_autocomplete_success(self, mock_svc):
        mock_svc.return_value = ["Araku Valley"]

        response = client.get("/api/v1/search/autocomplete?q=Araku")

        assert response.status_code == 200

    @patch("src.api.v1.endpoints.search.get_autocomplete", new_callable=AsyncMock)
    def test_autocomplete_empty_result(self, mock_svc):
        mock_svc.return_value = []

        response = client.get("/api/v1/search/autocomplete?q=xyz")

        assert response.status_code == 200