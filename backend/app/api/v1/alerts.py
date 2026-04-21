"""
api/v1/alerts.py  — matches api-reference.md §4
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db

router = APIRouter()


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


@router.get("/", response_model=PaginatedAlerts)
async def list_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    camera_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    from backend.app.models.alert import Alert

    query = select(Alert).order_by(Alert.timestamp.desc())
    if severity:
        query = query.where(Alert.severity == severity)
    if camera_id:
        query = query.where(Alert.camera_id == camera_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedAlerts(items=items, page=page, limit=limit, total=total)


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    from backend.app.models.alert import Alert
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
