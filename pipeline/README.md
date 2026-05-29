# WildSight — Deployable Livestream Detection Pipeline

A self-contained Docker system for wildlife detection on livestream cameras. Create projects, attach camera streams, upload detection models, and monitor real-time species detections through a modern web dashboard.

## Quick Start

```bash
# 1. Clone and enter directory
cd pipeline

# 2. Create config file
cp .env.example .env

# 3. Build and start (CPU mode)
docker compose build
docker compose up -d

# 4. Open in browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:5000/api/v1/health
```

### GPU Mode (NVIDIA)

```bash
# Requires NVIDIA Container Toolkit
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Architecture

```
Frontend (Flask+Jinja2) :3000  →  Backend (Flask API) :5000  →  PostgreSQL :5432
                                          ↕                          ↕
                                       Redis :6379  ←──  Worker (Detection Pipeline)
```

| Service | Description |
|---------|-------------|
| **frontend** | Web UI with project dashboard, camera grid, analytics, map view |
| **backend** | REST API + WebSocket for live updates |
| **worker** | Frame extraction, model inference, notification dispatch |
| **postgres** | Project, stream, detection, and model metadata storage |
| **redis** | Job queue, pub/sub for live detection events |

## Features

- **Multi-source streams**: YouTube, RTSP, HLS, MJPEG, JPEG snapshot cameras
- **Multi-model inference**: YOLOv5, YOLOv8, YOLOv10, YOLO-NAS, SpeciesNet, ONNX, TensorRT, TorchScript
- **Per-stream class filtering**: Select which species to detect per camera
- **GPU memory prediction**: Warns before overcommitting VRAM
- **Notifications**: Email (SMTP), webhook, browser push with cooldown
- **Analytics**: Activity timeline, species breakdown, per-stream stats, site activity score
- **Map view**: Leaflet.js with camera markers, status colors, click-to-view popups
- **PDF export**: Downloadable reports with charts (24h, 7d, 30d, all time)
- **Bulk import**: CSV upload for adding multiple streams at once

## Configuration

All settings are in `.env`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_PORT` | 3000 | Frontend web UI port |
| `BACKEND_PORT` | 5000 | Backend API port |
| `POSTGRES_PASSWORD` | wildsight_dev | Database password |
| `FRAME_INTERVAL_SECONDS` | 60 | Default capture interval |
| `MAX_CONCURRENT_EXTRACTIONS` | 4 | Parallel frame downloads |
| `DETECTION_RETENTION_DAYS` | 30 | How long to keep detection records |
| `SMTP_HOST` | — | SMTP server for email notifications |
| `VAPID_PUBLIC_KEY` | — | Web Push VAPID keys for browser notifications |
| `GPU_VRAM_THRESHOLD` | 0.95 | Max VRAM usage before blocking launch |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET/POST | `/api/v1/projects` | List / create projects |
| GET/PUT/DELETE | `/api/v1/projects/:id` | Project CRUD |
| GET/POST | `/api/v1/projects/:id/streams` | List / add streams |
| POST | `/api/v1/projects/:id/streams/import-csv` | Bulk CSV import |
| GET/PUT/DELETE | `/api/v1/streams/:id` | Stream CRUD |
| POST | `/api/v1/streams/test-url` | Test stream URL reachability |
| GET/POST | `/api/v1/projects/:id/models` | List / upload models |
| GET/DELETE | `/api/v1/models/:id` | Model detail / remove |
| GET | `/api/v1/streams/:id/detections` | Stream detections |
| GET/POST | `/api/v1/projects/:id/notifications` | Notification rules |
| PUT/DELETE | `/api/v1/notifications/:id` | Update / delete rule |
| GET | `/api/v1/projects/:id/analytics/summary` | Analytics summary |
| GET | `/api/v1/projects/:id/analytics/hourly` | Hourly activity |
| GET | `/api/v1/projects/:id/analytics/species` | Species breakdown |
| GET | `/api/v1/projects/:id/analytics/recent` | Recent detections |
| GET | `/api/v1/projects/:id/analytics/stream_stats` | Per-stream stats |
| GET | `/api/v1/projects/:id/export?range=7d` | PDF report download |
| GET | `/api/v1/gpu` | GPU inventory + utilization |
| GET | `/api/v1/gpu/predict` | VRAM prediction for loaded models |

## Adding Custom Models

1. Navigate to your project dashboard
2. Click **Upload Model**
3. Select your model file (`.pt`, `.onnx`, `.engine`, `.torchscript`, `.zip`)
4. Choose the framework (YOLOv8, ONNX, etc.)
5. Class names are auto-detected for YOLO models; enter manually for ONNX/TensorRT
6. Go to a stream's Edit page to assign the model and filter classes

## GPU Setup

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
2. Use the GPU compose override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
   ```
3. GPU info auto-detected on worker startup and shown in the dashboard
4. Check VRAM prediction before starting a project with multiple models

## HTTPS (Production)

See `caddy/Caddyfile.example` for an example reverse proxy config with automatic HTTPS.

## CSV Import Format

```csv
name,source_url,platform,location_name,latitude,longitude,frame_interval_seconds
Eagle Nest,https://youtube.com/watch?v=xxx,youtube,Iowa,-91.79,43.30,60
Bear Cam,https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_XXX,jpeg,British Columbia,-123.08,49.38,30
```
