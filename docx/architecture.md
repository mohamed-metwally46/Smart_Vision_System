# Architecture Overview

This document describes the high-level system architecture of the **Smart Vision System**, including all major layers, data flow between components, and the responsibilities of each service.

The architecture is designed to provide:

* Real-time AI video analytics
* Live event streaming
* Modular service separation
* Scalable multi-camera support
* Future cloud deployment readiness

---

# 1. System Architecture Layers

The system is divided into five major layers:

1. **Camera Input Layer**
2. **AI Processing Layer**
3. **Backend Service Layer**
4. **Frontend Dashboard Layer**
5. **Infrastructure Layer**

These layers work together to transform live camera streams into actionable analytics and alerts.

---

# 2. High-Level Data Flow

The main real-time processing flow is:

```bash id="g4n7hu"
Camera Stream
    ↓
Frame Capture Worker
    ↓
AI Detection Layer
    ↓
Tracking Layer
    ↓
Business Logic Layer
    ↓
Redis Pub/Sub
    ↓
Backend WebSocket Manager
    ↓
Frontend Dashboard
```

At the same time, events are stored in the database:

```bash id="1cz6x5"
Business Logic Events
        ↓
PostgreSQL Database
        ↓
REST APIs
        ↓
Frontend Analytics Pages
```

This creates two simultaneous flows:

1. **Real-Time Streaming Flow**
2. **Persistent Analytics Flow**

---

# 3. Camera Input Layer

The Camera Input Layer is responsible for acquiring frames from:

* USB cameras
* RTSP streams
* Recorded video files

Each camera source is handled by a dedicated worker process.

## Responsibilities

* Open video stream
* Read frames continuously
* Handle reconnection on failure
* Send frames to the AI pipeline

## Main Component

```bash id="p9s6wf"
backend/app/workers/camera_worker.py
```

This worker isolates each camera so that one failing stream does not interrupt the others.

---

# 4. AI Processing Layer

The AI Processing Layer transforms raw frames into structured detections and business events.

It consists of four sublayers:

1. Detection
2. Tracking
3. Business Logic
4. Frame Annotation

---

## 4.1 Detection Layer

This layer detects objects of interest from each frame.

### Phase 1

* Person detection using YOLOv8n

### Phase 2

* Weapon detection using a fine-tuned YOLO model

## Input

```bash id="1wqkho"
Raw Frame
```

## Output

```bash id="3shl1d"
Bounding Boxes + Confidence Scores
```

## Main Components

```bash id="3npx7y"
backend/ai/detector/model_loader.py
backend/ai/detector/person_detector.py
```

---

## 4.2 Tracking Layer

This layer assigns persistent IDs to detected persons using ByteTrack.

## Responsibilities

* Maintain object identity across frames
* Track movement
* Handle lost and recovered tracks

## Input

```bash id="6zc2kr"
Detections
```

## Output

```bash id="ikz67g"
Tracked Objects with IDs
```

## Main Components

```bash id="jjw1iy"
backend/ai/tracker/bytetrack_wrapper.py
backend/ai/tracker/track_manager.py
```

---

## 4.3 Business Logic Layer

This layer converts tracked movement into business events.

## Core Features

* Entry/Exit counting
* Zone occupancy monitoring
* Loitering detection
* Heatmap accumulation
* Alert generation

## Example Events

* Person entered
* Zone overcrowded
* Suspicious loitering detected

## Main Components

```bash id="kr7vzt"
backend/ai/business_logic/
```

---

## 4.4 Frame Annotation Layer

This layer overlays analytics data on frames.

## Draws

* Bounding boxes
* Track IDs
* Counters
* Zones
* Alerts

## Main Component

```bash id="1msm3u"
backend/ai/frame_annotator.py
```

---

## 4.5 AI Pipeline Orchestrator

This is the main integration point of the AI layer.

## Pipeline Flow

```bash id="qnt1f9"
Frame
 → Detection
 → Tracking
 → Business Logic
 → Annotation
```

## Main Component

```bash id="uq0wtk"
backend/ai/pipeline.py
```

This ensures all AI components remain modular while producing a unified output.

---

# 5. Backend Service Layer

The Backend Layer coordinates:

* AI workers
* API access
* WebSocket streaming
* event storage

It is implemented using **FastAPI**.

---

## 5.1 REST API Layer

Provides endpoints for:

* camera management
* alert history
* analytics
* logs

## Main Router Path

```bash id="jlwmgn"
backend/app/api/v1/
```

These APIs provide historical analytics data to the frontend dashboard.

---

## 5.2 WebSocket Streaming Layer

The WebSocket layer streams live frames and alerts to the frontend.

## Responsibilities

* manage dashboard connections
* broadcast annotated frames
* push live alerts

## Main Components

```bash id="cxxt6z"
backend/app/websocket/manager.py
backend/app/websocket/handlers.py
```

This enables real-time updates without page refresh.

---

## 5.3 Event Logging Layer

Business events are stored in PostgreSQL.

## Logged Events

* entry/exit events
* alerts
* zone violations
* occupancy snapshots

## Main Components

```bash id="3z6m91"
backend/app/models/
backend/app/db/
```

This supports historical analysis and reporting.

---

## 5.4 Redis Messaging Layer

Redis acts as an internal messaging bus.

## Responsibilities

* publish AI results
* deliver frames to WebSocket manager
* decouple workers from APIs

## Flow

```bash id="xllng4"
AI Worker → Redis Channel → WebSocket Manager
```

This architecture prevents the AI pipeline from depending directly on WebSocket clients.

---

# 6. Frontend Dashboard Layer

The frontend is built using **Next.js** and provides the monitoring interface.

---

## 6.1 Live Monitoring

Displays:

* live camera feeds
* track IDs
* overlays
* live counters

## Main Components

```bash id="bpl3ye"
frontend/components/monitor/
```

---

## 6.2 Alerts Dashboard

Displays:

* active alerts
* alert history
* severity indicators

## Main Path

```bash id="bgdnhu"
frontend/app/alerts/
```

---

## 6.3 Analytics Dashboard

Displays:

* occupancy charts
* heatmaps
* entry/exit reports

## Main Path

```bash id="mp4d2n"
frontend/app/analytics/
```

---

## 6.4 Frontend State Management

The frontend manages state using:

* Zustand for live state
* React Query for cached API data

## Main Components

```bash id="d64p48"
frontend/lib/store.ts
frontend/lib/api.ts
```

---

# 7. Infrastructure Layer

The infrastructure layer supports deployment and service orchestration.

---

## Services

* PostgreSQL
* Redis
* Backend API
* Frontend Dashboard

## Local Deployment

```bash id="h3lggp"
docker-compose.yml
```

## Production Deployment

```bash id="xdpmja"
docker-compose.prod.yml
```

---

# 8. Real-Time Processing Sequence

The sequence below describes what happens when a new frame arrives:

```bash id="8a5qzx"
1. CameraWorker reads a frame
2. Frame sent to AI pipeline
3. Detector finds persons
4. Tracker assigns IDs
5. Business logic generates events
6. Frame annotated
7. Result published to Redis
8. WebSocket manager broadcasts to dashboard
9. Events stored in PostgreSQL
```

This sequence repeats continuously for every active camera.

---

# 9. Scalability Model

The architecture supports scaling at three levels:

---

## Level 1 — Single Machine

All services run together:

* backend
* Redis
* PostgreSQL
* frontend

Suitable for:

* local development
* small deployments

---

## Level 2 — Worker Separation

Separate AI workers from API services.

Suitable for:

* multiple cameras
* dedicated GPU worker nodes

---

## Level 3 — Cloud Deployment

Deploy services independently:

* AI workers
* backend API
* Redis
* PostgreSQL
* frontend

Suitable for:

* production environments
* horizontal scaling

---

# 10. Design Principles

The architecture follows these principles:

---

## Separation of Concerns

Each layer has a single responsibility:

* AI handles inference
* backend handles delivery
* frontend handles visualization

---

## Decoupling

Redis separates:

* AI workers
* WebSocket delivery
* API services

This reduces service dependency and improves resilience.

---

## Scalability

Workers can be scaled independently from frontend or backend.

---

## Maintainability

Each module is isolated and testable.

---

## Extensibility

Future features can be added without changing the core flow, such as:

* weapon detection
* Re-ID
* authentication
* advanced analytics

---

# 11. Architecture Summary

The Smart Vision System architecture transforms raw video streams into:

* live analytics
* business insights
* security alerts

through a modular layered pipeline:

```bash id="5r5rvu"
Camera → AI Pipeline → Redis → Backend → Frontend
```

This design ensures:

* real-time responsiveness
* modularity
* scalability
* production readiness
