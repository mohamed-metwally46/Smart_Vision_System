"""
schemas/camera.py
<<<<<<< HEAD
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
=======
─────────────────
Pydantic schemas for the Camera resource.

Imported by:  api/v1/cameras.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CameraCreate(BaseModel):
    """Request body for POST /api/v1/cameras."""
    name: str = Field(..., min_length=1, max_length=128)
    source_type: str = Field(..., pattern="^(rtsp|file|usb)$")
    source_url: str = Field(..., max_length=512)
    is_active: bool = True


class CameraUpdate(BaseModel):
    """Request body for PUT /api/v1/cameras/{id}. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    source_url: Optional[str] = Field(None, max_length=512)
    is_active: Optional[bool] = None


class CameraOut(BaseModel):
    """Response schema for camera read operations."""
    id: int
    name: str
    source_type: str
    source_url: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CameraListItem(BaseModel):
    """Compact schema used in list responses."""
    id: int
    name: str
    is_active: bool

>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
    model_config = {"from_attributes": True}
