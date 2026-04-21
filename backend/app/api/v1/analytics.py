"""
api/v1/analytics.py  — matches api-reference.md §5
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db

router = APIRouter()


class SummaryOut(BaseModel):
    total_in: int
    total_out: int
    current_occupancy: int
    active_alerts: int


class HeatmapOut(BaseModel):
    camera_id: int
    heatmap_url: str


class ZoneStats(BaseModel):
    zone_id: int
    name: str
    occupancy: int
    threshold: int


class ZonesOut(BaseModel):
    zones: list[ZoneStats]


@router.get("/summary", response_model=SummaryOut)
async def get_summary(db: AsyncSession = Depends(get_db)):
    from backend.app.models.event import Event
    from backend.app.models.alert import Alert

    total_in = (
        await db.execute(
            select(func.count()).where(Event.event_type == "entry_event")
        )
    ).scalar_one()

    total_out = (
        await db.execute(
            select(func.count()).where(Event.event_type == "exit_event")
        )
    ).scalar_one()

    active_alerts = (
        await db.execute(
            select(func.count()).where(Alert.resolved == False)  # noqa: E712
        )
    ).scalar_one()

    return SummaryOut(
        total_in=total_in,
        total_out=total_out,
        current_occupancy=max(0, total_in - total_out),
        active_alerts=active_alerts,
    )


@router.get("/heatmap/{camera_id}", response_model=HeatmapOut)
async def get_heatmap(camera_id: int):
    return HeatmapOut(
        camera_id=camera_id,
        heatmap_url=f"/static/heatmaps/camera_{camera_id}_latest.png",
    )


@router.get("/zones/{camera_id}", response_model=ZonesOut)
async def get_zones(camera_id: int, db: AsyncSession = Depends(get_db)):
    from backend.app.models.zone import Zone

    result = await db.execute(select(Zone).where(Zone.camera_id == camera_id))
    zones = result.scalars().all()
    return ZonesOut(
        zones=[
            ZoneStats(
                zone_id=z.id,
                name=z.name,
                occupancy=z.current_occupancy,
                threshold=z.threshold,
            )
            for z in zones
        ]
    )
