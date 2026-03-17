# Empty file — will cause ImportError
from src.models.base import Base  # this will fail
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass