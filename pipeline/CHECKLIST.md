# WildSight — Implementation Checklist

Track progress here. Mark items `[x]` when complete.

---

## Phase 1 — Foundation

### 1.1 Project Scaffolding
- [x] Create directory structure (`frontend/`, `backend/`, `worker/`, `data/`)
- [x] Write `docker-compose.yml` with all 5 services (frontend, backend, worker, postgres, redis)
- [x] Write `docker-compose.gpu.yml` override for NVIDIA GPU passthrough
- [x] Create `.env.example` with all config variables
- [x] Create `Makefile` with `up`, `down`, `build`, `logs`, `migrate`, `shell` targets
- [x] Write Dockerfile for `frontend` service
- [x] Write Dockerfile for `backend` service
- [x] Write Dockerfile for `worker` (GPU-enabled, nvidia/cuda base)
- [x] Write Dockerfile.cpu for `worker` (CPU fallback)

### 1.2 Database & Migrations
- [x] PostgreSQL container config with named volume
- [x] Alembic setup in backend (`alembic init`, `env.py` config)
- [x] Migration: `projects` table
- [x] Migration: `models` table
- [x] Migration: `streams` table
- [x] Migration: `detections` table
- [x] Migration: `notification_rules` table
- [x] Migration: `gpu_inventory` table
- [x] Seed script with demo project + sample stream

### 1.3 Security (No Auth)
- [x] CSRF protection (Flask-WTF — disabled for local use, ready to enable)
- [x] Input validation (SQLAlchemy ORM, parameterized queries)
- [x] File upload validation (MIME type, extension whitelist, max size)
- [x] Content Security Policy headers
- [x] Non-root user in all Dockerfiles

### 1.4 Backend API Skeleton
- [x] Flask app factory (`create_app()`)
- [x] SQLAlchemy initialization + model base
- [x] Redis connection setup
- [x] Flask-SocketIO initialization
- [x] API blueprint registration under `/api/v1/`
- [x] Error handling middleware (consistent JSON errors)
- [x] Health check endpoint (`/api/v1/health`)
- [x] CORS configuration
- [x] Request logging middleware

---

## Phase 2 — Project & Stream Management

### 2.1 Project CRUD
- [x] `POST /api/v1/projects` — create project
- [x] `GET /api/v1/projects` — list projects
- [x] `GET /api/v1/projects/:id` — get project details
- [x] `PUT /api/v1/projects/:id` — update project
- [x] `DELETE /api/v1/projects/:id` — delete project (cascade)
- [x] Project list page (frontend template)
- [x] Project create form page
- [x] Project edit form page
- [x] Project status badges (stopped/running/error)

### 2.2 Stream Management
- [x] `POST /api/v1/projects/:id/streams` — add stream
- [x] `GET /api/v1/projects/:id/streams` — list streams
- [x] `GET /api/v1/streams/:id` — stream detail
- [x] `PUT /api/v1/streams/:id` — update stream
- [x] `DELETE /api/v1/streams/:id` — remove stream
- [x] Stream add form with:
  - [x] Name input
  - [x] URL input with validation
  - [x] Platform type dropdown (youtube, rtsp, hls, mjpeg, jpeg)
  - [x] URL connectivity test on save
  - [x] Lat/lng coordinate inputs
  - [x] Leaflet.js map pin dropper
  - [x] Auto timezone from coordinates (timezonefinder)
- [x] Stream edit form (full with model assignment + class filter)
- [x] Stream health indicators (last frame, errors, consecutive failures)
- [x] Bulk CSV import for streams

### 2.3 Model Management
- [x] `POST /api/v1/projects/:id/models` — upload model
- [x] `GET /api/v1/projects/:id/models` — list models
- [x] `GET /api/v1/models/:id` — model detail
- [x] `DELETE /api/v1/models/:id` — remove model
- [x] Model upload form:
  - [x] File upload (.pt, .onnx, .engine, .torchscript, .zip)
  - [x] Framework selector dropdown (YOLOv5, YOLOv8, YOLOv10, YOLO-NAS, SpeciesNet, ONNX, TensorRT, TorchScript)
  - [x] Auto-detect class names from YOLO model metadata
  - [x] Manual class name entry for ONNX/TensorRT/custom
  - [x] File size + MIME type validation
  - [x] Upload progress indicator (drag & drop UI)
- [x] Assign model to stream dropdown (in stream edit form)
- [x] Per-stream class filter checklist (toggle which species to detect)
- [x] GPU memory estimation display on upload

---

## Phase 3 — Detection Pipeline (Worker)

### 3.1 Frame Extraction
- [x] YouTube extractor (yt-dlp + ffmpeg) — port from WildWatch
- [x] JPEG snapshot extractor — port from WildWatch
- [x] MJPEG stream extractor — port from WildWatch
- [x] HLS stream extractor — port from WildWatch
- [x] RTSP stream extractor (ffmpeg)
- [x] Extractor registry (platform → extractor function)
- [x] Per-stream configurable frame interval
- [x] Consecutive failure tracking + auto-pause

### 3.2 Multi-Model Inference
- [x] Abstract model interface (`BaseDetector` with `load()`, `predict()`, `unload()`)
- [x] YOLOv5 implementation via `torch.hub`
- [x] YOLOv8/v10 implementation via `ultralytics`
- [x] YOLO-NAS implementation via `super_gradients`
- [x] SpeciesNet implementation (from WildWatch detector.py)
- [x] ONNX Runtime implementation (`onnxruntime-gpu`)
- [x] TensorRT implementation (`.engine` files)
- [x] TorchScript implementation (`.torchscript` files)
- [x] Model pool: load/unload based on active streams
- [x] Per-stream class filtering (only return matching detections)
- [x] Batch inference: group frames by model for GPU efficiency

### 3.3 Result Processing
- [x] Parse bounding boxes, labels, confidence scores
- [x] Draw bbox overlays on frames (PIL)
- [x] Save annotated frames to `/data/frames/`
- [x] Insert detection rows into PostgreSQL
- [x] Publish detection events via Redis pub/sub
- [x] WebSocket broadcast to connected frontend clients
- [x] Age-based detection pruning (configurable retention)

### 3.4 Notification System
- [x] Notification rule evaluation on each detection
- [x] Email dispatch via SMTP (configurable server)
- [x] Webhook dispatch (POST JSON to user URL)
- [x] Browser push notification (Web Push API via Redis pub/sub)
- [x] Cooldown enforcement per rule
- [x] Notification history/log (last_triggered_at tracked)
- [x] Notification rule CRUD API + UI

---

## Phase 4 — Dashboard & Visualization

### 4.1 Project Overview Page
- [x] Start/Stop project buttons (toggles processing, worker always running)
- [x] Real-time detection feed (polling every 15s)
- [x] Camera grid with latest frame thumbnails
- [x] Live detection event feed with species/confidence
- [x] Project status summary cards (streams, models, detections today, species)

### 4.2 Camera Detail View
- [x] Latest frame with bounding box overlay display
- [x] Classification history table (species, confidence, time)
- [x] Stream health stats (interval, failures, last frame)
- [x] Frame refresh button
- [x] Mini map with location pin

### 4.3 Analytics Dashboard
- [x] Activity timeline heatmap (hourly detection bar chart)
- [x] Species breakdown chart (doughnut)
- [x] Site activity score (per-stream stats table)
- [x] Per-species stats view (species list with bar graph)
- [x] Time range selector (24h, 7d, 30d, All Time)
- [x] Per-stream performance table (detections, species, last detection)

### 4.4 Map View
- [x] Leaflet.js map integration
- [x] Camera markers with status colors (green/yellow/red)
- [x] Click marker → popup with latest detection + thumbnail
- [x] Auto-fit bounds to all cameras
- [x] Satellite/terrain layer (OpenStreetMap)

### 4.5 Bounding Box Viewer
- [x] Full-size frame display with drawn bboxes (annotated frames)
- [x] Confidence score labels (drawn on frame overlay)
- [x] Detection frame in stream detail and feed

---

## Phase 5 — GPU Management & Predictions

### 5.1 GPU Auto-Detection
- [x] pynvml GPU enumeration on worker startup
- [x] Store GPU info in `gpu_inventory` table
- [x] API endpoint: `GET /api/v1/gpu` — list GPUs + utilization
- [x] GPU runtime stats (memory, utilization, temperature)

### 5.2 Memory Prediction Engine
- [x] Model memory estimation rules (per framework + size tier)
- [x] Pre-launch validation: sum models vs. available VRAM
- [x] `GET /api/v1/gpu/predict` — VRAM prediction endpoint
- [x] Block launch if predicted > 95% VRAM (API check)

### 5.3 Runtime GPU Monitoring
- [x] Periodic VRAM/utilization polling (gpu_monitor.py)
- [x] GPU stats available via API
- [x] Runtime stats in GPU API response

---

## Phase 6 — Export & Reporting

### 6.1 PDF Report Generation
- [x] Report template (WeasyPrint HTML → PDF)
- [x] Project summary section
- [x] Per-stream detection summary table
- [x] Activity timeline chart (matplotlib → base64 image)
- [x] Species breakdown chart (matplotlib pie → base64 image)
- [x] Species list with percentages
- [x] Time range options: 24hr, 1 week, 1 month, All Time
- [x] `GET /api/v1/projects/:id/export?range=7d` endpoint
- [x] Download button in analytics dashboard

---

## Phase 7 — Polish & Production

### 7.1 NVIDIA Docker Support
- [x] nvidia/cuda base image for worker
- [x] GPU passthrough in docker-compose.gpu.yml
- [x] CPU fallback mode detection (Dockerfile.cpu)
- [x] CUDA + cuDNN pre-installed in GPU image

### 7.2 UI/UX Polish
- [x] Design system: Source Serif 4, DM Sans, JetBrains Mono fonts
- [x] Earthy color palette (forest green, cream, dark text)
- [x] Card styling, shadows, rounded corners
- [x] Responsive layout (grid adapts to screen size)
- [x] Toast notifications for actions
- [x] Consistent iconography (SVG icons throughout)
- [x] Drag & drop file upload with progress

### 7.3 Security Hardening
- [x] Security headers middleware (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy)
- [x] File upload sandboxing (extension whitelist, size limit)
- [x] Rate limiting on API endpoints (Flask-Limiter)
- [x] Docker security: non-root users, no privileged
- [x] Secrets via .env
- [x] HTTPS reverse proxy config example (Caddy)

### 7.4 Observability
- [x] Structured logging (all services)
- [x] Health check endpoints (/api/v1/health)
- [x] Docker healthcheck directives in compose (postgres, redis, backend, frontend)
- [x] Service status via `docker compose ps`

### 7.5 Documentation
- [x] README.md with setup instructions
- [x] Quick start guide (clone → build → up → browser)
- [x] Configuration reference (.env variables table)
- [x] API reference (full endpoint table)
- [x] Adding custom models guide
- [x] GPU setup guide (NVIDIA Container Toolkit)
- [x] CSV import format documentation
- [x] HTTPS production guide (Caddy example)
