import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from src.api.deps.auth import get_current_user_id, get_optional_user_id
from src.schemas.search import (
    AutocompleteItem,
    EntitySearchResult,
    GlobalSearchResult,
    SuggestionItem,
    DestinationSearchParams,
    HotelSearchParams,
    PackageSearchParams,
    TempleSearchParams,
)
from src.services import search_service

router = APIRouter(prefix="/search", tags=["Search"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=GlobalSearchResult, summary="Global Search")
async def global_search(
    q: Annotated[str, Query(min_length=2, description="Search query (min 2 chars)")],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    user_id: Optional[int] = Depends(get_optional_user_id),
) -> GlobalSearchResult:
    return await search_service.global_search(q=q, limit=limit, user_id=user_id)


@router.get("/suggestions", response_model=list[SuggestionItem], summary="Search Suggestions")
async def get_suggestions(
    q: Annotated[str, Query(min_length=1)],
) -> list[SuggestionItem]:
    return await search_service.get_suggestions(q=q)


@router.get("/autocomplete", response_model=list[AutocompleteItem], summary="Autocomplete")
async def autocomplete(
    q: Annotated[str, Query(min_length=1)],
) -> list[AutocompleteItem]:
    return await search_service.get_autocomplete(q=q)


@router.get("/recent", response_model=list[str], summary="Recent Searches")
async def recent_searches(
    user_id: str = Depends(get_current_user_id),
) -> list[str]:
    return await search_service.get_recent_searches(user_id=user_id)


@router.get("/temples", response_model=EntitySearchResult, summary="Search Temples")
async def search_temples(
    q:            Annotated[Optional[str], Query()] = None,
    name:         Annotated[Optional[str], Query()] = None,
    deity:        Annotated[Optional[str], Query()] = None,
    district:     Annotated[Optional[str], Query()] = None,
    darshan_type: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> EntitySearchResult:
    return await search_service.search_temples(
        TempleSearchParams(q=q, name=name, deity=deity, district=district, darshan_type=darshan_type, page=page, size=size)
    )


@router.get("/hotels", response_model=EntitySearchResult, summary="Search Hotels")
async def search_hotels(
    q:           Annotated[Optional[str],       Query()] = None,
    name:        Annotated[Optional[str],       Query()] = None,
    city:        Annotated[Optional[str],       Query()] = None,
    amenities:   Annotated[Optional[list[str]], Query()] = None,
    min_price:   Annotated[Optional[float],     Query()] = None,
    max_price:   Annotated[Optional[float],     Query()] = None,
    star_rating: Annotated[Optional[int],       Query(ge=1, le=5)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> EntitySearchResult:
    return await search_service.search_hotels(
        HotelSearchParams(q=q, name=name, city=city, amenities=amenities,
                          min_price=min_price, max_price=max_price,
                          star_rating=star_rating, page=page, size=size)
    )


@router.get("/packages", response_model=EntitySearchResult, summary="Search Packages")
async def search_packages(
    q:            Annotated[Optional[str],   Query()] = None,
    name:         Annotated[Optional[str],   Query()] = None,
    destination:  Annotated[Optional[str],   Query()] = None,
    min_duration: Annotated[Optional[int],   Query()] = None,
    max_duration: Annotated[Optional[int],   Query()] = None,
    min_budget:   Annotated[Optional[float], Query()] = None,
    max_budget:   Annotated[Optional[float], Query()] = None,
    package_type: Annotated[Optional[str],   Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> EntitySearchResult:
    return await search_service.search_packages(
        PackageSearchParams(q=q, name=name, destination=destination,
                            min_duration=min_duration, max_duration=max_duration,
                            min_budget=min_budget, max_budget=max_budget,
                            package_type=package_type, page=page, size=size)
    )


@router.get("/destinations", response_model=EntitySearchResult, summary="Search Destinations")
async def search_destinations(
    q:                Annotated[Optional[str], Query()] = None,
    name:             Annotated[Optional[str], Query()] = None,
    destination_type: Annotated[Optional[str], Query()] = None,
    district:         Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> EntitySearchResult:
    return await search_service.search_destinations(
        DestinationSearchParams(q=q, name=name, destination_type=destination_type, district=district, page=page, size=size)
    )
