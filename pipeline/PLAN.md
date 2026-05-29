# WildSight — Deployable Livestream Detection Pipeline

## Vision

A self-contained, Docker-deployable system for creating wildlife detection projects, attaching livestreams, uploading custom object detection models, and monitoring real-time detections through a modern web dashboard. Built on top of the proven WildWatch agent architecture, packaged as a product anyone can deploy on their own hardware.

## Design Decisions (Confirmed)

| Question | Decision |
|----------|----------|
| Multi-user vs single-user | **Single user** — no user accounts, roles, or login |
| Frontend/Backend split | **Two containers** — separate frontend (Flask+Jinja2) and backend (API) |
| RTSP support | **Day one** — must work with IP cameras out of the box |
| Notification channels | **All three** — email, webhook, browser push from the start |
| Model framework scope | **Broad** — YOLOv8, YOLOv10, SpeciesNet, ONNX, TensorRT, and any other common format |
| Product name | **WildSight** |
| Worker lifecycle | **Always running** — Start/Stop toggles processing per project, doesn't restart containers |
| Authentication | **No auth** — local/trusted network tool, no login required |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │   Frontend    │   │   Backend    │   │   Worker(s)    │  │
│  │   (Flask +    │   │  (Flask API) │   │  (Detection    │  │
│  │   Jinja2 +    │◄──►   REST +    │◄──►   Pipeline)    │  │
│  │   Tailwind)   │   │  WebSocket   │   │  GPU-enabled   │  │
│  │   Port 3000   │   │  Port 5000   │   │               │  │
│  └──────────────┘   └──────┬───────┘   └───────┬────────┘  │
│                            │                     │          │
│                    ┌───────┴───────┐             │          │
│                    │   PostgreSQL  │◄────────────┘          │
│                    │   Port 5432   │                        │
│                    └───────┬───────┘                        │
│                            │                                │
│                    ┌───────┴───────┐                        │
│                    │     Redis     │                        │
│                    │   Port 6379   │  (job queue, pubsub)   │
│                    └───────────────┘                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Shared Volumes                            │   │
│  │  /data/models  /data/frames  /data/exports           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Services (5 containers)

| Service       | Role | Tech |
|---------------|------|------|
| **frontend**  | Web UI, serves pages, proxies API | Flask + Jinja2 + Tailwind CSS + Alpine.js |
| **backend**   | REST API + WebSocket for live updates | Flask + Flask-SocketIO + SQLAlchemy |
| **worker**    | Frame extraction, model inference, detection pipeline | Python + PyTorch + ffmpeg + yt-dlp |
| **postgres**  | Persistent storage for projects, streams, detections, models | PostgreSQL 16 |
| **redis**     | Job queue (RQ/Celery), pub/sub for live logs, caching | Redis 7 |

### Why Flask instead of React/Next.js?

- Single language (Python) across the entire stack — lower barrier for wildlife researchers
- Jinja2 server-rendered pages with Alpine.js for interactivity keeps it simple
- No Node.js build step — lighter Docker images
- Flask-SocketIO gives real-time WebSocket updates for logs and live detections
- Tailwind via CDN or standalone CLI binary — no npm required

---

## Data Model

### Core Tables

```sql
-- Projects are the top-level container (no user FK — single-user system)
projects (
    id UUID PK DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'stopped',  -- 'stopped', 'running', 'error'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
)

-- Uploaded detection models
models (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID FK → projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    filename VARCHAR(255) NOT NULL,          -- original upload filename
    storage_path VARCHAR(500) NOT NULL,      -- path on disk: /data/models/{id}/{filename}
    framework VARCHAR(50) NOT NULL,          -- 'yolov5', 'yolov8', 'yolov10', 'yolo_nas', 'speciesnet', 'onnx', 'tensorrt', 'torchscript'
    class_names JSONB NOT NULL DEFAULT '[]', -- ["bear", "deer", "eagle", ...]
    input_size INTEGER DEFAULT 640,          -- model input resolution
    gpu_memory_mb INTEGER,                   -- estimated GPU memory footprint
    precision VARCHAR(10) DEFAULT 'fp16',    -- 'fp32', 'fp16', 'int8'
    file_size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT now()
)

-- Livestream sources
streams (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID FK → projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    source_url TEXT NOT NULL,                 -- stream URL (YouTube, RTSP, HTTP, HLS, etc.)
    platform VARCHAR(30) NOT NULL,            -- 'youtube', 'rtsp', 'hls', 'mjpeg', 'jpeg'
    location_name VARCHAR(200),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timezone VARCHAR(50),                     -- auto-derived from lat/lng, e.g. 'America/New_York'
    model_id UUID FK → models(id),            -- which model to run
    active_classes JSONB DEFAULT '[]',        -- subset of model classes to detect, empty = all
    frame_interval_seconds INTEGER DEFAULT 60,
    is_active BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'idle',        -- 'idle', 'running', 'error', 'offline'
    last_frame_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
)

-- Detection results
detections (
    id UUID PK DEFAULT gen_random_uuid(),
    stream_id UUID FK → streams(id) ON DELETE CASCADE,
    species_label VARCHAR(200),
    common_name VARCHAR(200),
    confidence REAL,
    bbox_x1 REAL, bbox_y1 REAL,
    bbox_x2 REAL, bbox_y2 REAL,
    thumbnail_path VARCHAR(500),
    frame_path VARCHAR(500),                  -- full frame with bbox overlay
    detected_at TIMESTAMPTZ DEFAULT now()
)

-- Notification rules
notification_rules (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID FK → projects(id) ON DELETE CASCADE,
    stream_id UUID FK → streams(id),          -- NULL = all streams in project
    species_filter JSONB DEFAULT '[]',        -- empty = all species
    min_confidence REAL DEFAULT 0.5,
    channel VARCHAR(30) NOT NULL,             -- 'email', 'webhook', 'desktop'
    destination TEXT NOT NULL,                 -- email address, webhook URL, or 'browser'
    cooldown_seconds INTEGER DEFAULT 300,     -- don't re-alert within this window
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
)

-- GPU inventory (auto-detected on startup)
gpu_inventory (
    id SERIAL PK,
    device_index INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    total_memory_mb INTEGER NOT NULL,
    compute_capability VARCHAR(20),
    detected_at TIMESTAMPTZ DEFAULT now()
)
```

---

## Feature Breakdown

### Phase 1 — Foundation (Core Infrastructure)

#### 1.1 Project Scaffolding
- Directory structure with `docker-compose.yml`, per-service Dockerfiles
- Shared volume mounts for models, frames, exports
- `.env.example` with all configuration knobs
- `Makefile` for common commands (`make up`, `make down`, `make logs`, `make build`)

#### 1.2 Database & Migrations
- PostgreSQL 16 container with named volume for persistence
- Alembic for schema migrations
- Seed script with a demo project

#### 1.3 Security (No Auth)
- No login/registration — single-user local tool
- CSRF protection via Flask-WTF on all forms (still needed for form safety)
- Input validation and SQL injection prevention (SQLAlchemy ORM, parameterized queries)
- File upload validation: check MIME type, file extension whitelist, max file size
- Content Security Policy headers
- Docker: non-root user in all containers, read-only filesystem where possible
- Environment-based secrets (never hardcoded)

#### 1.4 Backend API (Flask)
- RESTful endpoints under `/api/v1/`
- Flask-SocketIO for WebSocket push (live logs, detection events)
- SQLAlchemy models matching the schema above
- Marshmallow schemas for request/response validation
- Error handling middleware with consistent JSON error format

### Phase 2 — Project & Stream Management

#### 2.1 Project CRUD
- Create project with name + description
- List projects with status badges (stopped/running/error)
- Edit project details
- Delete project (cascade deletes streams, detections, models)
- Project dashboard as the central hub

#### 2.2 Stream Management
- Add stream with:
  - Name
  - Source URL (text input)
  - Platform type dropdown: YouTube, RTSP, HLS, MJPEG, JPEG
  - URL validation per platform (test connectivity on save)
  - Location: lat/lng text inputs OR interactive map pin (Leaflet.js)
  - Auto-derive timezone from coordinates via `timezonefinder` library
- Edit and remove streams
- Stream health indicator (last successful frame, error count)
- Bulk import streams from CSV

#### 2.3 Model Management
- Upload model files (.pt, .onnx, .engine, .zip for SpeciesNet)
- Select framework: YOLOv8, YOLOv10, SpeciesNet, Custom ONNX
- Auto-detect class names from model metadata (YOLOv8/v10 embed them)
- Manual class name entry for ONNX models
- GPU memory estimation (see Phase 5)
- Assign model to stream(s)
- Per-stream class filter: checklist of model's classes, toggle which to detect

### Phase 3 — Detection Pipeline (Worker)

#### 3.1 Frame Extraction
- Reuse WildWatch extractor architecture: `_extract_jpeg`, `_extract_mjpeg`, `_extract_hls`, `_extract_youtube`
- Add RTSP support: `_extract_rtsp` via ffmpeg
- Configurable frame interval per stream
- Health monitoring: consecutive failure counting, auto-pause after N failures

#### 3.2 Multi-Model Inference
- Model loader that supports:
  - **YOLOv5**: `torch.hub` or ultralytics, `.pt` files
  - **YOLOv8/v10**: `ultralytics` library, `.pt` files
  - **YOLO-NAS**: `super_gradients` library, `.pt` files
  - **SpeciesNet**: existing WildWatch detector, `.zip` bundles
  - **ONNX Runtime**: `.onnx` files with `onnxruntime-gpu`
  - **TensorRT**: `.engine` files for maximum GPU throughput
  - **TorchScript**: `.torchscript` / `.pt` traced models
- Model pool: load/unload models based on which streams are active
- Per-stream class filtering: only report detections matching `active_classes`
- Batch inference: group frames by model, run batch predict for GPU efficiency

#### 3.3 Result Processing
- Parse bounding boxes, class labels, confidence scores
- Draw bbox overlays on frames (PIL/OpenCV), save annotated frame
- Store detection rows in PostgreSQL
- Publish detection events via Redis pub/sub → WebSocket to frontend
- Age-based detection pruning (configurable retention period)

#### 3.4 Notification Dispatch
- On detection matching notification rules:
  - Email via SMTP (configurable SMTP server)
  - Webhook: POST JSON payload to user-specified URL
  - Browser push notification via Web Push API
- Cooldown enforcement: skip if last trigger was within `cooldown_seconds`
- Notification log table for history/debugging

### Phase 4 — Dashboard & Visualization

#### 4.1 Project Overview Page
- Start/Stop buttons → toggles processing for the project (worker always running)
- Real-time Docker logs panel (streamed via WebSocket)
- Grid of active camera feeds with latest frame thumbnails
- Detection event feed (live updates via WebSocket)

#### 4.2 Camera Detail View
- Latest frame with bounding box overlay
- Classification history table (species, confidence, timestamp)
- Stream health stats (uptime, frames processed, error rate)

#### 4.3 Analytics Dashboard
- **Activity Timeline**: hourly detection heatmap (like WildWatch)
- **Species Breakdown**: pie/bar chart of detected species distribution
- **Site Activity Score**: composite metric based on:
  - Detection frequency (detections per hour)
  - Species diversity (unique species count / total possible)
  - Temporal spread (activity across different hours)
  - Formula: `activity_score = (det_freq * 0.4 + diversity * 0.3 + temporal_spread * 0.3) * 100`
- **Per-Species Stats**: filter timeline/charts by individual species
- **Trend Analysis**: compare activity across days/weeks
- Time range selector: 24h, 7d, 30d, All Time

#### 4.4 Map View
- Leaflet.js map with markers for each camera
- Marker color indicates status (green=detecting, yellow=idle, red=offline)
- Click marker → popup with latest detection thumbnail + species
- Cluster markers at zoom-out levels
- Optional satellite/terrain base layers

#### 4.5 Bounding Box Viewer
- Full-size frame view with drawn bounding boxes
- Toggle individual detections on/off
- Confidence score labels on each box
- Gallery of recent detection frames

### Phase 5 — GPU Management & Predictions

#### 5.1 GPU Auto-Detection
- On worker startup: query NVIDIA GPUs via `pynvml` (Python bindings for NVML)
- Store in `gpu_inventory` table: name, total VRAM, compute capability
- Display in UI: GPU card with model, memory, utilization

#### 5.2 Memory Prediction Engine
- Model memory estimation rules:
  - **YOLOv8/v10 Nano**: ~50MB (fp16), ~100MB (fp32)
  - **YOLOv8/v10 Small**: ~80MB (fp16), ~160MB (fp32)
  - **YOLOv8/v10 Medium**: ~200MB (fp16), ~400MB (fp32)
  - **YOLOv8/v10 Large**: ~400MB (fp16), ~800MB (fp32)
  - **YOLOv8/v10 XLarge**: ~700MB (fp16), ~1.4GB (fp32)
  - **SpeciesNet**: ~1.5GB
  - **Custom ONNX**: estimate from file size × 2.5 multiplier
  - **PyTorch overhead**: ~300MB base CUDA context
- Pre-launch validation:
  - Sum all loaded model sizes + base overhead
  - Compare against available GPU VRAM
  - Show warning with breakdown if over budget
  - Block launch if predicted usage > 95% of VRAM (configurable threshold)
- UI: visual bar chart showing predicted VRAM allocation per model vs. available

#### 5.3 Runtime Monitoring
- Periodic VRAM usage polling (actual vs. predicted)
- Alert if VRAM usage exceeds threshold
- Display in dashboard: real-time GPU utilization, temperature, memory

### Phase 6 — Export & Reporting

#### 6.1 PDF Report Generation
- Use `reportlab` or `weasyprint` for PDF generation
- Report sections:
  - Project summary (name, streams count, models, date range)
  - Per-stream summary: detection counts, top species, activity score
  - Activity timeline chart (rendered as image via matplotlib)
  - Species breakdown chart
  - Top detection thumbnails with timestamps
  - Site activity comparison table
- Time range options: 24hr, 1 week, 1 month, All Time
- Downloadable from dashboard, or scheduled email delivery

### Phase 7 — Polish & Production Readiness

#### 7.1 NVIDIA Docker Support
- Base worker image: `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
- `docker-compose.yml` with `deploy.resources.reservations.devices` for GPU passthrough
- Fallback CPU-only mode when no GPU detected
- CUDA + cuDNN pre-installed in worker image
- TensorRT optional layer

#### 7.2 UI/UX Polish
- Design system matching WildWatch:
  - `Source Serif 4` for headings, `DM Sans` for body, `JetBrains Mono` for code/stats
  - Earthy color palette: forest green accents, cream backgrounds, dark text
  - Subtle card shadows, rounded corners, consistent spacing
- Responsive layout (works on tablet for field researchers)
- Dark mode support
- Loading skeletons for async data
- Toast notifications for actions (saved, deleted, error)

#### 7.3 Security Hardening
- Helmet-style security headers middleware
- File upload sandboxing (virus scan integration point)
- API rate limiting per user
- Audit log for sensitive actions (model upload, project delete, settings change)
- Docker: no `--privileged`, minimal capabilities, non-root users
- Secrets management via Docker secrets or `.env` file
- CORS configuration for API

#### 7.4 Observability
- Structured JSON logging across all services
- Health check endpoints (`/health`, `/ready`)
- Docker healthcheck directives in compose
- Optional Prometheus metrics endpoint

---

## Directory Structure

```
pipeline/
├── docker-compose.yml              # Main orchestration
├── docker-compose.gpu.yml          # GPU override (nvidia runtime)
├── .env.example                    # Configuration template
├── Makefile                        # Convenience commands
├── README.md                       # Setup & usage guide
│
├── frontend/                       # Flask frontend service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                      # Flask app factory
│   ├── config.py
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css             # Tailwind output
│   │   ├── js/
│   │   │   └── app.js              # Alpine.js components
│   │   └── img/
│   ├── templates/
│   │   ├── base.html               # Layout with nav, footer
│   │   ├── projects/
│   │   │   ├── list.html
│   │   │   ├── create.html
│   │   │   ├── overview.html       # Main dashboard
│   │   │   └── edit.html
│   │   ├── streams/
│   │   │   ├── add.html
│   │   │   ├── detail.html
│   │   │   └── edit.html
│   │   ├── models/
│   │   │   ├── upload.html
│   │   │   └── list.html
│   │   ├── analytics/
│   │   │   ├── dashboard.html
│   │   │   ├── species.html
│   │   │   └── export.html
│   │   ├── notifications/
│   │   │   └── rules.html
│   │   └── map/
│   │       └── view.html
│   └── forms.py                    # WTForms form classes
│
├── backend/                        # Flask API service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                      # App factory
│   ├── config.py
│   ├── extensions.py               # SQLAlchemy, Redis, SocketIO init
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── stream.py
│   │   ├── detection.py
│   │   ├── model.py
│   │   ├── notification.py
│   │   └── gpu.py
│   ├── api/                        # API blueprints
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── streams.py
│   │   ├── models.py
│   │   ├── detections.py
│   │   ├── notifications.py
│   │   ├── analytics.py
│   │   ├── export.py
│   │   └── gpu.py
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── model_service.py        # Model upload, validation, memory estimation
│   │   ├── stream_service.py       # Stream CRUD, URL validation
│   │   ├── detection_service.py    # Detection queries, aggregation
│   │   ├── notification_service.py # Notification dispatch
│   │   ├── export_service.py       # PDF report generation
│   │   ├── gpu_service.py          # GPU detection, memory prediction
│   │   └── docker_service.py       # Worker lifecycle management
│   ├── schemas/                    # Marshmallow serialization
│   │   ├── __init__.py
│   │   └── ...
│   └── migrations/                 # Alembic
│       ├── alembic.ini
│       ├── env.py
│       └── versions/
│
├── worker/                         # Detection pipeline
│   ├── Dockerfile                  # nvidia/cuda base
│   ├── Dockerfile.cpu              # CPU-only fallback
│   ├── requirements.txt
│   ├── main.py                     # Worker entry point
│   ├── config.py
│   ├── extractors/                 # Frame extraction per platform
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── youtube.py
│   │   ├── rtsp.py
│   │   ├── hls.py
│   │   ├── mjpeg.py
│   │   └── jpeg.py
│   ├── inference/                  # Model loading & inference
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract model interface
│   │   ├── yolov5.py               # YOLOv5 via torch.hub/ultralytics
│   │   ├── yolo.py                 # YOLOv8/v10 via ultralytics
│   │   ├── yolo_nas.py             # YOLO-NAS via super_gradients
│   │   ├── speciesnet.py           # SpeciesNet wrapper
│   │   ├── onnx_model.py           # ONNX Runtime inference
│   │   ├── tensorrt_model.py       # TensorRT .engine inference
│   │   ├── torchscript_model.py    # TorchScript .pt inference
│   │   └── model_pool.py           # Load/unload management
│   ├── pipeline.py                 # Extract → infer → store → notify
│   ├── scheduler.py                # Stream scheduling (from WildWatch)
│   ├── overlay.py                  # BBox drawing on frames
│   └── gpu_monitor.py              # NVML-based GPU monitoring
│
└── data/                           # Docker volumes mount here
    ├── models/                     # Uploaded model files
    ├── frames/                     # Extracted frames
    └── exports/                    # Generated PDF reports
```

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Frontend | Flask + Jinja2 + Tailwind CSS + Alpine.js | All-Python stack, no Node.js build |
| Backend API | Flask + Flask-SocketIO + SQLAlchemy | Lightweight, WebSocket support |
| Database | PostgreSQL 16 | Proven, JSONB for flexible fields |
| Queue/Cache | Redis 7 | Job queue, pub/sub for live updates |
| Worker | Python + PyTorch + Ultralytics + ONNX Runtime | Multi-model support |
| Frame extraction | ffmpeg + yt-dlp | Proven from WildWatch |
| GPU management | pynvml | NVIDIA GPU monitoring |
| PDF export | WeasyPrint + matplotlib | HTML-to-PDF with charts |
| Maps | Leaflet.js | Lightweight, no API key needed |
| Interactivity | Alpine.js + HTMX | Minimal JS, server-driven |
| Auth | None (local tool) | No login required |
| Containerization | Docker + docker-compose | Single-command deploy |
| GPU passthrough | NVIDIA Container Toolkit | GPU in Docker |

---

## Implementation Order

The phases should be built in order, as each depends on the previous:

1. **Phase 1** → Foundation: Docker, DB, auth, API skeleton
2. **Phase 2** → Project/stream/model CRUD (the data layer)
3. **Phase 3** → Worker pipeline (the engine)
4. **Phase 5** → GPU management (needed before Phase 3 can safely run)
5. **Phase 4** → Dashboard & visualization (needs Phase 3 producing data)
6. **Phase 6** → Export & reporting (needs Phase 4 analytics)
7. **Phase 7** → Polish, security hardening, production readiness

Estimated total: ~3-4 weeks of focused development.

