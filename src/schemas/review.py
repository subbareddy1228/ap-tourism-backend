"""
Module 13 — Review APIs
Pydantic schemas: request / response
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.models.review import EntityType, ReportReason, ReviewStatus


# ---------------------------------------------------------------------------
# Nested helpers
# ---------------------------------------------------------------------------

class AuthorOut(BaseModel):
    id: UUID
    name: str
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Review — request
# ---------------------------------------------------------------------------

class ReviewCreateRequest(BaseModel):
    booking_id:  Optional[UUID] = None
    entity_type: EntityType
    entity_id:   UUID
    rating:      int = Field(..., ge=1, le=5)
    title:       Optional[str] = Field(None, max_length=150)
    body:        Optional[str] = None
    photos:      Optional[List[str]] = Field(None, max_length=5)

    @field_validator("photos")
    @classmethod
    def max_five_photos(cls, v):
        if v and len(v) > 5:
            raise ValueError("A maximum of 5 photos are allowed per review")
        return v


class ReviewUpdateRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title:  Optional[str] = Field(None, max_length=150)
    body:   Optional[str] = None
    photos: Optional[List[str]] = Field(None, max_length=5)

    @field_validator("photos")
    @classmethod
    def max_five_photos(cls, v):
        if v and len(v) > 5:
            raise ValueError("A maximum of 5 photos are allowed per review")
        return v


class ReviewReportRequest(BaseModel):
    reason: ReportReason
    note:   Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Review — response
# ---------------------------------------------------------------------------

class ReviewOut(BaseModel):
    id:          UUID
    user:        AuthorOut
    booking_id:  Optional[UUID]
    entity_type: EntityType
    entity_id:   UUID
    rating:      int
    title:       Optional[str]
    body:        Optional[str]
    photos:      List[str]
    helpful_count:    int
    status:           ReviewStatus
    created_at:       datetime
    updated_at:       datetime
    is_helpful_by_me: bool = False

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items:       List[ReviewOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
    average_rating:     Optional[float] = None
    rating_distribution: Optional[Dict[int, int]] = None


# ---------------------------------------------------------------------------
# Pending review (requires booking service)
# ---------------------------------------------------------------------------

class PendingReviewItem(BaseModel):
    booking_id:   UUID
    entity_type:  EntityType
    entity_id:    UUID
    entity_name:  Optional[str] = None
    booking_date: Optional[datetime] = None


class ReviewModerateRequest(BaseModel):
    status: str  # approved | rejected
    reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        if v not in ["approved", "rejected"]:
            raise ValueError("status must be approved or rejected")
        return v