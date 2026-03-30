import httpx

class GoogleMapsClient:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
    HEADERS = {"User-Agent": "ap-tourism-backend/1.0"}

    async def _geocode(self, address: str) -> tuple:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
        results = response.json()
        if not results:
            raise ValueError(f"Could not geocode address: '{address}'")
        return float(results[0]["lon"]), float(results[0]["lat"])

    async def get_distance(self, origin: str, destination: str) -> dict:
        origin_coords = await self._geocode(origin)
        destination_coords = await self._geocode(destination)
        coords = f"{origin_coords[0]},{origin_coords[1]};{destination_coords[0]},{destination_coords[1]}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.OSRM_URL}/{coords}",
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