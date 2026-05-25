"""
schemas/alert.py
<<<<<<< HEAD
"""
from __future__ import annotations
from datetime import datetime
from typing import List
from pydantic import BaseModel

class AlertOut(BaseModel):
=======
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
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
    id: int
    camera_id: int
    type: str
    severity: str
    message: str
    timestamp: datetime
<<<<<<< HEAD
    model_config = {"from_attributes": True}

class PaginatedAlerts(BaseModel):
    items: List[AlertOut]
    page: int
    limit: int
    total: int
=======

    model_config = {"from_attributes": True}


class AlertFilterParams(BaseModel):
    """Query parameters for GET /api/v1/alerts."""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    severity: Optional[SeverityLevel] = None
    camera_id: Optional[int] = None
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
