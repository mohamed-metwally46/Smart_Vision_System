# API Reference

This document defines the **REST APIs** and **WebSocket contracts** for the **Smart Vision System** backend.

---

# 1. API Base Structure

All REST endpoints are versioned under `/api/v1`.

Two communication mechanisms:
1. **REST API** — historical data, configuration
2. **WebSocket** — real-time frames and alerts

---

# 2. Authentication

Authentication is **not enabled in Phase 1**. All endpoints are public.

Future: JWT + role-based access control → `backend/app/core/security.py`

---

# 3. Cameras API

Base route: `/api/v1/cameras`

## 3.1 Create Camera
```http
POST /api/v1/cameras
```
**Request:**
```json
{
  "name": "Front Entrance",
  "source_type": "rtsp",
  "source_url": "rtsp://camera-url",
  "is_active": true
}
```
**Response:**
```json
{
  "id": 1,
  "name": "Front Entrance",
  "source_type": "rtsp",
  "source_url": "rtsp://camera-url",
  "is_active": true,
  "created_at": "2026-04-20T10:00:00Z"
}
```

## 3.2 List Cameras
```http
GET /api/v1/cameras
```
**Response:**
```json
[{ "id": 1, "name": "Front Entrance", "is_active": true }]
```

## 3.3 Get Camera by ID
```http
GET /api/v1/cameras/{camera_id}
```

## 3.4 Update Camera
```http
PUT /api/v1/cameras/{camera_id}
```

## 3.5 Delete Camera
```http
DELETE /api/v1/cameras/{camera_id}
```

---

# 4. Alerts API

Base route: `/api/v1/alerts`

## 4.1 List Alerts
```http
GET /api/v1/alerts?page=1&limit=20&severity=high&camera_id=1
```
**Response:**
```json
{
  "items": [
    {
      "id": 10,
      "camera_id": 1,
      "type": "zone_overcrowding",
      "severity": "high",
      "message": "Zone capacity exceeded",
      "timestamp": "2026-04-20T10:15:00Z"
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 1
}
```

**Alert Types:**

| type | severity | source |
|---|---|---|
| `zone_overcrowding` | high | ZoneMonitor + AlertEngine |
| `loitering` | medium | BehaviorAnalyzer + AlertEngine |
| `crossing_event` | low | EntryExitCounter + AlertEngine |
| `zone_occupancy` | low | ZoneMonitor (informational) |

## 4.2 Get Alert by ID
```http
GET /api/v1/alerts/{alert_id}
```

---

# 5. Analytics API

Base route: `/api/v1/analytics`

## 5.1 Dashboard Summary
```http
GET /api/v1/analytics/summary
```
**Response:**
```json
{
  "total_in": 125,
  "total_out": 119,
  "current_occupancy": 6,
  "active_alerts": 2
}
```

## 5.2 Heatmap Data
```http
GET /api/v1/analytics/heatmap/{camera_id}
```
**Response:**
```json
{
  "camera_id": 1,
  "heatmap_url": "/static/heatmaps/camera_1_latest.png"
}
```

## 5.3 Zone Statistics
```http
GET /api/v1/analytics/zones/{camera_id}
```
**Response:**
```json
{
  "zones": [
    { "zone_id": 1, "name": "Entrance", "occupancy": 3, "threshold": 5 }
  ]
}
```

---

# 6. Logs API

Base route: `/api/v1/logs`

## 6.1 List Event Logs
```http
GET /api/v1/logs?camera_id=1&type=entry_event&page=1&limit=50
```
**Response:**
```json
{
  "items": [
    {
      "id": 100,
      "camera_id": 1,
      "event_type": "entry_event",
      "message": "Person entered",
      "timestamp": "2026-04-20T10:20:00Z"
    }
  ]
}
```

---

# 7. Health API

Base route: `/api/v1/health`

## 7.1 Health Check
```http
GET /api/v1/health
```
**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

---

# 8. WebSocket API

Base route: `/ws`

## 8.1 Camera Stream WebSocket
```
/ws/cameras/{camera_id}
```
**Message Format:**
```json
{
  "camera_id": 1,
  "timestamp": "2026-04-20T10:25:00Z",
  "frame": "base64-encoded-jpeg",
  "occupancy": 4,
  "tracks": [
    { "track_id": 17, "bbox": [100, 120, 180, 300] }
  ]
}
```

## 8.2 Alerts WebSocket
```
/ws/alerts
```
**Message Format:**
```json
{
  "camera_id": 1,
  "type": "loitering",
  "severity": "medium",
  "message": "Person (ID:7) stationary for 32s",
  "timestamp": "2026-04-20T10:27:00Z",
  "metadata": {
    "track_id": 7,
    "duration_s": 32,
    "position": [640, 360]
  }
}
```

---

# 9. Internal Worker Contracts

## 9.1 Frame Payload
Published by `camera_worker.py` → consumed by `websocket/manager.py` via Redis.

```json
{
  "camera_id": 1,
  "frame": "base64-jpeg",
  "events": [],
  "timestamp": "2026-04-20T10:30:00Z"
}
```

## 9.2 Alert Payload
Published by `alert_engine.py` → consumed by `alert_worker.py` via Redis.

```json
{
  "camera_id": 1,
  "type": "zone_overcrowding",
  "severity": "high",
  "message": "Zone 'Entrance' overcrowded: 4 persons (threshold: 3)",
  "timestamp": "2026-04-20T10:30:00Z",
  "metadata": {
    "zone_id": 1,
    "zone_name": "Entrance",
    "occupancy": 4,
    "threshold": 3,
    "occupant_ids": [2, 5, 7, 11]
  }
}
```

## 9.3 AlertEngine Cooldowns

| Alert Type | Default Cooldown |
|---|---|
| `zone_overcrowding` | 15 seconds |
| `loitering` | 20 seconds |
| `crossing_event` | none (every crossing logged) |
| `zone_occupancy` | none (informational) |

---

# 10. API Design Principles

- **REST** for historical data: configuration, logs, analytics, camera management
- **WebSocket** for live data: frames, alerts — avoids polling
- **Consistent JSON** structures: lists, pagination, timestamps, errors
- **Separation of Concerns**: cameras / alerts / analytics / logs / health each isolated

---

# 11. Future API Extensions

- JWT auth endpoints
- Zone management APIs (CRUD for polygon zones)
- Alert rule management APIs (custom thresholds)
- Reporting APIs (daily/weekly summaries)
- Multi-tenant support

---

# 12. API Summary

```
AI Workers → AlertEngine → Redis → FastAPI WebSocket → Frontend Dashboard
                                → PostgreSQL → REST API → Frontend Analytics
```
