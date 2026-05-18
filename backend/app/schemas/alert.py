"""
schemas/alert.py
────────────────
Pydantic schemas for the Alert resource.

Imported by:  api/v1/alerts.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


SeverityLevel = Literal["high", "medium", "low"]

AlertType = Literal[
    "zone_overcrowding",
    "loitering",
    "crossing_event",
    "zone_occupancy",
    "unknown",
]


class AlertOut(BaseModel):
    """Response schema for a single alert."""
    id: int
    camera_id: int
    type: str
    severity: str
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class AlertFilterParams(BaseModel):
    """Query parameters for GET /api/v1/alerts."""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    severity: Optional[SeverityLevel] = None
    camera_id: Optional[int] = None
