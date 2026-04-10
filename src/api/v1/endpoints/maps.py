"""
src/api/v1/endpoints/maps.py

Maps API endpoints — thin proxy over MapsClient (Ola Maps).
prefix: /api/v1/maps

Endpoints:
    GET  /maps/autocomplete        — address typeahead for search bar
    GET  /maps/reverse-geocode     — lat/lng → readable address
    GET  /maps/navigate            — Google Maps deep-link (no API cost)

Auth: all endpoints require a logged-in user.
      Autocomplete is called from booking/search UI so it needs basic auth
      to prevent abuse (open endpoint = free geocoding for bots).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from src.api.deps.auth import get_current_user
from src.models.user import User
from src.common.responses import APIResponse
from src.integrations import maps_client

router = APIRouter(prefix="/maps", tags=["Maps"])


# ══════════════════════════════════════════════════════════════════════════════
# 1.  ADDRESS AUTOCOMPLETE
# GET /api/v1/maps/autocomplete?q=Tirupati&limit=5
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/autocomplete",
    response_model=APIResponse,
    summary="Address autocomplete suggestions",
)
async def address_autocomplete(
    q    : str            = Query(..., min_length=2, description="Partial address text"),
    limit: int            = Query(5, ge=1, le=10),
    lat  : Optional[float] = Query(None, description="Bias results near this latitude"),
    lng  : Optional[float] = Query(None, description="Bias results near this longitude"),
    current_user: User = Depends(get_current_user),
):
    """
    Returns up to `limit` address suggestions for the given partial query.
    Pass `lat`/`lng` to bias results toward the user's current location.

    Frontend usage:
        GET /api/v1/maps/autocomplete?q=Tiru&lat=13.63&lng=79.41
    """
    try:
        results = await maps_client.autocomplete(
            query             = q,
            limit             = limit,
            location_bias_lat = lat,
            location_bias_lng = lng,
        )
        return APIResponse.success(
            message=f"{len(results)} suggestions found",
            data=results,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Maps service unavailable: {str(e)}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2.  REVERSE GEOCODE
# GET /api/v1/maps/reverse-geocode?lat=13.63&lng=79.41
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/reverse-geocode",
    response_model=APIResponse,
    summary="Convert lat/lng to a readable address",
)
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a human-readable address string for the given coordinates.

    Frontend usage (e.g., show driver's current address in tracking UI):
        GET /api/v1/maps/reverse-geocode?lat=13.6288&lng=79.4192
    """
    try:
        address = await maps_client.reverse_geocode(lat=lat, lng=lng)
        return APIResponse.success(
            message="Address resolved",
            data={"address": address, "latitude": lat, "longitude": lng},
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Maps service unavailable: {str(e)}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3.  GOOGLE MAPS NAVIGATION DEEP LINK  (zero API cost)
# GET /api/v1/maps/navigate?pickup_lat=...&pickup_lng=...&drop_lat=...&drop_lng=...
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/navigate",
    response_model=APIResponse,
    summary="Get Google Maps deep-link for in-app navigation",
)
async def get_navigation_link(
    pickup_lat: float = Query(..., description="Pickup latitude"),
    pickup_lng: float = Query(..., description="Pickup longitude"),
    drop_lat  : float = Query(..., description="Drop latitude"),
    drop_lng  : float = Query(..., description="Drop longitude"),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a Google Maps URL that opens the native Maps app on mobile.
    No API key needed — this is a pure deep-link, zero cost.

    Frontend usage:
        GET /api/v1/maps/navigate?pickup_lat=13.63&pickup_lng=79.41&drop_lat=13.68&drop_lng=79.42
        → open response.data.url in a WebView / browser tab
    """
    url = maps_client.build_navigation_link(
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        drop_lat=drop_lat,
        drop_lng=drop_lng,
    )
    return APIResponse.success(
        message="Navigation link generated",
        data={"url": url},
    )
