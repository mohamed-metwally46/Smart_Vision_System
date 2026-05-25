"""
schemas/camera.py
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class CameraBase(BaseModel):
    name: str
    source_type: str
    source_url: str
    is_active: bool = True

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source_url: Optional[str] = None
    is_active: Optional[bool] = None

class CameraOut(CameraBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}
