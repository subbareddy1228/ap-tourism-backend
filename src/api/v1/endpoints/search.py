from fastapi import APIRouter, Query
from typing import Optional

from src.services.search_service import (
    global_search,
    get_suggestions,
    get_autocomplete,
)

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
async def search(q: str = Query(...), user_id: Optional[str] = None):
    return await global_search(q, user_id)

@router.get("/suggestions")
async def suggestions(q: str = Query(...)):
    return await get_suggestions(q)

@router.get("/autocomplete")
async def autocomplete(q: str = Query(...)):
    return await get_autocomplete(q)

@router.get("/temples")
async def search_temples_route(q: str):
    from src.services.search_service import search_temples
    return await search_temples(q)

@router.get("/hotels")
async def search_hotels_route(q: str):
    from src.services.search_service import search_hotels
    return await search_hotels(q)

@router.get("/packages")
async def search_packages_route(q: str):
    from src.services.search_service import search_packages
    return await search_packages(q)

@router.get("/destinations")
async def search_destinations_route(q: str):
    from src.services.search_service import search_destinations
    return await search_destinations(q)

@router.get("/recent")
async def recent_search(user_id: str):
    from src.services.search_service import get_recent_searches
    return await get_recent_searches(user_id)