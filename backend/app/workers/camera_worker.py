"""
camera_worker.py
────────────────
Async camera capture loop for the Smart Vision System.

Responsibilities (Phase 2 refactor)
────────────────────────────────────
  - Open video source (file / RTSP / webcam)
  - Read frames in an asyncio-friendly loop
  - Throttle output to MAX_FPS
  - Delegate AI inference to the pipeline (no business logic)
  - Delegate ALL payload serialization to websocket/serializers.py
  - Publish results to Redis via core/redis.py (no inline aioredis)
  - Handle source exhaustion and RTSP reconnection gracefully

Fixes applied
─────────────
  - Inline aioredis creation removed → core.redis.publish_json()
  - Alert metadata fully preserved (all event fields forwarded)
  - is_alert assumption removed → events with a "severity" field are
    treated as alert-worthy and published to the alert channel

STRICT: This file does NOT import or modify any ai/ module internals.
        It only calls ai.pipeline.AIPipeline.process_frame().
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import cv2

# ── AI pipeline (completed, untouched) ───────────────────────────────────────
from ai.pipeline import AIPipeline, PipelineResult

# ── Centralised Redis layer ───────────────────────────────────────────────────
from backend.app.core.redis import publish_json

# ── Serializers ───────────────────────────────────────────────────────────────
from backend.app.websocket.serializers import (
    serialize_internal_frame,
    serialize_alert_payload,
    event_to_dict,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_FPS: int = 15
FRAME_INTERVAL: float = 1.0 / MAX_FPS
RECONNECT_DELAY: float = 3.0
MAX_RECONNECT_ATTEMPTS: int = 10

# Severities that qualify an event for the alert channel
ALERT_SEVERITIES: frozenset[str] = frozenset({"high", "medium", "low"})


# ── Channel naming (imported by manager.py and alert_worker.py) ───────────────

def camera_channel(camera_id: int | str) -> str:
    return f"camera:{camera_id}:frames"


def alert_channel(camera_id: int | str) -> str:
    return f"camera:{camera_id}:alerts"


# ── Video source helpers ───────────────────────────────────────────────────────

def _open_capture(source: str | int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {source!r}")
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _is_file(source: str | int) -> bool:
    return isinstance(source, str) and not source.lower().startswith("rtsp://")


# ── Main coroutine ────────────────────────────────────────────────────────────

async def run_camera_worker(
    camera_id: int | str,
    source: str | int,
    redis_url: str,
    pipeline: Optional[AIPipeline] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """
    Entry-point coroutine for a single camera.

    Parameters
    ----------
    camera_id  : unique camera identifier (matches DB Camera.id)
    source     : video file path, RTSP URL, or webcam index (int)
    redis_url  : used to bootstrap core/redis.py pool when running in Celery
    pipeline   : pre-constructed AIPipeline; constructed here if None
    stop_event : set() to stop the loop gracefully
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    if pipeline is None:
        pipeline = AIPipeline()

    # Bootstrap the shared Redis pool when running inside a Celery process
    # (the FastAPI pool won't have been initialised in a worker process).
    import backend.app.core.redis as _redis_core
    if _redis_core._pool is None:
        import redis.asyncio as aioredis
        _redis_core._pool = await aioredis.from_url(
            redis_url, encoding="utf-8", decode_responses=True, max_connections=10
        )

    frame_ch = camera_channel(camera_id)
    alert_ch = alert_channel(camera_id)

    logger.info("[CameraWorker %s] Starting — source=%r", camera_id, source)

    reconnect_attempts = 0

    while not stop_event.is_set():
        cap = None
        try:
            cap = await asyncio.get_event_loop().run_in_executor(
                None, _open_capture, source
            )
            reconnect_attempts = 0
            logger.info("[CameraWorker %s] Source opened.", camera_id)

            await _capture_loop(
                camera_id=camera_id,
                cap=cap,
                pipeline=pipeline,
                frame_ch=frame_ch,
                alert_ch=alert_ch,
                stop_event=stop_event,
            )

        except asyncio.CancelledError:
            logger.info("[CameraWorker %s] Cancelled.", camera_id)
            break

        except Exception as exc:
            logger.exception("[CameraWorker %s] Error: %s", camera_id, exc)

        finally:
            if cap is not None:
                cap.release()

        if _is_file(source):
            logger.info("[CameraWorker %s] Video file exhausted — done.", camera_id)
            break

        reconnect_attempts += 1
        if reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
            logger.error(
                "[CameraWorker %s] Max reconnect attempts (%d) exceeded.",
                camera_id, MAX_RECONNECT_ATTEMPTS,
            )
            break

        wait = RECONNECT_DELAY * reconnect_attempts
        logger.warning(
            "[CameraWorker %s] Reconnecting in %.1f s (attempt %d/%d)…",
            camera_id, wait, reconnect_attempts, MAX_RECONNECT_ATTEMPTS,
        )
        await asyncio.sleep(wait)

    logger.info("[CameraWorker %s] Worker stopped.", camera_id)


async def _capture_loop(
    camera_id: int | str,
    cap: cv2.VideoCapture,
    pipeline: AIPipeline,
    frame_ch: str,
    alert_ch: str,
    stop_event: asyncio.Event,
) -> None:
    """Inner per-frame loop. Exits on EOF or stop_event."""
    loop = asyncio.get_event_loop()
    last_publish_time = 0.0

    while not stop_event.is_set():
        # 1. Read frame
        ret, frame = await loop.run_in_executor(None, cap.read)
        if not ret:
            logger.debug("[CameraWorker %s] EOF or frame drop.", camera_id)
            break

        # 2. FPS throttle
        now = time.monotonic()
        elapsed = now - last_publish_time
        if elapsed < FRAME_INTERVAL:
            await asyncio.sleep(FRAME_INTERVAL - elapsed)
            continue

        # 3. AI inference
        try:
            result: PipelineResult = await loop.run_in_executor(
                None, pipeline.process_frame, frame
            )
        except Exception as exc:
            logger.warning(
                "[CameraWorker %s] Pipeline error (frame skipped): %s", camera_id, exc
            )
            continue

        last_publish_time = time.monotonic()

        # 4. Publish internal frame payload (§9.1 contract)
        try:
            internal_payload = await loop.run_in_executor(
                None, serialize_internal_frame, camera_id, result
            )
            await publish_json(frame_ch, internal_payload)
        except Exception as exc:
            logger.warning(
                "[CameraWorker %s] Redis publish (frame) failed: %s", camera_id, exc
            )

        # 5. Publish alert events — check severity, preserve full metadata
        for event in (result.events or []):
            try:
                event_dict = event_to_dict(event)
            except Exception:
                continue

            if event_dict.get("severity", "") in ALERT_SEVERITIES:
                try:
                    alert_payload = serialize_alert_payload(camera_id, event_dict)
                    await publish_json(alert_ch, alert_payload)
                except Exception as exc:
                    logger.warning(
                        "[CameraWorker %s] Redis publish (alert) failed: %s",
                        camera_id, exc,
                    )

        # 6. Yield control
        await asyncio.sleep(0)
