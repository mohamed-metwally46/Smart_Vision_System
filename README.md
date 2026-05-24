Smart Vision System for Small Businesses
An integrated AI-powered real-time video monitoring and analysis platform designed for small businesses such as retail stores, shopping malls, and warehouses. The system transforms raw surveillance camera streams into intelligent, actionable data — including visitor counting, movement behavior analysis, security alerts, and occupancy analytics — all through a unified dashboard.

Table of Contents
Overview
Key Features
System Architecture
Technology Stack
Project Structure
Getting Started
API Reference
Frontend Dashboard
Development Phases
Use Cases
Design Principles
Overview
Traditional surveillance systems in small businesses are limited to passive recording, lacking the ability to analyze customer movement, count visitors accurately, detect suspicious behavior in real time, or generate actionable business insights. Smart Vision System addresses these gaps by combining computer vision and AI to turn existing cameras into an intelligent monitoring platform.

The system processes live video feeds through a multi-stage AI pipeline — detection, tracking, and business logic analysis — and delivers real-time results to a web-based dashboard alongside historical analytics and event logging.

What It Provides
Capability	Description
Person Detection	Real-time detection using YOLOv8 with bounding boxes and confidence scores
Multi-Object Tracking	Persistent ID assignment via ByteTrack for reliable movement analysis
Entry/Exit Counting	Automatic counting at virtual lines placed at entrances and exits
Zone Monitoring	Polygon-based occupancy tracking with configurable thresholds
Behavior Analysis	Loitering detection via centroid displacement tracking
Heatmap Generation	Density grid accumulation with Gaussian blur visualization
Weapon Detection	Dedicated fine-tuned YOLO model for guns and knives
Smart Alerts	Severity-based alert system with cooldown deduplication
Event Logging	Full event history with timestamps, camera IDs, and event types
Key Features
Real-Time Monitoring
Live video streams with detection bounding boxes, tracking IDs, and threat highlighting overlaid directly on the feed
Simultaneous multi-camera display support
FPS and processing time overlay for performance monitoring
Analytics Dashboard
Entry/exit traffic statistics over time
Current occupancy counts and zone-level activity breakdown
Heatmap visualization showing the most frequently visited areas
Historical trend analysis for business intelligence
Smart Alert System
The system generates categorized alerts for critical events:

Alert Type	Severity	Trigger
zone_overcrowding	High	Zone occupancy exceeds defined threshold
loitering	Medium	Individual remains stationary beyond time limit
crossing_event	Low	Person crosses a virtual entry/exit line
zone_occupancy	Low	Informational zone occupancy snapshot
weapon_detected	Critical	Gun or knife detected in frame
Operator Tools
Interactive mouse-based line selector for defining virtual counting lines at any angle
Configurable polygon zones for monitoring specific areas (entrance, cashier, restricted areas)
System Architecture
The system follows a layered architecture with clear separation of concerns:

┌─────────────────────────────────────────────────────────────────┐
│ Frontend Dashboard (Next.js) │
│ /monitor | /alerts | /analytics | /logs | /cameras │
└──────────────────────────┬──────────────────────────────────────┘
│ WebSocket + REST API
┌──────────────────────────┴──────────────────────────────────────┐
│ Backend Service Layer (FastAPI) │
│ REST API | WebSocket Manager | Workers | Event Logging │
└──────┬──────────────────┬───────────────────────────────────────┘
│ Redis Pub/Sub │ PostgreSQL
┌──────┴──────────────────┴───────────────────────────────────────┐
│ AI Processing Layer │
│ Detection (YOLOv8) │ Tracking (ByteTrack) │ Business Logic │
└──────────────────────────┬──────────────────────────────────────┘
│ Frame Capture
┌──────────────────────────┴──────────────────────────────────────┐
│ Camera Input Layer │
│ USB Cameras | RTSP Streams | Video Files │
└─────────────────────────────────────────────────────────────────┘

text


### Data Flow

**Real-Time Streaming:**
Camera Stream → Frame Capture → AI Pipeline → Redis Pub/Sub → WebSocket → Dashboard
│
┌─────────┼──────────┐
│ │ │
Detection Tracking Business Logic
│ │ │
└─────────┼──────────┘
│
AlertEngine → PostgreSQL

text


**Processing Sequence (per frame):**
1. Operator draws counting line via `line_selector` (once at startup)
2. `CameraWorker` opens video/RTSP stream
3. Frame read → `pipeline.process_frame()`
4. YOLOv8n detects persons → `List[Detection]`
5. ByteTrack assigns stable IDs → `List[TrackedObject]`
6. `TrackManager` updates ACTIVE/LOST/REMOVED states → `List[TrackEvent]`
7. `EntryExitCounter` checks line crossings
8. `ZoneMonitor` checks polygon occupancy
9. `BehaviorAnalyzer` checks loitering
10. `HeatmapGenerator` accumulates density
11. `AlertEngine` generates structured `AlertEvents`
12. `FrameAnnotator` draws overlays
13. Result published to Redis
14. WebSocket Manager broadcasts to dashboard
15. Events stored in PostgreSQL

---

## Technology Stack

### AI & Computer Vision
| Technology | Purpose |
|---|---|
| **YOLOv8n** | Real-time person detection |
| **YOLOv8 (fine-tuned)** | Weapon detection (guns, knives) |
| **ByteTrack** | Multi-object tracking with persistent IDs |
| **OpenCV** | Frame processing, polygon testing, annotation |
| **supervision** | ByteTrack wrapper and detection utilities |

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework and WebSocket server |
| **PostgreSQL** | Persistent storage for events, alerts, cameras |
| **Redis** | Message bus decoupling AI workers from WebSocket delivery |
| **SQLAlchemy (async)** | ORM with Alembic migrations |
| **Celery** | Distributed task queue for worker orchestration |
| **MinIO** | Object storage for heatmap images |

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js** | React framework for the dashboard UI |
| **Zustand** | Lightweight state management for live data |
| **React Query** | Cached API data fetching |
| **WebSocket API** | Real-time frame and alert streaming |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker Compose** | Local development orchestration |
| **Docker Compose (prod)** | Production configuration |
| **Kubernetes** | Production deployment and scaling |
| **Nginx** | Reverse proxy and load balancing |

---

## Project Structure

smart-vision-system/
├── backend/
│ ├── app/ # FastAPI application
│ │ ├── main.py # Application entry point
│ │ ├── config.py # Environment configuration
│ │ ├── dependencies.py # Dependency injection
│ │ ├── api/v1/ # REST API endpoints
│ │ │ ├── cameras.py # Camera CRUD
│ │ │ ├── alerts.py # Alert retrieval
│ │ │ ├── analytics.py # Analytics endpoints
│ │ │ ├── logs.py # Event logs
│ │ │ └── health.py # Health checks
│ │ ├── websocket/ # WebSocket layer
│ │ │ ├── manager.py # Connection management
│ │ │ ├── handlers.py # Frame broadcasting
│ │ │ └── serializers.py # Event serialization
│ │ ├── workers/ # Background workers
│ │ │ ├── camera_worker.py # Frame capture
│ │ │ ├── inference_worker.py # AI inference
│ │ │ ├── alert_worker.py # Alert processing
│ │ │ └── celery_app.py # Celery configuration
│ │ ├── models/ # SQLAlchemy models
│ │ ├── schemas/ # Pydantic schemas
│ │ ├── db/ # Database session & migrations
│ │ └── core/ # Redis, storage, security utils
│ ├── ai/ # AI processing module
│ │ ├── detector/ # YOLO detection layer
│ │ │ ├── model_loader.py # CUDA/CPU model loading
│ │ │ ├── person_detector.py # Person detection
│ │ │ └── weapon_detector.py # Weapon detection
│ │ ├── tracker/ # Object tracking layer
│ │ │ ├── bytetrack_wrapper.py # ByteTrack integration
│ │ │ ├── track_manager.py # Track state machine
│ │ │ └── reid_stub.py # Future Re-ID support
│ │ ├── business_logic/ # Business logic analyzers
│ │ │ ├── entry_exit_counter.py # Virtual line crossing
│ │ │ ├── zone_monitor.py # Polygon zone occupancy
│ │ │ ├── behavior_analyzer.py # Loitering detection
│ │ │ ├── heatmap_generator.py # Density heatmap
│ │ │ ├── alert_engine.py # Central alert generation
│ │ │ └── line_selector.py # Interactive line tool
│ │ ├── pipeline.py # AI pipeline orchestrator
│ │ └── frame_annotator.py # Visual frame annotation
│ ├── tests/ # Unit & integration tests
│ ├── Dockerfile
│ ├── requirements.txt
│ └── pyproject.toml
├── frontend/
│ ├── app/
│ │ ├── monitor/ # Live camera monitoring page
│ │ ├── alerts/ # Alerts panel page
│ │ ├── analytics/ # Analytics dashboard page
│ │ ├── logs/ # Event logs viewer page
│ │ └── cameras/ # Camera management page
│ ├── components/ # Reusable UI components
│ │ ├── monitor/ # Monitor-specific components
│ │ ├── alerts/ # Alert display components
│ │ ├── analytics/ # Chart and data components
│ │ ├── ui/ # Shared UI primitives
│ │ └── layout/ # Layout components
│ ├── hooks/ # Custom React hooks
│ │ ├── useWebSocket.ts # WebSocket connection hook
│ │ ├── useAlerts.ts # Alert data hook
│ │ └── useCameraStream.ts # Camera stream hook
│ ├── lib/ # Utilities
│ │ ├── api.ts # API client
│ │ └── store.ts # Zustand stores
│ ├── types/ # TypeScript type definitions
│ ├── Dockerfile
│ └── package.json
├── infrastructure/
│ ├── docker-compose.yml # Local development
│ ├── docker-compose.prod.yml # Production setup
│ ├── nginx/ # Nginx configuration
│ └── k8s/ # Kubernetes manifests
├── models/ # Pre-trained model weights
│ ├── yolov8n.pt # Person detection model
│ └── yolov8_weapon_v1.pt # Weapon detection model
└── docs/ # Project documentation
├── architecture.md
├── api-reference.md
├── project_structure.md
└── deployment.md

text


---

## Getting Started

### Prerequisites

- **Python 3.10+** with CUDA support (recommended for GPU acceleration)
- **Node.js 18+** and npm/yarn
- **Docker & Docker Compose** for containerized deployment
- **PostgreSQL 15+** for persistent storage
- **Redis 7+** for message brokering

### Quick Start (Docker Compose)

```bash
# Clone the repository
git clone <repository-url> smart-vision-system
cd smart-vision-system

# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose -f infrastructure/docker-compose.yml up --build

# Backend API available at http://localhost:8000
# Frontend Dashboard available at http://localhost:3000
Manual Setup
bash

# 1. Backend Setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/smartvision
export REDIS_URL=redis://localhost:6379

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Frontend Setup
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:3000
AI Pipeline Setup
bash

# Download pre-trained model weights
cd models
# yolov8n.pt and yolov8_weapon_v1.pt should be placed here

# (Optional) Train a custom weapon detection model
cd models
python train_pipeline.py --data weapon_dataset --epochs 100 --batch 16 --lr 0.001
Operator Line Setup
Before starting real-time processing, the operator defines virtual counting lines using the interactive tool:

bash

cd backend
python ai/business_logic/line_selector.py --source rtsp://camera-url
# Or for a video file:
python ai/business_logic/line_selector.py --source path/to/video.mp4
Click two points on the preview frame to set the counting line direction and position. The line configuration is stored in the Pipeline instance for the session.

API Reference
The backend exposes two communication channels:

Channel
Base Route
Purpose
REST API	/api/v1	Historical data, configuration, analytics
WebSocket	/ws	Real-time frames and alert streaming

REST Endpoints
Method
Endpoint
Description
POST	/api/v1/cameras	Create a new camera
GET	/api/v1/cameras	List all cameras
GET	/api/v1/cameras/{id}	Get camera details
PUT	/api/v1/cameras/{id}	Update camera settings
DELETE	/api/v1/cameras/{id}	Delete a camera
GET	/api/v1/alerts	List alerts (paginated, filterable)
GET	/api/v1/alerts/{id}	Get alert details
GET	/api/v1/analytics/summary	Dashboard summary statistics
GET	/api/v1/analytics/heatmap/{camera_id}	Get heatmap image
GET	/api/v1/analytics/zones/{camera_id}	Zone statistics
GET	/api/v1/logs	List event logs (paginated, filterable)
GET	/api/v1/health	System health check

WebSocket Channels
Channel
Message
Description
/ws/cameras/{camera_id}	Annotated frame (base64 JPEG), occupancy, tracks	Live camera stream
/ws/alerts	Real-time alert events	Live alert notifications

Note: Authentication is not enabled in Phase 1. All endpoints are public. JWT + role-based access control is planned for a future release.

For the full API specification with request/response schemas, see docs/api-reference.md.

Frontend Dashboard
The Next.js dashboard provides the primary user interface for monitoring and analysis:

Page
Route
Description
Live Monitor	/monitor	Real-time camera feeds with bounding boxes, track IDs, overlays, and counters
Alerts	/alerts	Active alerts, alert history, and severity indicators
Analytics	/analytics	Occupancy charts, heatmaps, and entry/exit reports
Event Logs	/logs	Historical event logs with search and filtering
Camera Management	/cameras	Camera CRUD operations and status monitoring

State Management: Zustand handles live real-time state (WebSocket data), while React Query manages cached API data for analytics and historical views.

Development Phases
Phase
Scope
Status
Phase 1	AI Layer — detection (YOLOv8), tracking (ByteTrack), business logic (counting, zones, loitering, heatmap, alerts), frame annotation	✅ Complete
Phase 2	Backend — FastAPI application, PostgreSQL, Redis, WebSocket streaming, REST API, background workers	🔲 Next
Phase 3	Frontend — Next.js dashboard with all monitoring, analytics, alerts, and camera management pages	🔲 Planned

Use Cases
The Smart Vision System is designed for deployment in a variety of small business environments:

Retail Stores — Track customer foot traffic, identify peak hours, optimize store layout using heatmap data, and detect shoplifting behavior
Shopping Malls — Monitor crowd density in common areas, manage occupancy limits, and receive real-time security alerts
Warehouses — Track worker movement, monitor restricted zones, ensure safety compliance, and detect unauthorized access
Security Monitoring — Real-time weapon detection, suspicious behavior alerts, and comprehensive event logging for security audits
Visitor Analytics — Understand visitor patterns, measure conversion rates from entry to purchase zones, and generate business intelligence reports
Design Principles
Principle
Implementation
Separation of Concerns	AI, backend, and frontend layers each have a single, well-defined responsibility
Decoupling	Redis message bus separates AI processing workers from WebSocket delivery, enabling independent scaling
Modularity	Each business logic analyzer (counter, zones, behavior, heatmap, alerts) plugs into the Pipeline independently via register_analyzer()
Defensive Processing	All pipeline stages catch exceptions individually — a single bad frame never crashes the processing loop
Scalability	Workers scale independently from the API server and frontend; supports single-machine, worker-separated, and full cloud deployments
Reproducibility	AI experimentation pipeline with argument-driven training, automatic experiment versioning, and metadata logging

Scalability Model
Level
Architecture
Suitable For
1 — Single Machine	All services on one host	Development and small deployments
2 — Worker Separation	AI workers on separate GPU nodes	Multiple cameras, GPU-accelerated inference
3 — Cloud	Fully independent services	Production with horizontal scaling (Kubernetes)

Documentation
For detailed information on specific aspects of the system, refer to the following documents:

Document
Description
architecture.md	Detailed system architecture, data flows, and layer descriptions
api-reference.md	Complete REST and WebSocket API specification
project_structure.md	Full folder and file structure with component descriptions
deployment.md	Deployment guides for Docker, Kubernetes, and production environments

License
This project is developed as a graduation project for academic purposes.

Project Value
Smart Vision System transforms traditional surveillance infrastructure from passive recording into an active, intelligent monitoring platform. By combining real-time AI analysis with business analytics, it delivers:

Enhanced Security — Instant weapon detection, zone intrusion alerts, and suspicious behavior monitoring
Visitor Intelligence — Accurate entry/exit counting, movement pattern analysis, and occupancy management
Operational Awareness — Heatmap-driven layout optimization, peak hour identification, and zone utilization insights
Business Decision-Making — Data-driven insights that support staffing, layout, and operational improvements
The system is designed to be affordable and scalable, making AI-powered surveillance accessible to small businesses that cannot invest in expensive enterprise solutions.