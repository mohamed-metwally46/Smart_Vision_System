"""
api/v1/cameras.py
─────────────────
Camera CRUD endpoints — matches api-reference.md §3.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    source_type: str          # "rtsp" | "file" | "usb"
    source_url: str
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source_url: Optional[str] = None
    is_active: Optional[bool] = None


class CameraOut(BaseModel):
    id: int
    name: str
    source_type: str
    source_url: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(payload: CameraCreate, db: AsyncSession = Depends(get_db)):
    from backend.app.models.camera import Camera
    cam = Camera(**payload.model_dump())
    db.add(cam)
    await db.flush()
    await db.refresh(cam)

    # ── Dispatch Celery worker for this camera ────────────────────────────────
    from backend.app.workers.celery_app import dispatch_camera_worker
    from backend.app.config import settings
    task_id = dispatch_camera_worker(cam.id, cam.source_url, settings.REDIS_URL)
    cam.worker_task_id = task_id
    await db.flush()

    return cam


@router.get("/", response_model=List[CameraOut])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    from backend.app.models.camera import Camera
    result = await db.execute(select(Camera))
    return result.scalars().all()


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    from backend.app.models.camera import Camera
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.put("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: int, payload: CameraUpdate, db: AsyncSession = Depends(get_db)
):
    from backend.app.models.camera import Camera
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(cam, field, value)
    await db.flush()
    await db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    from backend.app.models.camera import Camera
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # ── Stop Celery worker if running ─────────────────────────────────────────
    if cam.worker_task_id:
        from backend.app.workers.celery_app import stop_camera_worker
        stop_camera_worker(cam.worker_task_id)

    await db.delete(cam)
