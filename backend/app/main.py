"""
main.py
───────
FastAPI application factory for the Smart Vision System backend.

Mounts:
  - REST API router   → /api/v1  (all resources via api/router.py)
  - WebSocket routes  → /ws/cameras/{camera_id}  and  /ws/alerts
  - Lifespan hooks    → startup / shutdown (DB, Redis pool, WS manager)

Import contract
───────────────
  Shared resources  ← backend.app.dependencies   (get_db, get_redis, …)
  All REST routes   ← backend.app.api.router      (api_router)
  WebSocket manager ← backend.app.websocket.manager

STRICT: No AI logic here. No business logic. Pure orchestration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.dependencies import close_redis, get_ws_manager
from backend.app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup → yield → shutdown.

    Startup order:
      1. DB     — tables must exist before workers write events
      2. Seed   — create first superuser if users table is empty
      3. Redis  — pool lazily created; we track it for clean shutdown
      4. WS manager — subscribes to Redis, must come after Redis is up
    """
    logger.info("SVS Backend starting up…")

    # 1. Database
    from backend.app.db.session import init_db
    await init_db()

    # 2. Seed first superuser
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.db.seed import seed_superuser
    async with AsyncSessionLocal() as db:
        await seed_superuser(db)

    # 3. WebSocket manager (opens Redis pub/sub connection)
    ws_manager = get_ws_manager()
    await ws_manager.startup()

    logger.info(
        "SVS Backend ready — docs at http://%s:%d/docs",
        settings.HOST,
        settings.PORT,
    )
    yield

    # ── Shutdown (reverse order) ──────────────────────────────────────────────
    logger.info("SVS Backend shutting down…")

    await ws_manager.shutdown()   # closes WebSocket connections + pub/sub
    await close_redis()           # closes shared aioredis pool from dependencies.py

    from backend.app.db.session import close_db
    await close_db()              # disposes SQLAlchemy async engine

    logger.info("SVS Backend stopped cleanly.")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Vision System API",
        description=(
            "Real-time AI surveillance and analytics backend.\n\n"
            "- **REST** `/api/v1/` — cameras, alerts, analytics, logs, health, auth, zones\n"
            "- **WebSocket** `/ws/` — live annotated frames and alert stream"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST: single include — all routes live in api/router.py ──────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── WebSocket: per-camera live frame stream ───────────────────────────────
    @app.websocket("/ws/cameras/{camera_id}")
    async def camera_stream_ws(
        websocket: WebSocket,
        camera_id: int,
        manager: ConnectionManager = Depends(get_ws_manager),
    ):
        """
        Live annotated frame stream for one camera.

        Message schema — api-reference.md §8.1:
        {
            "camera_id": int,
            "timestamp": "ISO-8601",
            "frame":     "base64-jpeg",
            "occupancy": int,
            "tracks":    [{"track_id": int, "bbox": [x, y, w, h]}]
        }

        Auth: pass JWT as query param → /ws/cameras/1?token=<jwt>
        """
        from backend.app.core.security import ws_get_current_user
        from backend.app.dependencies import get_db
        from backend.app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            user = await ws_get_current_user(websocket, db)
        if user is None:
            return  # ws_get_current_user already closed the socket with 4001

        await manager.connect(websocket, camera_id)
        try:
            while True:
                await websocket.receive_text()  # blocks; detects client disconnect
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("[WS /cameras/%s] %s", camera_id, exc)
        finally:
            await manager.disconnect(websocket, camera_id)

    # ── WebSocket: global alert stream ────────────────────────────────────────
    @app.websocket("/ws/alerts")
    async def alerts_ws(
        websocket: WebSocket,
        manager: ConnectionManager = Depends(get_ws_manager),
    ):
        """
        Live alert stream from ALL cameras.

        Message schema — api-reference.md §8.2:
        {
            "camera_id": int,
            "type":      "zone_overcrowding" | "loitering" | "crossing_event",
            "severity":  "high" | "medium" | "low",
            "message":   str,
            "timestamp": "ISO-8601",
            "metadata":  { … }
        }

        Auth: pass JWT as query param → /ws/alerts?token=<jwt>
        """
        from backend.app.core.security import ws_get_current_user
        from backend.app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            user = await ws_get_current_user(websocket, db)
        if user is None:
            return

        await manager.connect(websocket, "alerts")
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("[WS /alerts] %s", exc)
        finally:
            await manager.disconnect(websocket, "alerts")

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {"status": "ok", "docs": "/docs", "version": "1.0.0"}

    return app


# ── ASGI entry-point ──────────────────────────────────────────────────────────
app = create_app()

# Run locally:
#   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload