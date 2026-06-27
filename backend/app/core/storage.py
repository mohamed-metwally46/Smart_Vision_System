"""
core/storage.py
───────────────
<<<<<<< HEAD
Local and cloud storage abstraction for the Smart Vision System.
Currently handles heatmap image persistence.
=======
Object storage interface for the Smart Vision System.

Future implementation — Phase 3 (production hardening sprint)
──────────────────────────────────────────────────────────────
This module will wrap the MinIO client to provide:

  - Heatmap image upload   → bucket: svs-media / heatmaps/
  - Snapshot upload        → bucket: svs-media / snapshots/
  - Pre-signed URL generation for frontend download links
  - Bucket initialisation on startup

Configuration (from config.py)
──────────────────────────────
  MINIO_ENDPOINT    e.g. "localhost:9000"
  MINIO_ACCESS_KEY
  MINIO_SECRET_KEY
  MINIO_BUCKET      default "svs-media"

Planned public API
──────────────────
  async upload_heatmap(camera_id, png_bytes) → str  (object key)
  async upload_snapshot(camera_id, jpg_bytes) → str
  async get_presigned_url(object_key, expires_seconds) → str
  async init_storage() → None   (called from lifespan startup)
  async close_storage() → None  (called from lifespan shutdown)

Usage (future — not yet active):
    from backend.app.core.storage import upload_heatmap
    key = await upload_heatmap(camera_id=1, png_bytes=heatmap_png)
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
"""

from __future__ import annotations

<<<<<<< HEAD
import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Canonical paths for media storage
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # project root
STATIC_DIR = BASE_DIR / "static"
HEATMAP_DIR = STATIC_DIR / "heatmaps"

# Ensure directories exist
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)


class StorageService:
    """
    Handles file I/O for AI-generated artifacts.
    """

    @staticmethod
    def save_heatmap(camera_id: int | str, heatmap: np.ndarray) -> str:
        """
        Save a heatmap BGR frame to the static directory.
        Returns the relative URL for the API.
        """
        filename = f"camera_{camera_id}_latest.png"
        filepath = HEATMAP_DIR / filename
        
        try:
            # Save using OpenCV
            cv2.imwrite(str(filepath), heatmap)
            logger.debug("[Storage] Saved heatmap: %s", filepath)
            return f"/static/heatmaps/{filename}"
        except Exception as exc:
            logger.error("[Storage] Failed to save heatmap for camera %s: %s", camera_id, exc)
            raise


storage_service = StorageService()
=======

class StorageNotImplementedError(NotImplementedError):
    """Raised when storage operations are called before Phase 3 implementation."""


class ObjectStorageClient:
    """
    Placeholder for the MinIO async client wrapper.

    Replace the method bodies below with actual miniopy-async or aiobotocore
    calls in Phase 3.
    """

    async def upload_heatmap(self, camera_id: int, png_bytes: bytes) -> str:
        raise StorageNotImplementedError("MinIO storage not yet implemented.")

    async def upload_snapshot(self, camera_id: int, jpg_bytes: bytes) -> str:
        raise StorageNotImplementedError("MinIO storage not yet implemented.")

    async def get_presigned_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        raise StorageNotImplementedError("MinIO storage not yet implemented.")

    async def init(self) -> None:
        """Initialise the MinIO client and ensure the bucket exists."""
        raise StorageNotImplementedError("MinIO storage not yet implemented.")

    async def close(self) -> None:
        """Close the MinIO client connection."""
        raise StorageNotImplementedError("MinIO storage not yet implemented.")


# Module-level singleton — swap implementation in Phase 3
storage_client = ObjectStorageClient()
>>>>>>> 039538419fb78c3d4ac4cc8e8c594d4d5793318f
