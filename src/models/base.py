"""
models/base.py
Base SQLAlchemy model — all other models inherit from this.
Provides UUID primary key, created_at, updated_at automatically.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class BaseModel(Base):
    """
    Abstract base model.
    Every model in the project should inherit from this.

    Provides:
        id          → UUID primary key (auto-generated)
        created_at  → timestamp when record was created
        updated_at  → timestamp when record was last updated

    Usage:
        class Hotel(BaseModel):
            __tablename__ = "hotels"
            name = Column(String(100))
            ...
    """
    __abstract__ = True   # tells SQLAlchemy not to create a table for this

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }
