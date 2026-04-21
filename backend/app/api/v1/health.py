"""
api/v1/health.py  — matches api-reference.md §7
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.config import settings

router = APIRouter()


class HealthOut(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/", response_model=HealthOut)
async def health_check():
    import asyncpg
    import redis.asyncio as aioredis

    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        conn = await asyncpg.connect(
            settings.POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        db_status = "connected"
    except Exception:
        pass

    try:
        r = await aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception:
        pass

    return HealthOut(status="ok", database=db_status, redis=redis_status)
