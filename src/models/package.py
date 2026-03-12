import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from src.core.database import Base

# Define enum directly here
class PackageType(str, enum.Enum):
    PILGRIMAGE = "PILGRIMAGE"
    LEISURE    = "LEISURE"
    ADVENTURE  = "ADVENTURE"



class Package(Base):
    __tablename__ = "packages"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic Information
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)

    # Foreign Key → Destination
    destination_id = Column(String(36), ForeignKey("destinations.id"), nullable=False, index=True)

    # Duration
    duration_days = Column(Integer, nullable=False)
    duration_nights = Column(Integer, nullable=False)

    # Type
    type = Column(SAEnum(PackageType), nullable=False, index=True)

    # Pricing
    price = Column(Float, nullable=False)

    # Group Info
    group_size = Column(Integer, nullable=True)

    # JSON Fields
    # itinerary: [{day, title, description, meals, accommodation}]
    itinerary = Column(JSON, nullable=False, default=list)

    # inclusions: ["Breakfast", "Transport", ...]
    inclusions = Column(JSON, nullable=False, default=list)

    # exclusions: ["Airfare", "Personal expenses", ...]
    exclusions = Column(JSON, nullable=False, default=list)

    # pricing_rules: [{label, min_people, max_people, price_per_person}]
    pricing_rules = Column(JSON, nullable=True, default=list)

    # departure_dates: ["2026-04-01", "2026-04-15", ...]
    departure_dates = Column(JSON, nullable=False, default=list)

    # images: [{url, caption, is_hero}]
    images = Column(JSON, nullable=False, default=list)

    # Ratings
    rating = Column(Float, nullable=False, default=0.0)
    reviews_count = Column(Integer, nullable=False, default=0)

    # Popularity
    total_bookings = Column(Integer, nullable=False, default=0)

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

    # Relationships
    destination = relationship("Destination", backref="packages")

    def __repr__(self):
        return f"<Package(id={self.id}, name={self.name})>"