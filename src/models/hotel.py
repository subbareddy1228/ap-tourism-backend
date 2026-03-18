from sqlalchemy import Column, String, Boolean, Float, Text, JSON, ForeignKey, Integer, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.models.base import BaseModel
from src.common.enums import RoomType


class Hotel(BaseModel):
    __tablename__ = "hotels"

    partner_id          = Column(UUID(as_uuid=False), nullable=True)  # no FK
    name                = Column(String(255), nullable=False, index=True)
    description         = Column(Text,        nullable=True)
    address_line1       = Column(String(255), nullable=False)
    address_line2       = Column(String(255), nullable=True)
    city                = Column(String(100), nullable=False, index=True)
    district            = Column(String(100), nullable=False)
    state               = Column(String(100), default="Andhra Pradesh")
    pincode             = Column(String(10),  nullable=False)
    latitude            = Column(Float,       nullable=True)
    longitude           = Column(Float,       nullable=True)
    star_rating         = Column(Integer,     default=3)
    check_in_time       = Column(String(10),  default="12:00")
    check_out_time      = Column(String(10),  default="11:00")
    cancellation_policy = Column(Text,        nullable=True)
    is_active           = Column(Boolean,     default=True)
    is_featured         = Column(Boolean,     default=False)
    booking_count       = Column(Integer,     default=0)
    average_rating      = Column(Float,       default=0.0)
    total_reviews       = Column(Integer,     default=0)
    amenities           = Column(JSON,        default=list)
    images              = Column(JSON,        default=list)
    phone               = Column(String(15),  nullable=True)
    email               = Column(String(255), nullable=True)
    website             = Column(String(255), nullable=True)

    rooms = relationship("HotelRoom", back_populates="hotel", cascade="all, delete-orphan")


class HotelRoom(BaseModel):
    __tablename__ = "hotel_rooms"

    hotel_id        = Column(UUID(as_uuid=False), ForeignKey("hotels.id"), nullable=False)
    name            = Column(String(100), nullable=False)
    description     = Column(Text,        nullable=True)
    room_type       = Column(SAEnum(RoomType), default=RoomType.STANDARD)
    capacity        = Column(Integer,     nullable=False, default=2)
    price_per_night = Column(Float,       nullable=False)
    total_rooms     = Column(Integer,     nullable=False, default=1)
    available_rooms = Column(Integer,     nullable=False, default=1)
    amenities       = Column(JSON,        default=list)
    images          = Column(JSON,        default=list)
    is_active       = Column(Boolean,     default=True)

    hotel  = relationship("Hotel",          back_populates="rooms")
    blocks = relationship("HotelRoomBlock", back_populates="room", cascade="all, delete-orphan")


class HotelRoomBlock(BaseModel):
    __tablename__ = "hotel_room_blocks"

    room_id    = Column(UUID(as_uuid=False), ForeignKey("hotel_rooms.id"), nullable=False)
    block_date = Column(String(20),  nullable=False)
    reason     = Column(String(255), nullable=True)

    room = relationship("HotelRoom", back_populates="blocks")