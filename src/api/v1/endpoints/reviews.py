"""
Module 13 — Review APIs
Router: all review endpoints
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps.auth import get_admin_user, get_current_user
from src.common.responses import APIResponse
from src.models.user import User
from src.core.database import get_db
from src.models.review import EntityType
from src.schemas.review import (
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewModerateRequest,
    ReviewOut,
    ReviewReportRequest,
    ReviewUpdateRequest,
)
from src.services import review_service
from src.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    return ReviewService(db)




# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=ReviewListResponse,
    summary="List reviews",
    description=(
        "Paginated list of active reviews. "
        "Filter by entity_type + entity_id to get stats (avg rating, distribution)."
    ),
)
async def list_reviews(
    entity_type: Optional[EntityType] = Query(None),
    entity_id:   Optional[UUID]       = Query(None),
    rating:      Optional[int]         = Query(None, ge=1, le=5),
    sort:        str                   = Query("newest", enum=["newest", "rating_desc", "rating_asc", "helpful"]),
    page:        int                   = Query(1, ge=1),
    page_size:   int                   = Query(20, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
):
    return await service.list_reviews(
        entity_type=entity_type,
        entity_id=entity_id,
        rating=rating,
        sort=sort,
        page=page,
        page_size=page_size,
        current_user_id=None,        # swap with current_user.id after auth
    )


@router.get(
    "/{review_id}",
    response_model=ReviewOut,
    summary="Get a single review",
)
async def get_review(
    review_id: UUID,
    service: ReviewService = Depends(get_review_service),
):
    return await service.get_review(review_id, current_user_id=None)


# ---------------------------------------------------------------------------
# Authenticated — CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review",
    description=(
        "Submit a review for a completed booking. "
        "Rules: one review per (user, booking, entity_type, entity_id). "
        "Optionally include up to 5 photo URLs."
    ),
)
async def create_review(
    payload: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.create_review(
        payload=payload,
        user_id=current_user.id ,       
        booking_service=None,       
    )


@router.patch(
    "/{review_id}",
    response_model=ReviewOut,
    summary="Edit a review",
    description="Update rating / title / body / photos within 24 hours of submission.",
)
async def update_review(
    review_id: UUID,
    payload:   ReviewUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.update_review(
        review_id=review_id,
        payload=payload,
        user_id=current_user.id,
    )


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review",
    description="Soft-deletes the review (sets status=REMOVED). Only the author can delete.",
)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    await service.delete_review(review_id=review_id, user_id=current_user.id)


# ---------------------------------------------------------------------------
# Helpful marks
# ---------------------------------------------------------------------------

@router.post(
    "/{review_id}/helpful",
    response_model=ReviewOut,
    summary="Mark review as helpful",
)
async def mark_helpful(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.mark_helpful(review_id=review_id, user_id=current_user.id)


@router.delete(
    "/{review_id}/helpful",
    response_model=ReviewOut,
    summary="Unmark review as helpful",
)
async def unmark_helpful(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.unmark_helpful(review_id=review_id, user_id=current_user.id)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@router.post(
    "/{review_id}/report",
    status_code=status.HTTP_201_CREATED,
    summary="Report a review",
    description="Flag a review as spam, offensive, fake, etc. One report per user per review.",
)
async def report_review(
    review_id: UUID,
    payload:   ReviewReportRequest,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.report_review(
        review_id=review_id,
        payload=payload,
        user_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# My reviews
# ---------------------------------------------------------------------------

@router.get(
    "/me/reviews",
    response_model=ReviewListResponse,
    summary="Get my reviews",
)
async def get_my_reviews(
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.get_my_reviews(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.put(
    "/{review_id}/moderate",
    response_model= APIResponse,
    summary="[Admin] Approve or reject a review"
)
async def moderate_review(
    review_id: str,
    data:ReviewModerateRequest,
    current_user: User = Depends( get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin action to approve or reject a flagged/reported review.
    status: 'approved' | 'rejected'
    """
    result = await  review_service.moderate_review(review_id, data, db)
    return APIResponse.success(message="Review moderated", data=result)