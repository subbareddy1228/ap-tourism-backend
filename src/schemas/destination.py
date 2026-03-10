from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.destination import DestinationType


# ---------- Nested Schemas ----------

class HowToReach(BaseModel):
    by_road: Optional[str] = None
    by_train: Optional[str] = None
    by_air: Optional[str] = None


class Attraction(BaseModel):
    name: str
    type: str
    distance_km: float


class NearbyTemple(BaseModel):
    id: str
    name: str
    distance_km: float


class Image(BaseModel):
    url: str
    caption: Optional[str] = None
    is_hero: bool = False


# ---------- Base Schema ----------

class DestinationBase(BaseModel):
    name: str = Field(..., example="Araku Valley")
    slug: str = Field(..., example="araku-valley")
    district: str = Field(..., example="Visakhapatnam")
    type: DestinationType

    tagline: str
    description: str

    best_season: Optional[str] = None
    temperature_range: Optional[str] = None

    how_to_reach: Optional[HowToReach] = None
    attractions: List[Attraction] = []
    nearby_temples: List[NearbyTemple] = []
    images: List[Image] = []


# ---------- Create Schema ----------

class DestinationCreate(DestinationBase):
    is_featured: Optional[bool] = False
    is_active: Optional[bool] = True


# ---------- Update Schema ----------

class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    district: Optional[str] = None
    type: Optional[DestinationType] = None

    tagline: Optional[str] = None
    description: Optional[str] = None

    best_season: Optional[str] = None
    temperature_range: Optional[str] = None

    how_to_reach: Optional[HowToReach] = None
    attractions: Optional[List[Attraction]] = None
    nearby_temples: Optional[List[NearbyTemple]] = None
    images: Optional[List[Image]] = None

    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


# ---------- Response Schema ----------

class DestinationResponse(DestinationBase):
    id: str
    rating: float
    reviews_count: int
    is_featured: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True