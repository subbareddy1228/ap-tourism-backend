"""
api/v1/endpoints/destination.py
Destination module — fixed for LEV146 integration.
Changes:
  - get_db from src.core.database
  - uses APIResponse wrapper
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.core.database import get_db
from src.api.deps.auth import get_admin_user
from src.models.user import User
from src.models.destination import DestinationType
from src.schemas.destination import DestinationCreate, DestinationUpdate
from src.common.responses import APIResponse
from src.services.destination_service import (
    get_destinations,
    get_featured_destinations,
    get_popular_destinations,
    get_destination_types,
    get_destination,
    create_destination,
    update_destination,
)

router = APIRouter(prefix="/destinations", tags=["Destinations"])


@router.get("/featured", response_model=APIResponse, summary="Featured destinations")
async def list_featured_destinations(db: AsyncSession = Depends(get_db)):
    result = await get_featured_destinations(db)
    return APIResponse.success(message=result["message"], data=result["data"])


@router.get("/popular", response_model=APIResponse, summary="Popular destinations")
async def list_popular_destinations(db: AsyncSession = Depends(get_db)):
    result = await get_popular_destinations(db)
    return APIResponse.success(message=result["message"], data=result["data"])


@router.get("/types", response_model=APIResponse, summary="Destination types")
async def list_destination_types():
    result = await get_destination_types()
    return APIResponse.success(message=result["message"], data=result["data"])


@router.get("", response_model=APIResponse, summary="List all destinations")
async def list_destinations(
    type:     Optional[DestinationType] = Query(None, description="NATURE | HERITAGE | ADVENTURE | COASTAL | RELIGIOUS"),
    district: Optional[str]             = Query(None, description="Filter by district"),
    page:     int                       = Query(1, ge=1),
    limit:    int                       = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await get_destinations(db, page=page, limit=limit, type=type, district=district)
    return APIResponse.success(message="Destinations fetched", data=result["data"])


@router.get("/{destination_id}", response_model=APIResponse, summary="Get destination by ID or slug")
async def retrieve_destination(
    destination_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await get_destination(db, destination_id)
    return APIResponse.success(message=result["message"], data=result["data"])


@router.post("", response_model=APIResponse, status_code=201, summary="[Admin] Create destination")
async def create_new_destination(
    data: DestinationCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await create_destination(db, data)
    return APIResponse.success(message=result["message"], data=result["data"])


@router.put("/{destination_id}", response_model=APIResponse, summary="[Admin] Update destination")
async def update_existing_destination(
    destination_id: str,
    data: DestinationUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await update_destination(db, destination_id, data)
    return APIResponse.success(message=result["message"], data=result["data"])