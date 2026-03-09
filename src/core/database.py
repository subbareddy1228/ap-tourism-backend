# ============================================================
# app/database.py
# Database connection — shared across all modules
# (Created by LEV148 - Perumalla Subbarao, Auth team)
# ============================================================

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:manu%40009@localhost:5432/ap_tourism")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Test connection before using
    pool_size=10,             # Max 10 connections in pool
    max_overflow=20           # Allow 20 extra connections under load
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency — inject database session into each request.
    Always closes session after request finishes.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
