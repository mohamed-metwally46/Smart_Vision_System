"""
api/v1/logs.py  — matches api-reference.md §6
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db

router = APIRouter()


class EventLogOut(BaseModel):
    id: int
    camera_id: int
    event_type: str
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class PaginatedLogs(BaseModel):
    items: List[EventLogOut]


@router.get("/", response_model=PaginatedLogs)
async def list_logs(
    camera_id: Optional[int] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from backend.app.models.event import Event

    query = select(Event).order_by(Event.timestamp.desc())
    if camera_id:
        query = query.where(Event.camera_id == camera_id)
    if type:
        query = query.where(Event.event_type == type)

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return PaginatedLogs(items=items)
