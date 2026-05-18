# Project Structure

This document defines the full production folder structure of the **Smart Vision System**.

---

# Root Project Structure

```
smart-vision-system/
├── backend/
├── frontend/
├── infrastructure/
├── models/
└── docs/
```

---

# 1. Backend Structure

```
backend/
├── app/
├── ai/
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## 1.1 `backend/app/`

```
backend/app/
├── main.py
├── config.py
├── dependencies.py
├── api/
├── websocket/
├── workers/
├── models/
├── schemas/
├── db/
└── core/
```

### `main.py`
Main FastAPI application entry point.
- Create FastAPI app
- Register routers and WebSocket handlers
- Startup / shutdown lifecycle events

### `config.py`
Application configuration via environment variables.
- database URL, Redis URL, model paths, app settings

### `dependencies.py`
Dependency injection for DB sessions, Redis clients, shared services.

---

## 1.2 API Layer

```
api/
├── v1/
│   ├── cameras.py
│   ├── alerts.py
│   ├── analytics.py
│   ├── logs.py
│   └── health.py
└── router.py
```

- Camera CRUD, alert retrieval, analytics, logs, health checks

---

## 1.3 WebSocket Layer

```
websocket/
├── manager.py
├── handlers.py
└── serializers.py
```

- Client connection management, real-time frame broadcasting, event serialization

---

## 1.4 Workers Layer

```
workers/
├── camera_worker.py
├── inference_worker.py
├── alert_worker.py
└── celery_app.py
```

- Camera frame capture, AI inference execution, alert processing, Celery orchestration

---

## 1.5 Database Models

```
models/
├── camera.py
├── event.py
├── alert.py
└── zone.py
```

---

## 1.6 Schemas Layer

```
schemas/
├── camera.py
├── event.py
└── alert.py
```

---

## 1.7 Database Layer

```
db/
├── session.py
└── migrations/
```

- SQLAlchemy async engine, Alembic migrations

---

## 1.8 Core Utilities

```
core/
├── redis.py
├── storage.py
└── security.py
```

- Redis pub/sub, MinIO object storage, JWT auth (future)

---

# 2. AI Module Structure

```
backend/ai/
├── detector/
├── tracker/
├── business_logic/
├── pipeline.py
└── frame_annotator.py
```

---

## 2.1 Detector Layer

```
detector/
├── base.py
├── person_detector.py
├── weapon_detector.py
└── model_loader.py
```

- Load models, person/weapon detection, CPU/GPU selection

---

## 2.2 Tracker Layer

```
tracker/
├── bytetrack_wrapper.py
├── track_manager.py
└── reid_stub.py
```

- Track IDs, track lifecycle (ACTIVE/LOST/REMOVED), future Re-ID support

---

## 2.3 Business Logic Layer

```
business_logic/
├── entry_exit_counter.py
├── zone_monitor.py
├── behavior_analyzer.py
├── heatmap_generator.py
├── alert_engine.py
└── line_selector.py
```

| File | Responsibility |
|---|---|
| `entry_exit_counter.py` | Virtual line crossing detection — any angle (horizontal/diagonal/vertical) |
| `zone_monitor.py` | Polygon zone occupancy monitoring and threshold alerts |
| `behavior_analyzer.py` | Loitering detection per track |
| `heatmap_generator.py` | Density grid accumulation and PNG export |
| `alert_engine.py` | Central alert generation, severity rules, cooldown deduplication |
| `line_selector.py` | Interactive mouse-based counting line selector (operator tool) |

---

## 2.4 Pipeline

```
pipeline.py
```

Single orchestration point:
```
Frame → Detection → Tracking → Business Logic → Output Events
```

Key methods:
- `process_frame(frame)` → `PipelineResult`
- `set_counting_line(start, end)` → `EntryExitCounter`
- `register_analyzer(analyzer)`

---

## 2.5 Frame Annotator

```
frame_annotator.py
```

Draws: bounding boxes, track IDs, counters, zone polygons, entry line, loitering flags, FPS overlay.

---

# 3. Testing Structure

```
tests/
├── unit/
├── integration/
└── conftest.py
```

---

# 4. Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── monitor/
│   ├── alerts/
│   ├── analytics/
│   ├── logs/
│   └── cameras/
├── components/
│   ├── monitor/
│   ├── alerts/
│   ├── analytics/
│   ├── ui/
│   └── layout/
├── hooks/
│   ├── useWebSocket.ts
│   ├── useAlerts.ts
│   └── useCameraStream.ts
├── lib/
│   ├── api.ts
│   └── store.ts
├── types/
├── Dockerfile
├── next.config.ts
└── package.json
```

State management: Zustand (live state) + React Query (cached API data)

---

# 5. Infrastructure

```
infrastructure/
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
└── k8s/
```

---

# 6. Models Storage

```
models/
├── yolov8n.pt
├── yolov8_weapon_v1.pt
└── README.md
```

---

# 7. Documentation

```
docs/
├── architecture.md
├── api-reference.md
├── project_structure.md
└── deployment.md
```

---

# Phase Implementation Status

| Phase | Layer | Status |
|---|---|---|
| Phase 1 | AI Layer (detector, tracker, business_logic, pipeline) | ✅ Complete |
| Phase 2 | Backend App (FastAPI, DB, WebSocket, Workers, REST API) | 🔲 Next |
| Phase 3 | Frontend Dashboard (Next.js) | 🔲 Planned |
