# API Reference

This document defines the **REST APIs** and **WebSocket contracts** for the **Smart Vision System** backend.

It serves as the source of truth for communication between:

* **AI workers**
* **FastAPI backend**
* **Frontend dashboard**

The API is designed to support:

* Camera management
* Real-time frame streaming
* Alert handling
* Analytics retrieval
* Event logs access

---

# 1. API Base Structure

All REST endpoints are versioned under:

```bash id="d4l9ks"
/api/v1
```

The backend exposes two communication mechanisms:

1. **REST API**
2. **WebSocket Streams**

---

# 2. Authentication

Authentication is **not enabled in Phase 1**.

All endpoints are public during development.

Future versions will use:

* JWT Authentication
* Role-based access control

Reserved file:

```bash id="u6pt40"
backend/app/core/security.py
```

---

# 3. Cameras API

The Cameras API manages all camera sources connected to the system.

Base route:

```bash id="c7rj2h"
/api/v1/cameras
```

---

## 3.1 Create Camera

Registers a new camera source.

### Endpoint

```http id="6knf2r"
POST /api/v1/cameras
```

### Request Body

```json id="drz7vn"
{
  "name": "Front Entrance",
  "source_type": "rtsp",
  "source_url": "rtsp://camera-url",
  "is_active": true
}
```

### Response

```json id="4vd5pk"
{
  "id": 1,
  "name": "Front Entrance",
  "source_type": "rtsp",
  "source_url": "rtsp://camera-url",
  "is_active": true,
  "created_at": "2026-04-20T10:00:00Z"
}
```

---

## 3.2 List Cameras

Returns all registered cameras.

### Endpoint

```http id="d6zn4x"
GET /api/v1/cameras
```

### Response

```json id="2i7p5a"
[
  {
    "id": 1,
    "name": "Front Entrance",
    "is_active": true
  }
]
```

---

## 3.3 Get Camera by ID

### Endpoint

```http id="s6f19m"
GET /api/v1/cameras/{camera_id}
```

---

## 3.4 Update Camera

### Endpoint

```http id="u3op8d"
PUT /api/v1/cameras/{camera_id}
```

---

## 3.5 Delete Camera

### Endpoint

```http id="wn2l3j"
DELETE /api/v1/cameras/{camera_id}
```

---

# 4. Alerts API

The Alerts API provides access to live and historical alerts.

Base route:

```bash id="pz7u1v"
/api/v1/alerts
```

---

## 4.1 List Alerts

Returns paginated alert history.

### Endpoint

```http id="t9fv6r"
GET /api/v1/alerts
```

### Query Parameters

```bash id="jlwm9s"
?page=1&limit=20&severity=high&camera_id=1
```

### Response

```json id="m1rf3q"
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

---

## 4.2 Get Alert by ID

### Endpoint

```http id="w8u0rd"
GET /api/v1/alerts/{alert_id}
```

---

# 5. Analytics API

The Analytics API provides business analytics metrics.

Base route:

```bash id="v2g5kc"
/api/v1/analytics
```

---

## 5.1 Dashboard Summary

Returns real-time summary metrics.

### Endpoint

```http id="k7px2s"
GET /api/v1/analytics/summary
```

### Response

```json id="jlwm6r"
{
  "total_in": 125,
  "total_out": 119,
  "current_occupancy": 6,
  "active_alerts": 2
}
```

---

## 5.2 Heatmap Data

Returns heatmap density data.

### Endpoint

```http id="j6tb1p"
GET /api/v1/analytics/heatmap/{camera_id}
```

### Response

```json id="k2vh8m"
{
  "camera_id": 1,
  "heatmap_url": "/static/heatmaps/camera_1_latest.png"
}
```

---

## 5.3 Zone Statistics

### Endpoint

```http id="z5s8qd"
GET /api/v1/analytics/zones/{camera_id}
```

### Response

```json id="r4x2kp"
{
  "zones": [
    {
      "zone_id": 1,
      "name": "Entrance",
      "occupancy": 3,
      "threshold": 5
    }
  ]
}
```

---

# 6. Logs API

The Logs API provides access to historical event logs.

Base route:

```bash id="q2k4yb"
/api/v1/logs
```

---

## 6.1 List Event Logs

### Endpoint

```http id="x5j3uq"
GET /api/v1/logs
```

### Query Parameters

```bash id="s9cw0n"
?camera_id=1&type=entry_event&page=1&limit=50
```

### Response

```json id="t7g2nv"
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

Provides service health information.

Base route:

```bash id="m2x4ut"
/api/v1/health
```

---

## 7.1 Health Check

### Endpoint

```http id="g7u4xk"
GET /api/v1/health
```

### Response

```json id="d5h2jq"
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

---

# 8. WebSocket API

The WebSocket API provides real-time frame and alert streaming.

Base route:

```bash id="v7t3qm"
/ws
```

---

## 8.1 Camera Stream WebSocket

Streams annotated frames for a camera.

### Endpoint

```bash id="c1n9ur"
/ws/cameras/{camera_id}
```

### Message Format

```json id="y8q2as"
{
  "camera_id": 1,
  "timestamp": "2026-04-20T10:25:00Z",
  "frame": "base64-encoded-jpeg",
  "occupancy": 4,
  "tracks": [
    {
      "track_id": 17,
      "bbox": [100, 120, 180, 300]
    }
  ]
}
```

---

## 8.2 Alerts WebSocket

Streams live alert notifications.

### Endpoint

```bash id="r9p3dz"
/ws/alerts
```

### Message Format

```json id="z7x1pk"
{
  "id": 15,
  "camera_id": 1,
  "type": "loitering",
  "severity": "medium",
  "message": "Person stationary for too long",
  "timestamp": "2026-04-20T10:27:00Z"
}
```

---

# 9. Internal Worker Contracts

These are internal payloads exchanged via Redis.

---

## 9.1 Frame Payload

Published by:

```bash id="b3k7ty"
camera_worker.py
```

Consumed by:

```bash id="f8m2vd"
websocket/manager.py
```

### Payload

```json id="j2n6wr"
{
  "camera_id": 1,
  "frame": "base64-jpeg",
  "events": [],
  "timestamp": "2026-04-20T10:30:00Z"
}
```

---

## 9.2 Alert Payload

### Payload

```json id="v4y8qs"
{
  "camera_id": 1,
  "type": "zone_alert",
  "severity": "high",
  "message": "Zone threshold exceeded"
}
```

---

# 10. API Design Principles

The API follows these principles:

---

## REST for Historical Data

REST endpoints are used for:

* configuration
* historical logs
* analytics
* camera management

---

## WebSocket for Live Data

WebSocket is used for:

* live frames
* live alerts

This avoids repeated polling and supports real-time dashboards.

---

## Consistent Response Formats

All endpoints follow consistent JSON structures for:

* lists
* pagination
* timestamps
* errors

---

## Separation of Concerns

Each API group has a dedicated responsibility:

* cameras
* alerts
* analytics
* logs
* health

This simplifies maintenance and future extension.

---

# 11. Future API Extensions

Planned future additions:

* JWT auth endpoints
* zone management APIs
* alert rule management APIs
* reporting APIs
* multi-tenant support

These will be added without changing existing contracts.

---

# 12. API Summary

The Smart Vision System backend provides:

### REST APIs for:

* cameras
* alerts
* analytics
* logs
* health

### WebSocket APIs for:

* live camera frames
* live alerts

The complete communication model is:

```bash id="m8y4tx"
AI Workers → Redis → FastAPI WebSocket → Frontend Dashboard
REST API → Frontend Dashboard
```

This API design ensures:

* modularity
* scalability
* real-time responsiveness
* future extensibility
