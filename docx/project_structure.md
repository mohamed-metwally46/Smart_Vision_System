# Project Structure

This document defines the full production folder structure of the **Smart Vision System**, including backend services, AI modules, frontend dashboard, infrastructure, model storage, and project documentation.

The architecture is designed to support:

* Real-time AI video processing
* Multi-camera scalability
* Event logging and analytics
* Live dashboard streaming
* Modular maintainability
* Future production deployment

---

# Root Project Structure

```bash id="7j2kq1"
smart-vision-system/
├── backend/
├── frontend/
├── infrastructure/
├── models/
└── docs/
```

---

# 1. Backend Structure

The backend is built using **FastAPI** and contains:

* API routes
* WebSocket handlers
* Background workers
* Database models
* AI pipeline modules

```bash id="3fxe8s"
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

This directory contains all backend application services.

```bash id="y2tbko"
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

---

### `main.py`

Main FastAPI application entry point.

Responsibilities:

* Create FastAPI app
* Register routers
* Register WebSocket handlers
* Startup / shutdown lifecycle events

---

### `config.py`

Application configuration using environment variables.

Stores:

* database URL
* Redis URL
* model paths
* app settings

---

### `dependencies.py`

Dependency injection layer for:

* DB sessions
* Redis clients
* shared services

---

## 1.2 API Layer

REST API route handlers.

```bash id="sdc7ko"
api/
├── v1/
│   ├── cameras.py
│   ├── alerts.py
│   ├── analytics.py
│   ├── logs.py
│   └── health.py
└── router.py
```

### Responsibilities:

* Camera CRUD operations
* Alert retrieval
* Analytics endpoints
* Logs queries
* Health checks

---

## 1.3 WebSocket Layer

Handles real-time streaming to dashboard clients.

```bash id="5z91ef"
websocket/
├── manager.py
├── handlers.py
└── serializers.py
```

### Responsibilities:

* Client connection management
* Real-time frame broadcasting
* Event serialization

---

## 1.4 Workers Layer

Background workers for continuous processing.

```bash id="6y7vcm"
workers/
├── camera_worker.py
├── inference_worker.py
├── alert_worker.py
└── celery_app.py
```

### Responsibilities:

* Camera frame capture
* AI inference execution
* Alert processing
* Celery task orchestration

---

## 1.5 Database Models

ORM models for PostgreSQL.

```bash id="ywuvfq"
models/
├── camera.py
├── event.py
├── alert.py
└── zone.py
```

Represents:

* Cameras
* Events
* Alerts
* Zone configurations

---

## 1.6 Schemas Layer

Pydantic schemas for API request/response validation.

```bash id="zh91g0"
schemas/
├── camera.py
├── event.py
└── alert.py
```

---

## 1.7 Database Layer

Database engine and migrations.

```bash id="u7tq9j"
db/
├── session.py
└── migrations/
```

Responsibilities:

* SQLAlchemy async engine
* Alembic migrations

---

## 1.8 Core Utilities

Shared infrastructure services.

```bash id="z2rme7"
core/
├── redis.py
├── storage.py
└── security.py
```

Responsibilities:

* Redis pub/sub
* MinIO object storage
* JWT auth (future)

---

# 2. AI Module Structure

This directory contains the AI pipeline logic independent of FastAPI.

```bash id="xuvn2p"
backend/ai/
├── detector/
├── tracker/
├── business_logic/
├── pipeline.py
└── frame_annotator.py
```

---

## 2.1 Detector Layer

Responsible for AI object detection.

```bash id="44bnsn"
detector/
├── base.py
├── person_detector.py
├── weapon_detector.py
└── model_loader.py
```

Responsibilities:

* Load models
* Run person detection
* Run weapon detection
* Device selection (CPU/GPU)

---

## 2.2 Tracker Layer

Responsible for maintaining identities.

```bash id="k3m7tw"
tracker/
├── bytetrack_wrapper.py
├── track_manager.py
└── reid_stub.py
```

Responsibilities:

* Track IDs
* Track lifecycle
* Future Re-ID support

---

## 2.3 Business Logic Layer

Transforms tracks into business events.

```bash id="j0g2wv"
business_logic/
├── entry_exit_counter.py
├── zone_monitor.py
├── behavior_analyzer.py
├── heatmap_generator.py
└── alert_engine.py
```

Responsibilities:

* Entry/exit counting
* Zone occupancy monitoring
* Loitering detection
* Heatmap generation
* Alert triggering

---

## 2.4 Pipeline

```bash id="o91n0y"
pipeline.py
```

Main AI orchestrator:

```bash id="pwzlhg"
Frame → Detection → Tracking → Business Logic → Output Events
```

---

## 2.5 Frame Annotator

```bash id="v6xw9k"
frame_annotator.py
```

Draws:

* bounding boxes
* IDs
* counters
* zones
* alerts

---

# 3. Testing Structure

Contains automated tests.

```bash id="ehl5u6"
tests/
├── unit/
├── integration/
└── conftest.py
```

---

# 4. Frontend Structure

Frontend dashboard built with **Next.js**.

```bash id="7cfz0l"
frontend/
├── app/
├── components/
├── hooks/
├── lib/
├── types/
├── Dockerfile
├── next.config.ts
└── package.json
```

---

## 4.1 App Router Pages

Main dashboard routes.

```bash id="e7b5yu"
app/
├── layout.tsx
├── page.tsx
├── monitor/
├── alerts/
├── analytics/
├── logs/
└── cameras/
```

Provides:

* live monitor
* alerts
* analytics
* logs
* camera management

---

## 4.2 Components

Reusable UI components.

```bash id="e1lkp2"
components/
├── monitor/
├── alerts/
├── analytics/
├── ui/
└── layout/
```

Responsibilities:

* camera feed rendering
* alerts display
* analytics charts
* layout components

---

## 4.3 Hooks

Reusable frontend hooks.

```bash id="lwdg2s"
hooks/
├── useWebSocket.ts
├── useAlerts.ts
└── useCameraStream.ts
```

Handles:

* WebSocket connections
* live alerts
* camera stream state

---

## 4.4 Frontend Utilities

```bash id="xn0ncf"
lib/
├── api.ts
└── store.ts
```

Responsibilities:

* API client
* global state management

---

# 5. Infrastructure

Deployment configuration.

```bash id="u9iqhi"
infrastructure/
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
└── k8s/
```

Includes:

* local development stack
* production overrides
* reverse proxy
* Kubernetes manifests

---

# 6. Models Storage

Stores trained weights.

```bash id="i6m7ho"
models/
├── yolov8n.pt
├── yolov8_weapon_v1.pt
└── README.md
```

---

# 7. Documentation

Project documentation.

```bash id="0m14rb"
docs/
├── architecture.md
├── api-reference.md
└── deployment.md
```

Contains:

* architecture decisions
* API documentation
* deployment instructions

---

# Architecture Summary

The project is divided into five independent layers:

1. **AI Layer**
2. **Backend Layer**
3. **Frontend Layer**
4. **Infrastructure Layer**
5. **Documentation Layer**

This modular structure ensures:

* scalability
* maintainability
* testability
* production readiness
