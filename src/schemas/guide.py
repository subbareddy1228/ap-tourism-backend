"""
schemas/guide.py
Guide module schemas — fixed for Pydantic v2 (LEV146 pattern).
Changes:
  - @validator → @field_validator
  - .from_orm() → model_config
  - Integer IDs → UUID
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

from src.models.guide import GuideStatus, Specialization, LanguageProficiency


# ─── Create / Update ──────────────────────────────────────────

class GuideCreateSchema(BaseModel):
    full_name:          str
    bio:                Optional[str]         = None
    city:               str
    state:              str
    experience_years:   Optional[int]         = 0
    price_per_day:      Optional[float]       = None
    price_per_half_day: Optional[float]       = None
    certifications:     Optional[List[str]]   = []
    destinations:       Optional[List[str]]   = []


class GuideUpdateSchema(BaseModel):
    full_name:          Optional[str]         = None
    bio:                Optional[str]         = None
    city:               Optional[str]         = None
    state:              Optional[str]         = None
    experience_years:   Optional[int]         = None
    price_per_day:      Optional[float]       = None
    price_per_half_day: Optional[float]       = None
    certifications:     Optional[List[str]]   = None
    destinations:       Optional[List[str]]   = None


class GuideStatusUpdateSchema(BaseModel):
    status: GuideStatus


class GuideAvailabilityUpdateSchema(BaseModel):
    unavailable_dates: List[str]   # ["YYYY-MM-DD"]


# ─── Language Schemas ─────────────────────────────────────────

class GuideLanguageCreateSchema(BaseModel):
    language:    str
    proficiency: LanguageProficiency = LanguageProficiency.CONVERSATIONAL

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        allowed = ["Telugu", "Hindi", "English", "Tamil", "Kannada", "Urdu"]
        if v not in allowed:
            raise ValueError(f"Language must be one of {allowed}")
        return v


class GuideLanguageResponseSchema(BaseModel):
    id:          UUID
    language:    str
    proficiency: LanguageProficiency
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─── Specialization Schemas ───────────────────────────────────

class GuideSpecializationCreateSchema(BaseModel):
    specialization: Specialization


class GuideSpecializationResponseSchema(BaseModel):
    id:             UUID
    specialization: Specialization
    created_at:     datetime

    model_config = {"from_attributes": True}


# ─── Document Schemas ─────────────────────────────────────────

class GuideDocumentResponseSchema(BaseModel):
    id:            UUID
    document_type: str
    file_url:      str
    is_verified:   bool
    created_at:    datetime

    model_config = {"from_attributes": True}


# ─── Response Schema ──────────────────────────────────────────

class GuideResponseSchema(BaseModel):
    id:                 UUID
    user_id:            UUID
    full_name:          str
    bio:                Optional[str]
    profile_photo:      Optional[str]
    city:               str
    state:              str
    experience_years:   int
    rating:             float
    total_reviews:      int
    total_trips:        int
    status:             GuideStatus
    is_featured:        bool
    is_verified:        bool
    price_per_day:      Optional[float]
    price_per_half_day: Optional[float]
    certifications:     List[str]
    destinations:       List[str]
    created_at:         datetime

    model_config = {"from_attributes": True}