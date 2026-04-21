"""
websocket/manager.py
────────────────────
ConnectionManager for the Smart Vision System.

Responsibilities:
  - Accept FastAPI WebSocket connections keyed by camera_id
  - Subscribe to Redis pub/sub channels for frame + alert payloads
  - Broadcast arriving Redis messages to all connected dashboard clients
  - Handle disconnection cleanly without crashing the broadcast loop
  - One Redis subscriber coroutine per active camera channel (created lazily)

Data flow:
    Redis channel  →  _redis_listener()  →  broadcast()  →  WebSocket clients

STRICT: No AI logic here. No frame processing. Pure orchestration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Set

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from backend.app.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages all active WebSocket connections and their Redis subscriptions.

    Usage (inside FastAPI endpoint):
        manager = ConnectionManager()             # singleton via lifespan
        await manager.connect(websocket, camera_id)
        try:
            await websocket.receive_text()        # keep alive
        except WebSocketDisconnect:
            await manager.disconnect(websocket, camera_id)
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.REDIS_URL

        # camera_id → set of connected WebSocket clients
        self._connections: Dict[str | int, Set[WebSocket]] = defaultdict(set)

        # camera_id → asyncio.Task running the Redis listener
        self._listener_tasks: Dict[str | int, asyncio.Task] = {}

        # Shared Redis client (asyncio)
        self._redis: aioredis.Redis | None = None
        self._redis_lock = asyncio.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        """Call once during FastAPI lifespan startup."""
        self._redis = await aioredis.from_url(
            self._redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info("[WSManager] Redis client connected — %s", self._redis_url)

    async def shutdown(self) -> None:
        """Call once during FastAPI lifespan shutdown."""
        # Cancel all listener tasks
        for camera_id, task in list(self._listener_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._listener_tasks.clear()

        # Close all WebSocket connections
        for camera_id, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    await ws.close()
                except Exception:
                    pass
        self._connections.clear()

        if self._redis:
            await self._redis.aclose()
            self._redis = None

        logger.info("[WSManager] Shutdown complete.")

    # ── Public API ────────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, camera_id: int | str) -> None:
        """
        Accept a new WebSocket connection for the given camera_id.
        Starts a Redis listener for this camera if one is not already running.
        """
        await websocket.accept()
        self._connections[camera_id].add(websocket)
        logger.info(
            "[WSManager] Client connected — camera_id=%s total_clients=%d",
            camera_id,
            len(self._connections[camera_id]),
        )
        await self._ensure_listener(camera_id)

    async def disconnect(self, websocket: WebSocket, camera_id: int | str) -> None:
        """Remove a WebSocket connection. Stops the Redis listener if no clients remain."""
        self._connections[camera_id].discard(websocket)
        logger.info(
            "[WSManager] Client disconnected — camera_id=%s remaining=%d",
            camera_id,
            len(self._connections[camera_id]),
        )

        # Stop the listener when the last client leaves
        if not self._connections[camera_id]:
            await self._stop_listener(camera_id)
            del self._connections[camera_id]

    async def broadcast_to_camera(
        self, camera_id: int | str, message: str
    ) -> None:
        """Send a raw JSON string to every client subscribed to camera_id."""
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(camera_id, [])):
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                dead.append(ws)
            except Exception as exc:
                logger.debug("[WSManager] Send error (%s): %s", camera_id, exc)
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws, camera_id)

    async def broadcast_alert(self, alert_payload: str) -> None:
        """
        Broadcast an alert to ALL connected clients regardless of camera_id.
        Used by the /ws/alerts global endpoint.
        """
        for camera_id, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    await ws.send_text(alert_payload)
                except Exception:
                    pass

    # ── Redis listener management ─────────────────────────────────────────────

    async def _ensure_listener(self, camera_id: int | str) -> None:
        """Start a Redis subscription listener for camera_id if not already running."""
        if camera_id in self._listener_tasks:
            task = self._listener_tasks[camera_id]
            if not task.done():
                return  # already running

        task = asyncio.create_task(
            self._redis_listener(camera_id),
            name=f"redis-listener-{camera_id}",
        )
        self._listener_tasks[camera_id] = task
        logger.debug("[WSManager] Listener started — camera_id=%s", camera_id)

    async def _stop_listener(self, camera_id: int | str) -> None:
        task = self._listener_tasks.pop(camera_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.debug("[WSManager] Listener stopped — camera_id=%s", camera_id)

    async def _redis_listener(self, camera_id: int | str) -> None:
        """
        Long-running coroutine that subscribes to both the frame channel
        and the alert channel for a given camera_id and forwards messages
        to connected WebSocket clients.
        """
        from backend.app.workers.camera_worker import camera_channel, alert_channel

        frame_ch = camera_channel(camera_id)
        alert_ch = alert_channel(camera_id)

        # Each listener gets its own pub/sub connection to avoid contention
        redis_sub: aioredis.Redis = await aioredis.from_url(
            self._redis_url, encoding="utf-8", decode_responses=True
        )
        pubsub = redis_sub.pubsub()

        try:
            await pubsub.subscribe(frame_ch, alert_ch)
            logger.info(
                "[WSManager] Subscribed to Redis channels: %s, %s", frame_ch, alert_ch
            )

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                data: str = message["data"]
                channel: str = message["channel"]

                # ── Frame messages → camera-specific broadcast ────────────────
                if channel == frame_ch:
                    await self.broadcast_to_camera(camera_id, data)

                # ── Alert messages → global alert broadcast ───────────────────
                elif channel == alert_ch:
                    await self.broadcast_alert(data)

        except asyncio.CancelledError:
            logger.info("[WSManager] Listener cancelled — camera_id=%s", camera_id)
        except Exception as exc:
            logger.exception("[WSManager] Listener error — camera_id=%s: %s", camera_id, exc)
        finally:
            await pubsub.unsubscribe(frame_ch, alert_ch)
            await pubsub.close()
            await redis_sub.aclose()
            logger.debug("[WSManager] Listener cleaned up — camera_id=%s", camera_id)

    # ── Debug helpers ─────────────────────────────────────────────────────────

    @property
    def active_cameras(self) -> list:
        return list(self._connections.keys())

    def client_count(self, camera_id: int | str) -> int:
        return len(self._connections.get(camera_id, set()))


# ── Module-level singleton (imported by main.py) ───────────────────────────────
manager = ConnectionManager()
