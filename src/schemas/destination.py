from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field, ConfigDict
from src.models.destination import DestinationType
from datetime import date, time
from uuid import UUID


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

class DestinationListResponse(BaseModel):
    id: str
    name: str
    slug: str
    district: str
    type: DestinationType
    tagline: str
    rating: float          # ← show star rating on card
    is_featured: bool      # ← show featured badge on card
    images: List[Image] = []  # ← show hero image on card

    class Config:
        from_attributes = True

#add in pooja slot above poojaslot response
class PoojaSlotBulkGenerate(BaseModel):
    from_date:   date
    to_date:     date
    start_time:  time
    end_time:    time
    total_quota: int = 50


# ─────────────────────────────────────────────────────────────
# PRASADAM ITEM (Admin creates items)
# ─────────────────────────────────────────────────────────────
class PrasadamItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_available: bool = True


class PrasadamItemResponse(BaseModel):
    id: UUID
    temple_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    price: float
    weight_grams: Optional[int] = None
    image_url: Optional[str] = None
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# PRASADAM ORDER (User places order)
# ─────────────────────────────────────────────────────────────

class PrasadamOrderItemRequest(BaseModel):
    item_id: UUID
    quantity: int = Field(default=1, ge=1)


class PrasadamOrderRequest(BaseModel):
    items: List[PrasadamOrderItemRequest] = Field(..., min_length=1)
    pickup_date: Optional[date] = None
    booking_id: Optional[UUID] = None



# ─────────────────────────────────────────────────────────────
# RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class PrasadamOrderItemResponse(BaseModel):
    id: UUID
    item_id: UUID
    quantity: int
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PrasadamOrderResponse(BaseModel):
    id: UUID
    temple_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    order_reference: Optional[str] = None
    total_amount: Optional[float] = None
    pickup_date: Optional[date] = None
    status: Optional[str] = None
    items: List[PrasadamOrderItemResponse] = []
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)