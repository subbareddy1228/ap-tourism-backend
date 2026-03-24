"""
schemas/tracking.py
M18 — Tracking Module Pydantic schemas

Three schemas per resource (project standard):
    CreateSchema   — POST body
    UpdateSchema   — PUT body (all optional)
    ResponseSchema — output (used inside APIResponse.data)

Branch : feature/LEV156-tracking
Author : LEV156 Ram Kishore Pawar
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# REQUEST  SCHEMAS
# ─────────────────────────────────────────────────────────────

class TrackingSessionCreate(BaseModel):
    """Body for POST /tracking/sessions  (driver or guide starts trip)."""
    booking_id      : UUID
    tracker_role    : str = Field(..., description="DRIVER or GUIDE")
    destination_lat : Optional[float] = Field(None, ge=-90,  le=90)
    destination_lng : Optional[float] = Field(None, ge=-180, le=180)


class LocationPingCreate(BaseModel):
    """
    Body for POST /tracking/sessions/{id}/ping.
    Sent by driver/guide app every 5–10 seconds.
    """
    latitude  : float = Field(..., ge=-90,  le=90)
    longitude : float = Field(..., ge=-180, le=180)
    accuracy  : Optional[float] = Field(None, ge=0,   description="Metres")
    speed     : Optional[float] = Field(None, ge=0,   description="km/h")
    bearing   : Optional[float] = Field(None, ge=0,   le=360, description="Degrees 0–360")
    altitude  : Optional[float] = Field(None,          description="Metres above sea level")

    # Send updated destination coords only when the next stop changes
    destination_lat : Optional[float] = Field(None, ge=-90,  le=90)
    destination_lng : Optional[float] = Field(None, ge=-180, le=180)


class ShareToggleRequest(BaseModel):
    """Body for PUT /tracking/sessions/{id}/share."""
    share_enabled: bool


# ─────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS  (serialised inside APIResponse.data)
# ─────────────────────────────────────────────────────────────

class CurrentLocationResponse(BaseModel):
    latitude              : float
    longitude             : float
    accuracy              : Optional[float]
    speed                 : Optional[float]
    bearing               : Optional[float]
    altitude              : Optional[float]
    address               : Optional[str]
    eta_minutes           : Optional[float]
    distance_remaining_km : Optional[float]
    destination_lat       : Optional[float]
    destination_lng       : Optional[float]
    pinged_at             : Optional[datetime]


class TrackingSessionResponse(BaseModel):
    id                : UUID
    booking_id        : UUID
    tracker_role      : str
    status            : str
    share_token       : str
    share_enabled     : bool
    trip_started_at   : Optional[datetime]
    trip_completed_at : Optional[datetime]
    created_at        : datetime
    current_location  : Optional[CurrentLocationResponse] = None


class PingResponse(BaseModel):
    """Returned after a successful GPS ping."""
    session_id            : UUID
    eta_minutes           : Optional[float]
    distance_remaining_km : Optional[float]
    message               : str = "Location updated"


class BreadcrumbPoint(BaseModel):
    latitude  : float
    longitude : float
    speed     : Optional[float]
    bearing   : Optional[float]
    pinged_at : datetime


class LocationHistoryResponse(BaseModel):
    session_id : UUID
    booking_id : UUID
    points     : List[BreadcrumbPoint]
    total      : int


class ShareLinkResponse(BaseModel):
    share_token   : str
    share_enabled : bool
    share_url     : str
