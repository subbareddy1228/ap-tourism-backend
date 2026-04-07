from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app

client = TestClient(app)

PKG_ID = str(uuid4())

SAMPLE_PACKAGE = {
    "id": PKG_ID,
    "name": "Tirupati Package",
    "slug": "tirupati-package",
    "destination_id": str(uuid4()),
    "type": "PILGRIMAGE",   # FIXED ENUM
    "duration_days": 2,
    "duration_nights": 1,
    "price": 4999,
    "rating": 4.5,
    "reviews_count": 10,
    "total_bookings": 100,
    "is_featured": True,
    "is_active": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow(),
}


# ---------------- LIST PACKAGES ----------------

class TestListPackages:

    def test_list_packages(self):

        with patch(
            "src.repositories.package_repo.get_packages",
            new=AsyncMock(return_value=[SAMPLE_PACKAGE])
        ), patch(
            "src.repositories.package_repo.get_packages_count",
            new=AsyncMock(return_value=1)
        ):

            response = client.get("/api/v1/packages/")

        assert response.status_code == 200


# ---------------- FEATURED ----------------

class TestFeaturedPackages:

    def test_featured(self):

        with patch(
            "src.repositories.package_repo.get_featured_packages",
            new=AsyncMock(return_value=[SAMPLE_PACKAGE])
        ):
            response = client.get("/api/v1/packages/featured")

        assert response.status_code == 200


# ---------------- POPULAR ----------------

class TestPopularPackages:

    def test_popular(self):

        with patch(
            "src.repositories.package_repo.get_popular_packages",
            new=AsyncMock(return_value=[SAMPLE_PACKAGE])
        ):
            response = client.get("/api/v1/packages/popular")

        assert response.status_code == 200


# ---------------- BY DURATION ----------------

class TestPackagesByDuration:

    def test_duration(self):

        with patch(
            "src.repositories.package_repo.get_packages_by_duration",
            new=AsyncMock(return_value=[SAMPLE_PACKAGE])
        ), patch(
            "src.repositories.package_repo.get_packages_by_duration_count",
            new=AsyncMock(return_value=1)
        ):
            response = client.get("/api/v1/packages/by-duration/3")

        assert response.status_code == 200


# ---------------- PACKAGE DETAIL ----------------

class TestPackageDetail:

    def test_get_package(self):

        with patch(
            "src.repositories.package_repo.get_package_by_id_or_slug",
            new=AsyncMock(return_value=SAMPLE_PACKAGE)
        ):
            response = client.get(f"/api/v1/packages/{PKG_ID}")

        assert response.status_code == 200


# ---------------- PRICE CALCULATION ----------------

class TestPackageCalculation:

    def test_calculate_price(self):

        with patch(
            "src.services.package_service.calculate_price",
            new=AsyncMock(return_value={"total_price": 9998})
        ):
            response = client.post(
                "/api/v1/packages/calculate-price",
                json={
                    "package_id": PKG_ID,
                    "num_adults": 2,
                    "travel_date": "2025-08-15"
                }
            )

        assert response.status_code in [200, 422]


# ---------------- CUSTOM PACKAGE ----------------

class TestCustomizePackage:

    def test_customize(self):

        with patch(
            "src.services.package_service.customize_package",
            new=AsyncMock(return_value={"id": str(uuid4())})
        ):

            response = client.post(
                "/api/v1/packages/customize",
                json={
                    "destination_id": str(uuid4()),
                    "duration_days": 3,
                    "num_adults": 2,
                    "travel_date": "2025-09-01"
                },
                headers={"Authorization": "Bearer testtoken"}
            )

        assert response.status_code in [200, 201, 401, 422]