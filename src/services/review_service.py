"""
Module 13 — Review APIs
Service: business rules, orchestration
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.review import EntityType, Review, ReviewReport, ReviewStatus
from src.repositories.review_repo import ReviewRepository

from src.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from src.schemas.review import (
    PendingReviewItem,
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewOut,
    ReviewReportRequest,
    ReviewUpdateRequest,
)

EDIT_WINDOW_HOURS = 24

class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReviewRepository(db)

    # ------------------------------------------------------------------
    # Public — read
    # ------------------------------------------------------------------

    async def list_reviews(
        self,
        entity_type: Optional[EntityType],
        entity_id: Optional[UUID],
        rating: Optional[int],
        sort: str,
        page: int,
        page_size: int,
        current_user_id: Optional[UUID] = None,
    ) -> ReviewListResponse:
        reviews, total = await self.repo.list_reviews(
            entity_type=entity_type,
            entity_id=entity_id,
            rating=rating,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        helpful_ids: List[UUID] = []
        if current_user_id and reviews:
            helpful_ids = await self.repo.get_user_helpful_ids(
                current_user_id, [r.id for r in reviews]
            )

        items = [self._map_review(r, helpful_ids) for r in reviews]

        avg_rating = None
        rating_dist = None
        if entity_type and entity_id:
            avg_rating, rating_dist = await self.repo.get_rating_stats(
                entity_type, entity_id
            )

        return ReviewListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size else 1,
            average_rating=avg_rating,
            rating_distribution=rating_dist,
        )

    async def get_review(
        self, review_id: UUID, current_user_id: Optional[UUID] = None
    ) -> ReviewOut:
        review = await self.repo.get_by_id(review_id)
        if not review or review.status == ReviewStatus.REMOVED:
            raise NotFoundException("Review not found")
        helpful_ids = []
        if current_user_id:
            helpful_ids = await self.repo.get_user_helpful_ids(
                current_user_id, [review.id]
            )
        return self._map_review(review, helpful_ids)

    # ------------------------------------------------------------------
    # Authenticated — CRUD
    # ------------------------------------------------------------------

    async def create_review(
        self,
        payload: ReviewCreateRequest,
        user_id: UUID,
        booking_service=None,
    ) -> ReviewOut:
        # 1. Verify booking belongs to user and is COMPLETED (if service available)
        if booking_service and payload.booking_id:
            booking = await booking_service.get_booking(payload.booking_id)
            if not booking or str(booking.user_id) != str(user_id):
                raise NotFoundException("Booking not found",)
            if str(getattr(booking, "status", "")).upper() != "COMPLETED":
                raise BadRequestException("Reviews can only be submitted for completed bookings",)

        # 2. Duplicate check
        existing = await self.repo.find_existing_review(
            user_id=user_id,
            booking_id=payload.booking_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
        )
        if existing:
            raise ConflictException("You have already reviewed this entity for this booking",)

        # 3. Persist
        review = Review(
            user_id=user_id,
            booking_id=payload.booking_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
            photos=json.dumps(payload.photos or []),
        )
        review = await self.repo.create(review)
        await self.db.commit()
        await self.db.refresh(review)
        return self._map_review(review, [])

    async def update_review(
        self, review_id: UUID, payload: ReviewUpdateRequest, user_id: UUID
    ) -> ReviewOut:
        review = await self._get_owned_review(review_id, user_id)

        if datetime.utcnow() - review.created_at > timedelta(hours=EDIT_WINDOW_HOURS):
            raise ForbiddenException("Review can only be edited within 24 hours of submission",)

        data: dict = {}
        if payload.rating is not None:
            data["rating"] = payload.rating
        if payload.title is not None:
            data["title"] = payload.title
        if payload.body is not None:
            data["body"] = payload.body
        if payload.photos is not None:
            data["photos"] = json.dumps(payload.photos)

        review = await self.repo.update(review, data)
        await self.db.commit()
        return self._map_review(review, [])

    async def delete_review(self, review_id: UUID, user_id: UUID) -> None:
        review = await self._get_owned_review(review_id, user_id)
        await self.repo.soft_delete(review)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Helpful
    # ------------------------------------------------------------------

    async def mark_helpful(self, review_id: UUID, user_id: UUID) -> ReviewOut:
        review = await self._get_active_review(review_id)

        if str(review.user_id) == str(user_id):
            raise BadRequestException("You cannot mark your own review as helpful",)

        existing = await self.repo.get_helpful_mark(review_id, user_id)
        if existing:
            raise ConflictException("You have already marked this review as helpful",)

        await self.repo.add_helpful_mark(review_id, user_id)
        await self.db.commit()
        await self.db.refresh(review)
        helpful_ids = await self.repo.get_user_helpful_ids(user_id, [review.id])
        return self._map_review(review, helpful_ids)

    async def unmark_helpful(self, review_id: UUID, user_id: UUID) -> ReviewOut:
        review = await self._get_active_review(review_id)
        existing = await self.repo.get_helpful_mark(review_id, user_id)
        if not existing:
            raise NotFoundException("You have not marked this review as helpful",)
        await self.repo.remove_helpful_mark(review_id, user_id)
        await self.db.commit()
        await self.db.refresh(review)
        return self._map_review(review, [])

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    async def report_review(
        self, review_id: UUID, payload: ReviewReportRequest, user_id: UUID
    ) -> dict:
        review = await self._get_active_review(review_id)

        if str(review.user_id) == str(user_id):
            raise BadRequestException("You cannot report your own review",)

        existing = await self.repo.find_report(review_id, user_id)
        if existing:
            raise ConflictException("You have already reported this review",)

        report = ReviewReport(
            review_id=review_id,
            reported_by=user_id,
            reason=payload.reason,
            note=payload.note,
        )
        await self.repo.create_report(report)
        await self.db.commit()
        return {"message": "Report submitted. Our team will review it shortly."}

    # ------------------------------------------------------------------
    # My reviews
    # ------------------------------------------------------------------

    async def get_my_reviews(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> ReviewListResponse:
        reviews, total = await self.repo.get_user_reviews(user_id, page, page_size)
        helpful_ids = await self.repo.get_user_helpful_ids(
            user_id, [r.id for r in reviews]
        )
        items = [self._map_review(r, helpful_ids) for r in reviews]
        return ReviewListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size else 1,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_active_review(self, review_id: UUID) -> Review:
        review = await self.repo.get_by_id(review_id)
        if not review or review.status == ReviewStatus.REMOVED:
            raise NotFoundException("Review not found")
        return review

    async def _get_owned_review(self, review_id: UUID, user_id: UUID) -> Review:
        review = await self._get_active_review(review_id)
        if str(review.user_id) != str(user_id):
            raise ForbiddenException("Permission denied")
        return review

    @staticmethod
    def _map_review(review: Review, helpful_ids: List[UUID]) -> ReviewOut:
        user_obj = getattr(review, "user", None)
        author = {
            "id": review.user_id,
            "name": getattr(user_obj, "name", "Unknown") if user_obj else "Unknown",
            "avatar_url": getattr(user_obj, "avatar_url", None) if user_obj else None,
        }
        return ReviewOut(
            id=review.id,
            user=author,
            booking_id=review.booking_id,
            entity_type=review.entity_type,
            entity_id=review.entity_id,
            rating=review.rating,
            title=review.title,
            body=review.body,
            photos=json.loads(review.photos) if review.photos else [],
            helpful_count=review.helpful_count,
            status=review.status,
            created_at=review.created_at,
            updated_at=review.updated_at,
            is_helpful_by_me=review.id in helpful_ids,
        )
