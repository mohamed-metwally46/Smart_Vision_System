"""
bytetrack_wrapper.py
--------------------
Wraps the ByteTrack multi-object tracker.

Design constraints (from handoff):
  - Input  : List[Detection]  (from person_detector)
  - Output : List[TrackedObject]  (track_id + bbox per active track)
  - No business logic — identity assignment only
  - No FastAPI imports

Install dependency:
    pip install lapx byte-tracker
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from ..detector.person_detector import Detection

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """
    A single tracked person returned by ByteTrack for one frame.

    Attributes
    ----------
    track_id:
        Unique integer ID assigned by ByteTrack; stable across frames.
    bbox:
        Bounding box ``(x1, y1, x2, y2)`` in pixel coordinates.
    confidence:
        Detection confidence at the time of last association.
    is_confirmed:
        True once the track has been confirmed over multiple frames.
    """

    track_id: int
    bbox: tuple[int, int, int, int]
    confidence: float
    is_confirmed: bool = True


class _ByteTrackArgs:
    """
    Minimal argument object expected by BYTETracker.
    Mirrors the argparse namespace used in the original ByteTrack repo.
    """

    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 60,
        match_thresh: float = 0.8,
        frame_rate: int = 30,
    ) -> None:
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.mot20 = False
        self.frame_rate = frame_rate


class ByteTrackWrapper:
    """
    Stateful wrapper around BYTETracker.

    One instance per camera — do not share across cameras because
    ByteTrack's internal Kalman filters hold per-camera state.

    Usage
    -----
    >>> tracker = ByteTrackWrapper(frame_rate=25)
    >>> tracked = tracker.update(detections, frame_shape=(720, 1280))
    """

    def __init__(
        self,
        frame_rate: int = 30,
        track_thresh: float = 0.5,
        track_buffer: int = 60,
        match_thresh: float = 0.8,
    ) -> None:
        """
        Parameters
        ----------
        frame_rate:
            Expected frames-per-second of the input stream.
            Used to tune the Kalman filter motion model.
        track_thresh:
            Minimum detection score for high-confidence track association.
        track_buffer:
            Frames to keep a lost track alive before removing it.
            Set to 60 (2 s @ 30 fps) per handoff risk-mitigation note.
        match_thresh:
            IoU threshold for track-detection matching.
        """
        try:
            from byte_tracker import BYTETracker  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "ByteTrack is not installed. Run:  pip install lapx byte-tracker"
            ) from exc

        args = _ByteTrackArgs(
            track_thresh=track_thresh,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            frame_rate=frame_rate,
        )
        self._tracker = BYTETracker(args, frame_rate=frame_rate)
        logger.info(
            "ByteTrackWrapper initialised | frame_rate=%d | track_buffer=%d",
            frame_rate,
            track_buffer,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        detections: List[Detection],
        frame_shape: tuple[int, int],
    ) -> List[TrackedObject]:
        """
        Associate *detections* with existing tracks and return active tracks.

        Parameters
        ----------
        detections:
            Output of ``PersonDetector.detect()`` for the current frame.
        frame_shape:
            ``(height, width)`` of the source frame — used by ByteTrack
            to clip predicted boxes to valid image bounds.

        Returns
        -------
        List[TrackedObject]
            All currently active (confirmed + tentative) tracks.
        """
        if not detections:
            # Advance tracker with empty detections so Kalman filters update
            try:
                self._tracker.update(
                    np.empty((0, 5), dtype=np.float32),
                    frame_shape,
                    frame_shape,
                )
            except Exception:
                pass
            return []

        det_array = self._detections_to_array(detections)

        try:
            stracks = self._tracker.update(
                det_array,
                frame_shape,
                frame_shape,
            )
        except Exception as exc:
            logger.error("ByteTrack update failed: %s", exc, exc_info=True)
            return []

        return self._stracks_to_tracked_objects(stracks)

    def reset(self) -> None:
        """Reset tracker state (call between disconnected video segments)."""
        self._tracker.reset()
        logger.debug("ByteTrackWrapper state reset.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detections_to_array(detections: List[Detection]) -> np.ndarray:
        """
        Convert Detection list → NumPy array shaped ``(N, 5)``.
        Columns: ``[x1, y1, x2, y2, confidence]``
        """
        rows = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            rows.append([x1, y1, x2, y2, det.confidence])
        return np.array(rows, dtype=np.float32)

    @staticmethod
    def _stracks_to_tracked_objects(stracks) -> List[TrackedObject]:
        """Convert STrack objects → TrackedObject dataclasses."""
        result: List[TrackedObject] = []
        for strack in stracks:
            tlbr = strack.tlbr  # top-left bottom-right
            x1, y1, x2, y2 = int(tlbr[0]), int(tlbr[1]), int(tlbr[2]), int(tlbr[3])
            result.append(
                TrackedObject(
                    track_id=int(strack.track_id),
                    bbox=(x1, y1, x2, y2),
                    confidence=float(strack.score),
                    is_confirmed=strack.is_activated,
                )
            )
        return result
