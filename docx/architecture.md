# Architecture Overview

This document describes the system architecture of the **Smart Vision System**.

---

# 1. System Architecture Layers

1. **Camera Input Layer**
2. **AI Processing Layer**
3. **Backend Service Layer**
4. **Frontend Dashboard Layer**
5. **Infrastructure Layer**

---

# 2. High-Level Data Flow

**Real-Time Streaming Flow:**
```
Camera Stream
    ↓
Frame Capture Worker (camera_worker.py)
    ↓
AI Pipeline (pipeline.py)
    ├── Detection (YOLOv8n)
    ├── Tracking (ByteTrack via supervision)
    ├── Business Logic (counter, zones, loitering, heatmap, alerts)
    └── Frame Annotation
    ↓
Redis Pub/Sub
    ↓
Backend WebSocket Manager
    ↓
Frontend Dashboard
```

**Persistent Analytics Flow:**
```
Business Logic Events
    ↓
AlertEngine → PostgreSQL
    ↓
REST APIs
    ↓
Frontend Analytics Pages
```

---

# 3. Camera Input Layer

Acquires frames from: USB cameras, RTSP streams, recorded video files.

**Operator Setup (Phase 1):**
Before processing starts, the operator uses `line_selector.py` to draw
the virtual counting line on a preview frame. The line is stored in the
Pipeline instance for the session.

```
grab_preview_frame(cap) → select_line(frame) → pipeline.set_counting_line(start, end)
```

Main component: `backend/app/workers/camera_worker.py`

---

# 4. AI Processing Layer

## 4.1 Detection Layer
- Phase 1: Person detection via YOLOv8n
- Phase 2: Weapon detection via fine-tuned YOLO

Input: Raw BGR frame → Output: `List[Detection]` (bbox + confidence)

Components:
- `backend/ai/detector/model_loader.py` — CUDA/CPU device selection, model caching
- `backend/ai/detector/person_detector.py` — YOLOv8 inference wrapper

## 4.2 Tracking Layer
ByteTrack via `supervision` library assigns stable IDs across frames.

Input: `List[Detection]` → Output: `List[TrackedObject]` (track_id + bbox)

Components:
- `backend/ai/tracker/bytetrack_wrapper.py` — supervision ByteTrack wrapper
- `backend/ai/tracker/track_manager.py` — ACTIVE/LOST/REMOVED state machine, velocity

## 4.3 Business Logic Layer
Converts tracked movement into business events.

| Module | Function |
|---|---|
| `entry_exit_counter.py` | Virtual line crossing (any angle) with signed-distance math |
| `zone_monitor.py` | Polygon zone occupancy via `cv2.pointPolygonTest` |
| `behavior_analyzer.py` | Loitering detection via centroid displacement |
| `heatmap_generator.py` | Float32 density grid + Gaussian blur PNG export |
| `alert_engine.py` | Severity rules, cooldown deduplication, structured AlertEvents |
| `line_selector.py` | Interactive mouse line selector (operator tool, any angle) |

## 4.4 Frame Annotation Layer
`backend/ai/frame_annotator.py` draws:
- Bounding boxes (colour per track ID)
- Track IDs + confidence
- Zone polygons with occupancy labels
- Entry/exit virtual line with counters
- Loitering red-border indicator
- FPS / processing time overlay

## 4.5 AI Pipeline Orchestrator
`backend/ai/pipeline.py` — single public entry point:

```python
result = pipeline.process_frame(frame)
# result.detections, result.tracks, result.business_events
```

Key methods:
- `set_counting_line(start, end, in_direction="auto")` — manual line setup
- `register_analyzer(analyzer)` — plug in any business logic module
- `get_counter()` — access entry/exit counts

---

# 5. AI Experimentation & Pipeline Management

For a graduation project, it is critical to have a robust and reproducible model development lifecycle. This layer manages the offline phases of the AI lifecycle: dataset preparation and model training.

## 5.1 Dataset Management

The system uses a dedicated manager to handle dataset acquisition and integrity.

### Responsibilities
- Securely download datasets from Roboflow using API keys.
- Validate dataset directory structures.
- Normalize `data.yaml` paths for cross-platform compatibility (Windows/Linux).
- Ensure class consistency across different training versions.

### Main Component
```bash id="ds_mgr"
dataset/dataset_manager.py
```

## 5.2 Training & Experimentation Pipeline

A structured pipeline is used to fine-tune YOLOv8 models for specialized tasks (e.g., weapon detection).

### Core Features
- **Argument-Driven Training**: Hyperparameters (LR, epochs, batch size) are controlled via CLI for easy experimentation.
- **Experiment Tracking**: Each training run is automatically versioned and logged.
- **Metadata Logging**: Saves `experiment_config.json` containing base models, hyperparameters, and results paths.
- **Early Stopping**: Integrated patience mechanisms to prevent overfitting and optimize compute resources.

### Main Component
```bash id="train_pipe"
models/train_pipeline.py
```

---

# 6. Backend Service Layer

## 5.1 REST API Layer
`backend/app/api/v1/` — historical data endpoints:
- cameras, alerts, analytics, logs, health

## 5.2 WebSocket Streaming Layer
`backend/app/websocket/` — real-time push to dashboard:
- annotated frames (base64 JPEG)
- live alert notifications

## 5.3 Event Logging Layer
PostgreSQL via SQLAlchemy async:
- entry/exit events, alerts, zone violations, occupancy snapshots

## 5.4 Redis Messaging Layer
Decouples AI workers from WebSocket delivery:
```
AI Worker → Redis Channel → WebSocket Manager → Dashboard
```

---

# 6. Frontend Dashboard Layer (Next.js)

| Page | Content |
|---|---|
| `/monitor` | Live camera feeds, track IDs, overlays, counters |
| `/alerts` | Active alerts, history, severity indicators |
| `/analytics` | Occupancy charts, heatmaps, entry/exit reports |
| `/logs` | Historical event logs |
| `/cameras` | Camera management CRUD |

State: Zustand (live) + React Query (cached API)

---

# 7. Infrastructure Layer

- **PostgreSQL** — persistent storage
- **Redis** — messaging bus
- **FastAPI** — backend API + WebSocket
- **Next.js** — frontend
- **Docker Compose** — local orchestration
- **Kubernetes** — production deployment

---

# 8. Real-Time Processing Sequence

```
1. Operator draws counting line via line_selector (once at startup)
2. CameraWorker opens video / RTSP stream
3. Frame read → pipeline.process_frame()
4. YOLOv8n detects persons → List[Detection]
5. ByteTrack assigns stable IDs → List[TrackedObject]
6. TrackManager updates ACTIVE/LOST/REMOVED states → List[TrackEvent]
7. EntryExitCounter checks line crossings
8. ZoneMonitor checks polygon occupancy
9. BehaviorAnalyzer checks loitering
10. HeatmapGenerator accumulates density
11. AlertEngine generates structured AlertEvents
12. FrameAnnotator draws overlays
13. Result published to Redis
14. WebSocket Manager broadcasts to dashboard
15. Events stored in PostgreSQL
```

---

# 9. Scalability Model

| Level | Description | Suitable For |
|---|---|---|
| 1 — Single Machine | All services together | Dev / small deployments |
| 2 — Worker Separation | AI workers separate from API | Multiple cameras, GPU nodes |
| 3 — Cloud | All services independent | Production, horizontal scaling |

---

# 10. Design Principles

- **Separation of Concerns** — AI / backend / frontend each have one responsibility
- **Decoupling** — Redis separates AI workers from WebSocket delivery
- **Modularity** — each analyzer plugs into Pipeline independently
- **Defensive Processing** — all pipeline stages catch exceptions; one bad frame never crashes the loop
- **Scalability** — workers scale independently from API and frontend

---

# 11. Phase Status

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Full AI layer — detection, tracking, business logic, annotation | ✅ Complete |
| Phase 2 | Backend — FastAPI, PostgreSQL, Redis, WebSocket, REST API, Workers | 🔲 Next |
| Phase 3 | Frontend — Next.js dashboard | 🔲 Planned |
