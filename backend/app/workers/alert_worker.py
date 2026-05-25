"""
alert_worker.py
───────────────
<<<<<<< HEAD
Async consumer for the Smart Vision System that persists alerts to the database.

Responsibilities:
  - Subscribe to Redis alert channels (camera:*:alerts)
  - Parse JSON alert payloads
  - Create and save Alert objects to PostgreSQL
  - Run as a long-lived background service
=======
Redis consumer that persists alert and event payloads to PostgreSQL.

Architecture position (api-reference.md §12):
    AI Workers → AlertEngine → Redis → alert_worker → PostgreSQL
                                     → WebSocket Manager → Frontend

Responsibilities
────────────────
  - Subscribe to ALL camera alert channels: camera:*:alerts
  - Parse and validate each incoming payload safely
  - Persist Alert records for high/medium severity events
  - Persist Event records for entry_event / exit_event types
  - Preserve the full metadata field — never discard it
  - Retry failed DB writes without crashing the loop
  - Log every decision with enough detail to debug production issues

Entry-points
────────────
  run_alert_worker(redis_url, stop_event)   → asyncio coroutine (used by Celery)
  AlertWorker                               → class form for direct instantiation

Celery task is registered in celery_app.py as start_alert_worker.
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
<<<<<<< HEAD

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.alert import Alert

logger = logging.getLogger(__name__)


async def run_alert_worker(stop_event: asyncio.Event | None = None) -> None:
    """
    Main entry point for the alert persistence worker.
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    redis_client: aioredis.Redis = await aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    
    # We use psubscribe to capture alerts from ALL cameras
    pubsub = redis_client.pubsub()
    alert_pattern = "camera:*:alerts"

    try:
        await pubsub.psubscribe(alert_pattern)
        logger.info("[AlertWorker] Subscribed to %s", alert_pattern)

        while not stop_event.is_set():
            try:
                # listen() blocks; we use a timeout to check stop_event periodically
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    continue

                data = message.get("data")
                if not data:
                    continue

                await _process_alert_payload(data)

            except Exception as exc:
                logger.error("[AlertWorker] Processing error: %s", exc, exc_info=True)
                await asyncio.sleep(1.0)

    except asyncio.CancelledError:
        logger.info("[AlertWorker] Cancelled.")
    finally:
        await pubsub.punsubscribe(alert_pattern)
        await pubsub.close()
        await redis_client.aclose()
        logger.info("[AlertWorker] Stopped.")


async def _process_alert_payload(payload_str: str) -> None:
    """Parse JSON and save to database."""
    try:
        data = json.loads(payload_str)
        
        # Schema from camera_worker.py:
        # {
        #     "camera_id": int,
        #     "type": str,
        #     "severity": str,
        #     "message": str,
        #     "timestamp": str (ISO-8601)
        # }
        
        camera_id = data.get("camera_id")
        alert_type = data.get("type", "unknown")
        severity = data.get("severity", "medium")
        message = data.get("message", "")
        ts_str = data.get("timestamp")
        
        # Convert ISO-8601 string to datetime object
        if ts_str:
            timestamp = datetime.fromisoformat(ts_str)
        else:
            timestamp = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            new_alert = Alert(
=======
from typing import Any, Optional

import redis.asyncio as aioredis

from backend.app.config import settings

logger = logging.getLogger(__name__)

# ── Alert types that should generate an Alert DB record ──────────────────────
ALERT_TYPES: frozenset[str] = frozenset({
    "zone_overcrowding",
    "loitering",
    "crossing_event",
    "zone_occupancy",
})

# ── Event types that should generate an Event DB record ──────────────────────
EVENT_TYPES: frozenset[str] = frozenset({
    "entry_event",
    "exit_event",
    "crossing_event",
})

# ── Severities that create a DB Alert record ──────────────────────────────────
PERSIST_SEVERITIES: frozenset[str] = frozenset({"high", "medium", "low"})

# ── Redis pattern to subscribe to all camera alert channels ───────────────────
ALERT_CHANNEL_PATTERN: str = "camera:*:alerts"
FRAME_CHANNEL_PATTERN: str  = "camera:*:frames"  # entry/exit events embedded in frame payload


# ─────────────────────────────────────────────────────────────────────────────
# Payload validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_payload(raw: str) -> Optional[dict[str, Any]]:
    """
    Safely decode a JSON string into a dict.
    Returns None (and logs a warning) if the string is invalid JSON.
    """
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            logger.warning("[AlertWorker] Payload is not a dict: %r", raw[:120])
            return None
        return data
    except json.JSONDecodeError as exc:
        logger.warning("[AlertWorker] JSON decode error: %s — raw=%r", exc, raw[:120])
        return None


def _extract_camera_id(payload: dict, channel: str) -> Optional[int]:
    """
    Extract camera_id from the payload dict.
    Falls back to parsing it from the channel name (camera:{id}:alerts).
    """
    if "camera_id" in payload:
        try:
            return int(payload["camera_id"])
        except (TypeError, ValueError):
            pass

    # Parse from channel name: "camera:7:alerts" → 7
    parts = channel.split(":")
    if len(parts) == 3 and parts[0] == "camera" and parts[2] == "alerts":
        try:
            return int(parts[1])
        except ValueError:
            pass

    logger.warning("[AlertWorker] Cannot extract camera_id from payload or channel=%r", channel)
    return None


def _parse_timestamp(payload: dict) -> datetime:
    """
    Parse ISO-8601 timestamp from payload or return now(UTC) as fallback.
    """
    raw_ts = payload.get("timestamp")
    if raw_ts:
        try:
            return datetime.fromisoformat(raw_ts)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# DB persistence helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_alert(camera_id: int, payload: dict) -> None:
    """
    Write one Alert row to PostgreSQL.

    Preserves all metadata. Uses an isolated async session so a DB failure
    does not affect the Redis listener loop.
    """
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.models.alert import Alert

    alert_type = payload.get("type", "unknown")
    severity   = payload.get("severity", "low")
    message    = payload.get("message", "")
    metadata   = payload.get("metadata", {})
    timestamp  = _parse_timestamp(payload)

    # Flatten metadata into the message if it carries useful info and message is empty
    if not message and metadata:
        message = json.dumps(metadata, default=str)

    async with AsyncSessionLocal() as session:
        try:
            alert = Alert(
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
                camera_id=camera_id,
                type=alert_type,
                severity=severity,
                message=message,
<<<<<<< HEAD
                timestamp=timestamp
            )
            db.add(new_alert)
            await db.commit()
            logger.info("[AlertWorker] Persisted alert: %s (camera=%s)", alert_type, camera_id)

    except json.JSONDecodeError:
        logger.error("[AlertWorker] Failed to decode JSON payload: %r", payload_str)
    except Exception as exc:
        logger.error("[AlertWorker] Database persistence failed: %s", exc)


if __name__ == "__main__":
    # For standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    try:
        asyncio.run(run_alert_worker())
    except KeyboardInterrupt:
        pass
=======
                resolved=False,
                timestamp=timestamp,
            )
            session.add(alert)
            await session.commit()
            logger.debug(
                "[AlertWorker] Alert persisted — camera=%s type=%s severity=%s",
                camera_id, alert_type, severity,
            )
        except Exception as exc:
            await session.rollback()
            logger.error(
                "[AlertWorker] DB write failed (alert) — camera=%s: %s",
                camera_id, exc,
            )


async def _persist_event(camera_id: int, payload: dict) -> None:
    """
    Write one Event row to PostgreSQL for entry/exit/crossing events.
    """
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.models.event import Event

    event_type = payload.get("type", "unknown")
    message    = payload.get("message", "")
    timestamp  = _parse_timestamp(payload)

    if not message:
        metadata = payload.get("metadata", {})
        message = json.dumps(metadata, default=str) if metadata else f"{event_type} detected"

    async with AsyncSessionLocal() as session:
        try:
            event = Event(
                camera_id=camera_id,
                event_type=event_type,
                message=message,
                timestamp=timestamp,
            )
            session.add(event)
            await session.commit()
            logger.debug(
                "[AlertWorker] Event persisted — camera=%s type=%s",
                camera_id, event_type,
            )
        except Exception as exc:
            await session.rollback()
            logger.error(
                "[AlertWorker] DB write failed (event) — camera=%s: %s",
                camera_id, exc,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch: decide what to persist
# ─────────────────────────────────────────────────────────────────────────────

async def _process_payload(channel: str, raw: str) -> None:
    """
    Parse, validate, and persist a single Redis message.

    Routing rules:
      camera:*:alerts channel
        → payload is a single alert event (§9.2)
        → Any event with a recognised severity → Alert record
        → entry_event / exit_event / crossing_event  → also Event record

      camera:*:frames channel
        → payload is a frame result (§9.1) containing an events[] array
        → Iterate events[]; persist entry_event / exit_event as Event records
        → Severity events in frames are also persisted as Alert records
    """
    payload = _parse_payload(raw)
    if payload is None:
        return

    camera_id = _extract_camera_id(payload, channel)
    if camera_id is None:
        return

    # ── Alert channel: single event payload ────────────────────────────────────
    if channel.endswith(":alerts"):
        alert_type = payload.get("type", "")
        severity   = payload.get("severity", "")

        if severity in PERSIST_SEVERITIES:
            await _persist_alert(camera_id, payload)

        if alert_type in EVENT_TYPES:
            await _persist_event(camera_id, payload)

    # ── Frame channel: extract entry/exit events from events[] array ───────────
    elif channel.endswith(":frames"):
        events = payload.get("events", [])
        if not isinstance(events, list):
            return
        for event in events:
            if not isinstance(event, dict):
                continue
            ev_type  = event.get("type", "")
            severity = event.get("severity", "")
            # Persist entry/exit as Event rows
            if ev_type in EVENT_TYPES:
                await _persist_event(camera_id, event)
            # If the embedded event also carries a severity, persist as Alert
            if severity in PERSIST_SEVERITIES:
                await _persist_alert(camera_id, event)


# ─────────────────────────────────────────────────────────────────────────────
# Main coroutine
# ─────────────────────────────────────────────────────────────────────────────

async def run_alert_worker(
    redis_url: Optional[str] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """
    Entry-point coroutine for the alert persistence worker.

    Subscribes to ALL camera alert channels via Redis pattern subscription
    (PSUBSCRIBE camera:*:alerts), processes every incoming message, and
    writes it to PostgreSQL.

    Parameters
    ----------
    redis_url  : Redis connection URL; falls back to settings.REDIS_URL
    stop_event : set() to stop the loop gracefully
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    effective_url = redis_url or settings.REDIS_URL

    while not stop_event.is_set():
        conn: aioredis.Redis | None = None
        pubsub = None

        try:
            conn = await aioredis.from_url(
                effective_url,
                encoding="utf-8",
                decode_responses=True,
            )
            pubsub = conn.pubsub()
            await pubsub.psubscribe(ALERT_CHANNEL_PATTERN, FRAME_CHANNEL_PATTERN)
            logger.info(
                "[AlertWorker] Subscribed — patterns=%s,%s url=%s",
                ALERT_CHANNEL_PATTERN, FRAME_CHANNEL_PATTERN, effective_url,
            )

            async for message in pubsub.listen():
                if stop_event.is_set():
                    break

                if message["type"] not in ("pmessage", "message"):
                    continue

                channel: str = message.get("channel") or message.get("pattern", "")
                data: str    = message.get("data", "")

                if not data:
                    continue

                try:
                    await _process_payload(channel, data)
                except Exception as exc:
                    # Never let a single bad payload crash the loop
                    logger.exception(
                        "[AlertWorker] Unhandled error processing message: %s", exc
                    )

        except asyncio.CancelledError:
            logger.info("[AlertWorker] Cancelled.")
            break

        except Exception as exc:
            logger.exception("[AlertWorker] Connection error: %s", exc)
            if not stop_event.is_set():
                logger.info("[AlertWorker] Reconnecting in 5 s…")
                await asyncio.sleep(5)

        finally:
            if pubsub:
                try:
                    await pubsub.punsubscribe(ALERT_CHANNEL_PATTERN, FRAME_CHANNEL_PATTERN)
                    await pubsub.aclose()
                except Exception:
                    pass
            if conn:
                try:
                    await conn.aclose()
                except Exception:
                    pass

    logger.info("[AlertWorker] Stopped.")
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
