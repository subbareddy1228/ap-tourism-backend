"""
API v1 — central router that includes all endpoint modules.
"""

from fastapi import APIRouter

from src.api.v1.endpoints import reviews

api_router = APIRouter()

# Module 13 — Reviews
api_router.include_router(reviews.router)

