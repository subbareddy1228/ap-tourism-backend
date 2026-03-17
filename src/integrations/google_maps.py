# src/integrations/google_maps.py
"""
Distance calculation using Nominatim (geocoding) + OSRM (routing).
Both are free, open-source, and require NO API key.
Nominatim: https://nominatim.openstreetmap.org
OSRM:      https://router.project-osrm.org
"""
import requests


class GoogleMapsClient:

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
    HEADERS = {"User-Agent": "ap-tourism-backend/1.0"}

    def _geocode(self, address: str) -> tuple:
        """Convert address to (longitude, latitude) using Nominatim."""
        response = requests.get(
            self.NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers=self.HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            raise ValueError(f"Could not geocode address: '{address}'")
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
        return lon, lat  # OSRM expects longitude first

    def get_distance(self, origin: str, destination: str) -> dict:
        """
        Get driving distance and duration between two addresses.
        Returns dict with distance_km and duration_minutes.
        """
        origin_coords = self._geocode(origin)
        destination_coords = self._geocode(destination)

        # OSRM expects: /route/v1/driving/lon1,lat1;lon2,lat2
        coords = f"{origin_coords[0]},{origin_coords[1]};{destination_coords[0]},{destination_coords[1]}"
        url = f"{self.OSRM_URL}/{coords}"

        response = requests.get(
            url,
            params={"overview": "false"},
            headers=self.HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM returned no route: {data.get('code')}")

        route = data["routes"][0]
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60, 1),
        }