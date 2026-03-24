"""
Module 13 — Review APIs
Repository: all DB queries for reviews
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.review import (
    EntityType, Review, ReviewHelpful, ReviewReport, ReviewStatus,
)


class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def get_by_id(self, review_id: UUID) -> Optional[Review]:
        result = await self.db.execute(
            select(Review).where(Review.id == review_id)
        )
        return result.scalars().first()

    async def create(self, review: Review) -> Review:
        self.db.add(review)
        await self.db.flush()
        return review

    async def update(self, review: Review, data: dict) -> Review:
        for key, value in data.items():
            setattr(review, key, value)
        self.db.add(review)
        await self.db.flush()
        return review

    async def soft_delete(self, review: Review) -> None:
        review.status = ReviewStatus.REMOVED
        self.db.add(review)
        await self.db.flush()

    # ------------------------------------------------------------------
    # Listing & filtering
    # ------------------------------------------------------------------

    async def list_reviews(
        self,
        entity_type: Optional[EntityType],
        entity_id: Optional[UUID],
        rating: Optional[int],
        sort: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[Review], int]:
        q = select(Review).where(Review.status == ReviewStatus.ACTIVE)

        if entity_type:
            q = q.where(Review.entity_type == entity_type)
        if entity_id:
            q = q.where(Review.entity_id == entity_id)
        if rating:
            q = q.where(Review.rating == rating)

        # Sorting
        if sort == "rating_desc":
            q = q.order_by(Review.rating.desc())
        elif sort == "rating_asc":
            q = q.order_by(Review.rating.asc())
        elif sort == "helpful":
            q = q.order_by(Review.helpful_count.desc())
        else:  # newest (default)
            q = q.order_by(Review.created_at.desc())

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        q = q.offset((page - 1) * page_size).limit(page_size)
        reviews = (await self.db.execute(q)).scalars().all()
        return list(reviews), total

    async def get_user_reviews(
        self, user_id: UUID, page: int, page_size: int
    ) -> Tuple[List[Review], int]:
        q = select(Review).where(
            Review.user_id == user_id,
            Review.status != ReviewStatus.REMOVED,
        ).order_by(Review.created_at.desc())

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        q = q.offset((page - 1) * page_size).limit(page_size)
        reviews = (await self.db.execute(q)).scalars().all()
        return list(reviews), total

    async def find_existing_review(
        self,
        user_id: UUID,
        booking_id: Optional[UUID],
        entity_type: EntityType,
        entity_id: UUID,
    ) -> Optional[Review]:
        q = select(Review).where(
            Review.user_id == user_id,
            Review.entity_type == entity_type,
            Review.entity_id == entity_id,
            Review.status != ReviewStatus.REMOVED,
        )
        if booking_id:
            q = q.where(Review.booking_id == booking_id)
        return (await self.db.execute(q)).scalars().first()

    # ------------------------------------------------------------------
    # Aggregate stats
    # ------------------------------------------------------------------

    async def get_rating_stats(
        self, entity_type: EntityType, entity_id: UUID
    ) -> Tuple[Optional[float], Optional[dict]]:
        q = select(Review.rating).where(
            Review.entity_type == entity_type,
            Review.entity_id == entity_id,
            Review.status == ReviewStatus.ACTIVE,
        )
        ratings = (await self.db.execute(q)).scalars().all()
        if not ratings:
            return None, None

        avg = round(sum(ratings) / len(ratings), 2)
        dist = {i: 0 for i in range(1, 6)}
        for r in ratings:
            dist[r] = dist.get(r, 0) + 1
        return avg, dist

    # ------------------------------------------------------------------
    # Helpful marks
    # ------------------------------------------------------------------

    async def get_helpful_mark(
        self, review_id: UUID, user_id: UUID
    ) -> Optional[ReviewHelpful]:
        result = await self.db.execute(
            select(ReviewHelpful).where(
                ReviewHelpful.review_id == review_id,
                ReviewHelpful.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def get_user_helpful_ids(
        self, user_id: UUID, review_ids: List[UUID]
    ) -> List[UUID]:
        if not review_ids:
            return []
        result = await self.db.execute(
            select(ReviewHelpful.review_id).where(
                ReviewHelpful.user_id == user_id,
                ReviewHelpful.review_id.in_(review_ids),
            )
        )
        return list(result.scalars().all())

    async def add_helpful_mark(self, review_id: UUID, user_id: UUID) -> None:
        mark = ReviewHelpful(review_id=review_id, user_id=user_id)
        self.db.add(mark)
        await self.db.flush()
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(helpful_count=Review.helpful_count + 1)
        )

    async def remove_helpful_mark(self, review_id: UUID, user_id: UUID) -> None:
        mark = await self.get_helpful_mark(review_id, user_id)
        if mark:
            await self.db.delete(mark)
            await self.db.flush()
            await self.db.execute(
                update(Review)
                .where(Review.id == review_id)
                .values(helpful_count=Review.helpful_count - 1)
            )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    async def find_report(
        self, review_id: UUID, user_id: UUID
    ) -> Optional[ReviewReport]:
        result = await self.db.execute(
            select(ReviewReport).where(
                ReviewReport.review_id == review_id,
                ReviewReport.reported_by == user_id,
            )
        )
        return result.scalars().first()

    async def create_report(self, report: ReviewReport) -> ReviewReport:
        self.db.add(report)
        await self.db.flush()
        return report
