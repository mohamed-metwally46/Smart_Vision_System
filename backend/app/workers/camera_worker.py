"""
camera_worker.py
────────────────
Async camera capture loop for the Smart Vision System.

Responsibilities:
  - Open video source (file / RTSP / webcam)
  - Read frames in an asyncio-friendly loop
  - Call AI pipeline (process_frame) — no business logic here
  - Throttle output to MAX_FPS
  - Publish PipelineResult payload to Redis pub/sub channel per camera
  - Handle source exhaustion (EOF on video files) and reconnection on RTSP loss

STRICT: This file does NOT import or modify any ai/ module internals.
        It only calls ai.pipeline.Pipeline.process_frame().
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional

import cv2
import redis.asyncio as aioredis

# ── AI pipeline (updated to match Pipeline class name) ──────────────────────
from backend.ai.pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
MAX_FPS: int = 15                        # hard cap — never push more than 15 fps to Redis
FRAME_INTERVAL: float = 1.0 / MAX_FPS   # ≈ 66.7 ms
RECONNECT_DELAY: float = 3.0            # seconds to wait before re-opening a lost RTSP stream
MAX_RECONNECT_ATTEMPTS: int = 10
JPEG_QUALITY: int = 75                  # encode quality; lower = smaller payload


# ── Redis channel naming convention ─────────────────────────────────────────
def camera_channel(camera_id: int | str) -> str:
    return f"camera:{camera_id}:frames"


def alert_channel(camera_id: int | str) -> str:
    return f"camera:{camera_id}:alerts"


def event_channel(camera_id: int | str) -> str:
    return f"camera:{camera_id}:events"


# ── Payload builders ─────────────────────────────────────────────────────────

def _encode_frame(frame) -> str:
    """Encode an annotated OpenCV frame to a base64 JPEG string."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _build_frame_payload(camera_id: int | str, result: PipelineResult) -> str:
    """
    Build the JSON string that the WebSocket manager will forward to browsers.
    """
    tracks = [
        {"track_id": t.track_id, "bbox": list(t.bbox)}
        for t in (result.tracks or [])
    ]

    payload = {
        "camera_id": camera_id,
        "timestamp": _utcnow(),
        "frame": _encode_frame(result.annotated_frame),
        "occupancy": len(tracks),
        "tracks": tracks,
        "events": _serialize_events(result.events),
        "business_events": result.business_events,
    }
    return json.dumps(payload)


def _build_alert_payload(camera_id: int | str, event: dict) -> str:
    """Build an alert JSON string from a business-logic event dict."""
    return json.dumps({
        "camera_id": camera_id,
        "type": event.get("type", "unknown"),
        "severity": event.get("severity", "low"),
        "message": event.get("message", ""),
        "timestamp": _utcnow(),
    })


def _build_event_payload(camera_id: int | str, event: dict) -> str:
    """Build a general business event JSON string."""
    return json.dumps({
        "camera_id": camera_id,
        "type": event.get("type", "unknown"),
        "message": event.get("message", f"Event: {event.get('type')}"),
        "timestamp": _utcnow(),
    })


def _serialize_events(events) -> list:
    if not events:
        return []
    result = []
    for e in events:
        try:
            result.append(asdict(e) if hasattr(e, "__dataclass_fields__") else dict(e))
        except Exception:
            result.append(str(e))
    return result


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── Source helpers ────────────────────────────────────────────────────────────

def _open_capture(source: str | int) -> cv2.VideoCapture:
    """Open a VideoCapture; raise RuntimeError if it fails to open."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {source!r}")
    # For RTSP: buffer only 1 frame to minimise latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _is_rtsp(source: str | int) -> bool:
    return isinstance(source, str) and source.lower().startswith("rtsp://")


def _is_file(source: str | int) -> bool:
    return isinstance(source, str) and not source.lower().startswith("rtsp://")


# ── Main worker coroutine ─────────────────────────────────────────────────────

async def run_camera_worker(
    camera_id: int | str,
    source: str | int,
    redis_url: str,
    pipeline: Optional[Pipeline] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """
    Entry-point coroutine for a single camera.
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    if pipeline is None:
        from backend.app.config import settings
        pipeline = Pipeline(
            model_path=settings.MODEL_PATH,
            weapon_model_path=settings.WEAPON_MODEL_PATH,
            weapon_imgsz=settings.WEAPON_IMGSZ
        )

    redis_client: aioredis.Redis = await aioredis.from_url(
        redis_url, encoding="utf-8", decode_responses=True
    )

    frame_ch = camera_channel(camera_id)
    alert_ch = alert_channel(camera_id)
    event_ch = event_channel(camera_id)

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
                redis_client=redis_client,
                frame_ch=frame_ch,
                alert_ch=alert_ch,
                event_ch=event_ch,
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

        # ── EOF on video file → stop (no reconnect needed) ──────────────────
        if _is_file(source):
            logger.info("[CameraWorker %s] Video file exhausted — worker done.", camera_id)
            break

        # ── RTSP / webcam loss → reconnect with back-off ─────────────────────
        reconnect_attempts += 1
        if reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
            logger.error(
                "[CameraWorker %s] Exceeded max reconnect attempts (%d). Giving up.",
                camera_id,
                MAX_RECONNECT_ATTEMPTS,
            )
            break

        wait = RECONNECT_DELAY * reconnect_attempts
        logger.warning(
            "[CameraWorker %s] Reconnecting in %.1f s (attempt %d/%d)…",
            camera_id, wait, reconnect_attempts, MAX_RECONNECT_ATTEMPTS,
        )
        await asyncio.sleep(wait)

    await redis_client.aclose()
    logger.info("[CameraWorker %s] Worker stopped.", camera_id)


async def _capture_loop(
    camera_id,
    cap: cv2.VideoCapture,
    pipeline: Pipeline,
    redis_client: aioredis.Redis,
    frame_ch: str,
    alert_ch: str,
    event_ch: str,
    stop_event: asyncio.Event,
) -> None:
    """Inner frame-reading loop."""
    loop = asyncio.get_event_loop()
    last_publish_time = 0.0

    while not stop_event.is_set():
        ret, frame = await loop.run_in_executor(None, cap.read)

        if not ret:
            logger.debug("[CameraWorker %s] cap.read() returned False — EOF or drop.", camera_id)
            break

        now = time.monotonic()
        elapsed = now - last_publish_time
        if elapsed < FRAME_INTERVAL:
            await asyncio.sleep(FRAME_INTERVAL - elapsed)
            continue

        try:
            result: PipelineResult = await loop.run_in_executor(
                None, pipeline.process_frame, frame
            )
        except Exception as exc:
            logger.warning("[CameraWorker %s] Pipeline error: %s", camera_id, exc)
            continue

        last_publish_time = time.monotonic()

        # ── 4. Publish annotated frame ───────────────────────────────────────
        try:
            frame_payload = await loop.run_in_executor(
                None, _build_frame_payload, camera_id, result
            )
            await redis_client.publish(frame_ch, frame_payload)
        except Exception as exc:
            logger.warning("[CameraWorker %s] Redis publish (frame) failed: %s", camera_id, exc)

        # ── 5. Publish events & alerts ───────────────────────────────────────
        all_alerts = []
        all_events = []
        
        for evt in result.business_events:
            if "alert" in evt.get("type", "").lower() or "overcrowding" in evt.get("type", "").lower():
                all_alerts.append(evt)
            else:
                all_events.append(evt)
        
        for event in (result.events or []):
            event_dict = asdict(event) if hasattr(event, "__dataclass_fields__") else dict(event)
            if event_dict.get("is_alert"):
                all_alerts.append(event_dict)

        for alert in all_alerts:
            try:
                alert_payload = _build_alert_payload(camera_id, alert)
                await redis_client.publish(alert_ch, alert_payload)
            except Exception as exc:
                logger.warning("[CameraWorker %s] Redis publish (alert) failed: %s", camera_id, exc)
        
        for biz_event in all_events:
            try:
                event_payload = _build_event_payload(camera_id, biz_event)
                await redis_client.publish(event_ch, event_payload)
            except Exception as exc:
                logger.warning("[CameraWorker %s] Redis publish (event) failed: %s", camera_id, exc)

        await asyncio.sleep(0)
