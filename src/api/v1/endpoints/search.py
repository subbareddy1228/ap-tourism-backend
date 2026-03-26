from fastapi import APIRouter, Query
from typing import Optional

from src.services.search_service import (
    global_search,
    get_suggestions,
    get_autocomplete
)

# Create FastAPI router
router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


# ---------------- GLOBAL SEARCH ----------------

@router.get("/")
async def search(
    q: str = Query(..., description="Search query"),
    user_id: Optional[str] = None,
):
    return await global_search(q, user_id)


# ---------------- SUGGESTIONS ----------------

@router.get("/suggestions")
async def suggestions(
    q: str = Query(..., description="Suggestion query")
):
    return await get_suggestions(q)


# ---------------- AUTOCOMPLETE ----------------

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., description="Autocomplete query")
):
    return await get_autocomplete(q)


    # -------- TEMPLE SEARCH --------
@router.get("/temples")
async def search_temples(q: str):
    from src.services.search_service import search_temples
    return await search_temples(q)


# -------- HOTEL SEARCH --------
@router.get("/hotels")
async def search_hotels(q: str):
    from src.services.search_service import search_hotels
    return await search_hotels(q)


# -------- PACKAGE SEARCH --------
@router.get("/packages")
async def search_packages(q: str):
    from src.services.search_service import search_packages
    return await search_packages(q)


# -------- DESTINATION SEARCH --------
@router.get("/destinations")
async def search_destinations(q: str):
    from src.services.search_service import search_destinations
    return await search_destinations(q)


# -------- RECENT SEARCH --------
@router.get("/recent")
async def recent_search(user_id: str):
    from src.services.search_service import get_recent_searches
    return await get_recent_searches(user_id)