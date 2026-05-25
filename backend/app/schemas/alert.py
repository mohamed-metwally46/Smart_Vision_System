"""
schemas/alert.py
"""
from __future__ import annotations
from datetime import datetime
from typing import List
from pydantic import BaseModel

class AlertOut(BaseModel):
    id: int
    camera_id: int
    type: str
    severity: str
    message: str
    timestamp: datetime
    model_config = {"from_attributes": True}

class PaginatedAlerts(BaseModel):
    items: List[AlertOut]
    page: int
    limit: int
    total: int
