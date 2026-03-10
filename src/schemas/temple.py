from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


# ─────────────────────────────────────────────
# Base / Shared
# ─────────────────────────────────────────────
class TempleTimings(BaseModel):
    open: str = Field(..., example="06:00")
    close: str = Field(..., example="20:00")


class TempleBase(BaseModel):
    name: str
    description: Optional[str] = None
    deity: str
    district: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dress_code: Optional[str] = None
    timings: Optional[Dict[str, TempleTimings]] = None   # {"monday": {...}, ...}
    images: Optional[List[str]] = []


# ─────────────────────────────────────────────
# Create / Update (Admin)
# ─────────────────────────────────────────────
class TempleCreate(TempleBase):
    pass


class TempleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deity: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_featured: Optional[bool] = None
    dress_code: Optional[str] = None
    timings: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ─────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────
class TempleListItem(BaseModel):
    """Lightweight schema used in list endpoints."""
    id: UUID
    name: str
    deity: str
    district: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_featured: bool
    booking_count: int
    images: Optional[List[str]] = []

    model_config = {"from_attributes": True}


class TempleDetail(TempleBase):
    """Full detail schema for GET /{id}."""
    id: UUID
    is_featured: bool
    booking_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Event Schema
# ─────────────────────────────────────────────
class TempleEventResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    description: Optional[str]
    event_date: str
    start_time: Optional[str]
    end_time: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Review Schemas
# ─────────────────────────────────────────────
class TempleReviewCreate(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0)
    title: Optional[str] = None
    body: Optional[str] = None
    visit_date: Optional[str] = None


class TempleReviewResponse(BaseModel):
    id: UUID
    temple_id: UUID
    user_id: UUID
    rating: float
    title: Optional[str]
    body: Optional[str]
    visit_date: Optional[str]
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Filter / Query params
# ─────────────────────────────────────────────
class TempleFilters(BaseModel):
    deity: Optional[str] = None
    district: Optional[str] = None
    darshan_type: Optional[str] = None
    page: int = 1
    page_size: int = 20