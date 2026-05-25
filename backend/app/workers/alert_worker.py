"""
alert_worker.py
───────────────
Async consumer for the Smart Vision System that persists alerts to the database.

Responsibilities:
  - Subscribe to Redis alert channels (camera:*:alerts)
  - Parse JSON alert payloads
  - Create and save Alert objects to PostgreSQL
  - Run as a long-lived background service
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

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
                camera_id=camera_id,
                type=alert_type,
                severity=severity,
                message=message,
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
