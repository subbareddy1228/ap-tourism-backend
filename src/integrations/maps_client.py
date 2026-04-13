"""
src/integrations/maps_client.py

Vendor-agnostic map client backed by Ola Maps API.
Replaces: src/integrations/google_maps.py

Covers:
  1. reverse_geocode   — lat/lng  → readable address        (tracking pings)
  2. geocode           — address  → lat/lng                  (fare calculation)
  3. directions        — pickup → drop, distance/duration/polyline
  4. distance_matrix   — quick distance between two addresses
  5. snap_to_roads     — clean GPS breadcrumb trail
  6. autocomplete      — address typeahead search

  + build_navigation_link — Google Maps deep-link (zero API cost)

Ola Maps API docs: https://maps.olakrutrim.com/docs
"""

import httpx
from typing import Optional
from src.core.config import settings


# ── Base URL ──────────────────────────────────────────────────────────────────
_BASE = "https://api.olamaps.io"


# ── Thin HTTP helper ──────────────────────────────────────────────────────────

def _auth_params() -> dict:
    """Ola Maps uses api_key as a query param on every request."""
    return {"api_key": settings.OLA_MAPS_API_KEY}


async def _get(path: str, params: dict) -> dict:
    """
    Single shared GET helper.
    Raises RuntimeError on HTTP error so callers get a clean 503.
    """
    params.update(_auth_params())
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{_BASE}{path}", params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"Ola Maps error {response.status_code} on {path}: {response.text[:200]}"
        )
    return response.json()


# ══════════════════════════════════════════════════════════════════════════════
# 1. REVERSE GEOCODE  —  lat/lng → address string
# ══════════════════════════════════════════════════════════════════════════════

async def reverse_geocode(lat: float, lng: float) -> str:
    """
    Convert a GPS coordinate into a human-readable address.
    Used in tracking_service.process_ping() to label the driver's location.

    Returns: address string, e.g. "Tirumala, Tirupati, Andhra Pradesh 517504"
    """
    data = await _get(
        "/places/v1/reverse-geocode",
        {"latlng": f"{lat},{lng}"},
    )
    results = data.get("results") or data.get("result") or []
    if not results:
        return f"{lat:.6f},{lng:.6f}"          # graceful fallback — never crash
    return results[0].get("formatted_address", f"{lat:.6f},{lng:.6f}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. GEOCODE  —  address string → (lat, lng)
# ══════════════════════════════════════════════════════════════════════════════

async def geocode(address: str) -> tuple[float, float]:
    """
    Convert a text address into GPS coordinates.
    Used in vehicle_service.calculate_fare() before calling distance_matrix().

    Returns: (latitude, longitude)
    Raises: ValueError if address cannot be resolved.
    """
    data = await _get(
        "/places/v1/geocode",
        {"address": address},
    )
    results = data.get("geocodingResults") or data.get("results") or []
    if not results:
        raise ValueError(f"Could not geocode address: '{address}'")
    loc = results[0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


# ══════════════════════════════════════════════════════════════════════════════
# 3. DIRECTIONS  —  pickup → drop: distance, duration, polyline
# ══════════════════════════════════════════════════════════════════════════════

async def directions(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Get a full route from one coordinate to another.
    Used in tracking_service.start_session() to pre-compute the trip route.

    Returns:
        {
            "distance_km"     : 12.3,
            "duration_minutes": 24.5,
            "polyline"        : "encoded_polyline_string",
            "steps"           : [ ... ]    # optional turn-by-turn
        }
    """
    data = await _get(
        "/routing/v1/directions",
        {
            "origin"     : f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
        },
    )
    routes = data.get("routes") or []
    if not routes:
        raise ValueError("Ola Maps returned no route for given coordinates")

    route = routes[0]
    leg   = route.get("legs", [{}])[0]

    return {
        "distance_km"     : round(leg.get("distance", {}).get("value", 0) / 1000, 2),
        "duration_minutes": round(leg.get("duration", {}).get("value", 0) / 60, 1),
        "polyline"        : route.get("overview_polyline", {}).get("points", ""),
        "steps"           : leg.get("steps", []),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. DISTANCE MATRIX  —  two addresses → distance + duration
# ══════════════════════════════════════════════════════════════════════════════

async def distance_matrix(origin: str, destination: str) -> dict:
    """
    Quick distance + duration between two text addresses.
    Used in vehicle_service.calculate_fare().

    Returns:
        {
            "distance_km"     : 18.4,
            "duration_minutes": 31.0
        }
    Raises: ValueError if either address cannot be resolved or no route found.
    """
    # Geocode both addresses in parallel
    import asyncio
    origin_coords, dest_coords = await asyncio.gather(
        geocode(origin),
        geocode(destination),
    )

    data = await _get(
        "/routing/v1/distanceMatrix",
        {
            "origins"     : f"{origin_coords[0]},{origin_coords[1]}",
            "destinations": f"{dest_coords[0]},{dest_coords[1]}",
        },
    )

    rows = data.get("rows") or []
    if not rows or not rows[0].get("elements"):
        raise ValueError(f"No route found between '{origin}' and '{destination}'")

    element = rows[0]["elements"][0]
    if element.get("status") != "OK":
        raise ValueError(
            f"Distance matrix failed: {element.get('status')} "
            f"for '{origin}' → '{destination}'"
        )

    # Ola Maps returns distance/duration as plain int (metres/seconds)
    # not as {"value": ...} dict like Google Maps
    distance = element.get("distance") or element.get("distanceMeters", 0)
    duration = element.get("duration") or element.get("durationSeconds", 0)

    if isinstance(distance, dict):
        distance = distance.get("value", 0)
    if isinstance(duration, dict):
        duration = duration.get("value", 0)
    
    return {
        "distance_km"     : round(distance / 1000, 2),
        "duration_minutes": round(duration / 60, 1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. SNAP TO ROADS  —  clean GPS breadcrumb trail
# ══════════════════════════════════════════════════════════════════════════════

async def snap_to_roads(points: list[dict]) -> list[dict]:
    """
    Snap raw GPS breadcrumb points onto actual road geometry.
    Used in tracking_service.get_history() — called once on history fetch,
    NOT on every ping (avoids per-ping API cost).

    Args:
        points: list of {"latitude": float, "longitude": float}
                (up to 100 points per call — Ola Maps limit)

    Returns:
        list of {"latitude": float, "longitude": float} — snapped to road.
        Falls back to original points if API fails (never crash history fetch).
    """
    if not points:
        return points

    # Ola Maps snap_to_roads accepts "path" as "lat,lng|lat,lng|..."
    path = "|".join(f"{p['latitude']},{p['longitude']}" for p in points)

    try:
        data = await _get("/routing/v1/snapToRoad", {"path": path})
        snapped = data.get("snappedPoints") or []
        if not snapped:
            return points   # graceful fallback

        return [
            {
                "latitude" : sp["location"]["latitude"],
                "longitude": sp["location"]["longitude"],
            }
            for sp in snapped
        ]
    except Exception:
        # History fetch must NEVER fail just because snap API is down
        return points


# ══════════════════════════════════════════════════════════════════════════════
# 6. AUTOCOMPLETE  —  address typeahead
# ══════════════════════════════════════════════════════════════════════════════

async def autocomplete(
    query: str,
    limit: int = 5,
    location_bias_lat: Optional[float] = None,
    location_bias_lng: Optional[float] = None,
) -> list[dict]:
    """
    Address autocomplete suggestions for the search bar.
    Used in GET /api/v1/maps/autocomplete?q=...

    Args:
        query            : partial text the user has typed
        limit            : max suggestions to return (default 5)
        location_bias_lat: bias results toward this area (optional)
        location_bias_lng: bias results toward this area (optional)

    Returns:
        [
            {
                "description": "Tirumala, Tirupati, Andhra Pradesh",
                "place_id"   : "ChIJ...",
                "types"      : ["locality", ...]
            },
            ...
        ]
    """
    params: dict = {"input": query}
    if location_bias_lat and location_bias_lng:
        params["location"] = f"{location_bias_lat},{location_bias_lng}"

    data = await _get("/places/v1/autocomplete", params)

    predictions = data.get("predictions") or []
    results = [
        {
            "description": p.get("description", ""),
            "place_id"   : p.get("place_id", ""),
            "types"      : p.get("types", []),
        }
        for p in predictions[:limit]
    ]
    return results


# ══════════════════════════════════════════════════════════════════════════════
# 7. GOOGLE MAPS NAVIGATION DEEP LINK  (zero API cost)
# ══════════════════════════════════════════════════════════════════════════════

def build_navigation_link(
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
) -> str:
    """
    Build a Google Maps deep-link for in-app navigation.
    No API key. Opens Google Maps app on mobile if installed,
    falls back to maps.google.com in browser.

    Used in GET /api/v1/maps/navigate
    """
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={pickup_lat},{pickup_lng}"
        f"&destination={drop_lat},{drop_lng}"
        f"&travelmode=driving"
    )
