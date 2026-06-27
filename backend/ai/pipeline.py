"""
pipeline.py
-----------
Single orchestration point for the AI layer.

Counting line is set MANUALLY via set_counting_line()
after the operator draws it with line_selector.select_line().
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

from .detector.person_detector import Detection, PersonDetector
from .tracker.bytetrack_wrapper import ByteTrackWrapper, TrackedObject
from .tracker.track_manager import Track, TrackEvent, TrackManager
from .business_logic.entry_exit_counter import EntryExitCounter

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    annotated_frame: Optional[np.ndarray]
    detections: List[Detection]
    tracks: List[Track]
    events: List[TrackEvent]
    business_events: List[dict] = field(default_factory=list)
    frame_index: int = 0
    timestamp: float = field(default_factory=time.time)
    processing_time_ms: float = 0.0


class Pipeline:
    """
    Orchestrates detection → tracking → business logic → annotation.
    One instance per camera.

    Usage
    -----
    >>> from backend.ai.business_logic.line_selector import select_line, grab_preview_frame
    >>> cap = cv2.VideoCapture("video.mp4")
    >>> preview = grab_preview_frame(cap)
    >>> cap.release(); cap = cv2.VideoCapture("video.mp4")   # reopen after preview!
    >>> line_start, line_end = select_line(preview)
    >>> pipeline = Pipeline(model_path="models/yolov8n.pt")
    >>> counter = pipeline.set_counting_line(line_start, line_end)
    """

    def __init__(
        self,
        model_path: str | Path = "models/yolov8n.pt",
        confidence_threshold: float = 0.4,
        frame_rate: int = 30,
        max_frames_lost: int = 45,
        imgsz: int = 640,
    ) -> None:
        self._detector = PersonDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            imgsz=imgsz,
        )
        self._tracker = ByteTrackWrapper(
            frame_rate=frame_rate,
            track_buffer=max_frames_lost,
        )
        self._track_manager = TrackManager(max_frames_lost=max_frames_lost)
        self._analyzers: list = []
        self._counter: Optional[EntryExitCounter] = None
        self._frame_index: int = 0

        logger.info(
            "Pipeline initialised | model=%s | conf=%.2f | fps=%d",
            Path(model_path).name, confidence_threshold, frame_rate,
        )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray, annotate: bool = True) -> PipelineResult:
        t_start = time.perf_counter()
        self._frame_index += 1

        detections: List[Detection] = []
        tracked_objects: List[TrackedObject] = []
        track_events: List[TrackEvent] = []
        business_events: List[dict] = []
        annotated_frame: Optional[np.ndarray] = None

        # Stage 1 — Detection
        try:
            detections = self._detector.detect(frame)
        except Exception as exc:
            logger.error("[Frame %d] Detection failed: %s", self._frame_index, exc, exc_info=True)

        # Stage 2 — Tracking
        try:
            h, w = frame.shape[:2]
            tracked_objects = self._tracker.update(detections, frame_shape=(h, w))
        except Exception as exc:
            logger.error("[Frame %d] Tracking failed: %s", self._frame_index, exc, exc_info=True)

        # Stage 3 — Track manager
        try:
            track_events = self._track_manager.update(tracked_objects)
        except Exception as exc:
            logger.error("[Frame %d] TrackManager failed: %s", self._frame_index, exc, exc_info=True)

        active_tracks = self._track_manager.get_active_tracks()

        # Stage 4 — Business logic analyzers
        for analyzer in self._analyzers:
            try:
                events = analyzer.analyze(active_tracks, track_events)
                business_events.extend(events)
            except Exception as exc:
                logger.error(
                    "[Frame %d] Analyzer %s failed: %s",
                    self._frame_index, type(analyzer).__name__, exc, exc_info=True,
                )

        # Stage 5 — Annotation
        if annotate:
            try:
                annotated_frame = self._annotate(frame, active_tracks)
            except Exception as exc:
                logger.error("[Frame %d] Annotation failed: %s", self._frame_index, exc, exc_info=True)
                annotated_frame = frame.copy()

        processing_ms = (time.perf_counter() - t_start) * 1000.0

        return PipelineResult(
            annotated_frame=annotated_frame,
            detections=detections,
            tracks=active_tracks,
            events=track_events,
            business_events=business_events,
            frame_index=self._frame_index,
            timestamp=time.time(),
            processing_time_ms=processing_ms,
        )

    # ------------------------------------------------------------------
    # Counting line
    # ------------------------------------------------------------------

    def set_counting_line(
        self,
        line_start: tuple[int, int],
        line_end: tuple[int, int],
        in_direction: str = "auto",
        debounce_frames: int = 10,
    ) -> EntryExitCounter:
        """
        Set (or replace) the virtual counting line.

        Parameters
        ----------
        line_start, line_end:
            (x, y) endpoints — any angle supported.
        in_direction:
            "auto"  — detected from line angle automatically (recommended)
            "down"  — downward crossing = IN
            "up"    — upward crossing = IN
            "right" — rightward crossing = IN
            "left"  — leftward crossing = IN
        debounce_frames:
            Min frames between two counts for the same track.

        Returns
        -------
        EntryExitCounter
            Store reference to read count_in / count_out.
        """
        if in_direction == "auto":
            in_direction = _infer_direction(line_start, line_end)
            logger.info("Auto-inferred in_direction: %s", in_direction)

        # Remove any existing counter
        self._analyzers = [a for a in self._analyzers if not isinstance(a, EntryExitCounter)]

        counter = EntryExitCounter(
            line_start=line_start,
            line_end=line_end,
            in_direction=in_direction,
            debounce_frames=debounce_frames,
        )
        self._analyzers.insert(0, counter)
        self._counter = counter

        logger.info(
            "Counting line set | start=%s end=%s direction=%s",
            line_start, line_end, in_direction,
        )
        return counter

    def get_counter(self) -> Optional[EntryExitCounter]:
        """Return the active EntryExitCounter, or None if not set."""
        return self._counter

    # ------------------------------------------------------------------
    # Analyzers
    # ------------------------------------------------------------------

    def register_analyzer(self, analyzer) -> None:
        """Register a business-logic analyzer."""
        self._analyzers.append(analyzer)
        logger.info("Registered analyzer: %s", type(analyzer).__name__)

    def reset(self) -> None:
        """Reset tracker and track manager state."""
        self._tracker.reset()
        self._track_manager.reset()
        self._frame_index = 0
        logger.info("Pipeline state reset.")

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _annotate(self, frame: np.ndarray, tracks: List[Track]) -> np.ndarray:
        import cv2
        canvas = frame.copy()
        for track in tracks:
            x1, y1, x2, y2 = track.bbox
            color = self._id_to_color(track.track_id)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                canvas, f"ID:{track.track_id}  {track.confidence:.2f}",
                (x1, max(y1 - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA,
            )
        return canvas

    @staticmethod
    def _id_to_color(track_id: int) -> tuple[int, int, int]:
        palette = [
            (255, 56, 56),   (255, 157, 151), (255, 112, 31),  (255, 178, 29),
            (207, 210, 49),  (72, 249, 10),   (146, 204, 23),  (61, 219, 134),
            (26, 147, 52),   (0, 212, 187),   (44, 153, 168),  (0, 194, 255),
            (52, 69, 147),   (100, 115, 255), (0, 24, 236),    (132, 56, 255),
            (82, 0, 133),    (203, 56, 255),  (255, 149, 200), (255, 55, 199),
        ]
        return palette[track_id % len(palette)]


# ---------------------------------------------------------------------------
# Helper — infer IN direction from line angle
# ---------------------------------------------------------------------------

def _infer_direction(start: tuple[int, int], end: tuple[int, int]) -> str:
    """
    Infer the natural IN direction from the line angle.

    For a mostly-horizontal line → people crossing downward = IN.
    For a mostly-vertical line   → people crossing rightward = IN.
    For diagonal lines           → based on dominant axis.
    """
    import math
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = abs(math.degrees(math.atan2(dy, dx)))

    # Horizontal-ish line (angle < 45°)
    if angle < 45 or angle > 135:
        return "down"
    # Vertical-ish line
    else:
        return "right"


# ---------------------------------------------------------------------------
# Backwards-compatible alias
# ---------------------------------------------------------------------------
# The worker/celery modules historically import ``AIPipeline``; the canonical
# class is ``Pipeline``. Expose an alias so those imports resolve. (C1)
AIPipeline = Pipeline