"""
core/storage.py
───────────────
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
"""

from __future__ import annotations


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
