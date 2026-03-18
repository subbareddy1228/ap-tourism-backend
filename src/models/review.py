"""
Module 13 — Review APIs
Models: Review, ReviewHelpful, ReviewReport
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntityType(str, enum.Enum):
    HOTEL = "HOTEL"
    TEMPLE = "TEMPLE"
    GUIDE = "GUIDE"
    PACKAGE = "PACKAGE"
    VEHICLE = "VEHICLE"


class ReviewStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FLAGGED = "FLAGGED"
    REMOVED = "REMOVED"


class ReportReason(str, enum.Enum):
    SPAM = "SPAM"
    OFFENSIVE = "OFFENSIVE"
    FAKE = "FAKE"
    IRRELEVANT = "IRRELEVANT"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Review(Base):
    """
    Core review entity.
    One review per (user_id, booking_id, entity_type, entity_id).
    Only allowed after booking status = COMPLETED.
    Editable within 24 hours of submission.
    """
    __tablename__ = "reviews"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), nullable=False)
    booking_id  = Column(UUID(as_uuid=True), nullable=True)

    entity_type = Column(SAEnum(EntityType, name="entitytype"), nullable=False)
    entity_id   = Column(UUID(as_uuid=True), nullable=False)

    rating = Column(Integer, nullable=False)
    title  = Column(String(150), nullable=True)
    body   = Column(Text, nullable=True)
    photos = Column(Text, nullable=True)            # JSON array string, max 5 URLs

    helpful_count = Column(Integer, default=0, nullable=False)
    status        = Column(
        SAEnum(ReviewStatus, name="reviewstatus"),
        default=ReviewStatus.ACTIVE, nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "booking_id", "entity_type", "entity_id",
            name="uq_review_user_booking_entity",
        ),
        Index("ix_reviews_entity",  "entity_type", "entity_id"),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_status",  "status"),
    )

    helpful_marks = relationship(
        "ReviewHelpful", back_populates="review", cascade="all, delete-orphan"
    )
    reports = relationship(
        "ReviewReport", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewHelpful(Base):
    """One helpful mark per user per review."""
    __tablename__ = "review_helpfuls"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id    = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("review_id", "user_id", name="uq_review_helpful_user"),
    )

    review = relationship("Review", back_populates="helpful_marks")


class ReviewReport(Base):
    """Reports submitted against inappropriate reviews."""
    __tablename__ = "review_reports"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    reported_by = Column(UUID(as_uuid=True), nullable=False)
    reason      = Column(SAEnum(ReportReason, name="reportreason"), nullable=False)
    note        = Column(Text, nullable=True)
    resolved    = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("review_id", "reported_by", name="uq_report_user_review"),
    )

    review = relationship("Review", back_populates="reports")
