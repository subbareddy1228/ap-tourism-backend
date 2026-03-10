import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    JSON,
    String,
    Text,
)

from src.core.database import Base


# Destination category types
class DestinationType(str, enum.Enum):
    NATURE = "NATURE"
    HERITAGE = "HERITAGE"
    ADVENTURE = "ADVENTURE"
    COASTAL = "COASTAL"
    RELIGIOUS = "RELIGIOUS"


class Destination(Base):
    __tablename__ = "destinations"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic Information
    name = Column(String(150), nullable=False, unique=True)
    slug = Column(String(160), nullable=False, unique=True, index=True)
    district = Column(String(100), nullable=False, index=True)
    type = Column(SAEnum(DestinationType), nullable=False, index=True)

    tagline = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Travel Info
    best_season = Column(String(100), nullable=True)
    temperature_range = Column(String(50), nullable=True)

    # JSON Fields
    # how_to_reach: {by_road, by_train, by_air}
    how_to_reach = Column(JSON, nullable=True, default=dict)

    # attractions: [{name, type, distance_km}]
    attractions = Column(JSON, nullable=False, default=list)

    # nearby_temples: [{id, name, distance_km}]
    nearby_temples = Column(JSON, nullable=False, default=list)

    # images: [{url, caption, is_hero}]
    images = Column(JSON, nullable=False, default=list)

    # Ratings
    rating = Column(Float, nullable=False, default=0.0)
    reviews_count = Column(Integer, nullable=False, default=0)

    # Status Flags
    is_featured = Column(Boolean, nullable=False, default=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self):
        return f"<Destination(id={self.id}, name={self.name})>"