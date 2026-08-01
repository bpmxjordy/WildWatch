# WildWatch

**Live wildlife camera dashboard with real-time AI species detection.**

WildWatch aggregates public wildlife camera livestreams and uses Google's [SpeciesNet](https://github.com/google/cameratrapai) AI model to detect and identify animals in real time. Browse the grid, watch bounding boxes appear on live snapshots, explore geographic and cinematic views, and see activity patterns for every camera over the last 24 hours to 30 days.

🌍 **Live site:** [thewildwatch.vercel.app](https://thewildwatch.vercel.app)

---

## Architecture

| Component | Stack | Runs on |
|-----------|-------|---------|
| **Web app** | Next.js 14 (App Router), Tailwind CSS, Leaflet, Framer Motion | Vercel |
| **Detection agent** | Python, SpeciesNet (MegaDetector v5 + EfficientNet V2), yt-dlp, ffmpeg, Pillow | Docker on a GPU host |
| **Backend** | Supabase (PostgreSQL, Storage) | Supabase Cloud |

```
 Livestreams (YouTube / Ozolio / HDOnTap / explore.org …)
        |
        v
 [Detection Agent]  ── yt-dlp / ffmpeg ──> frame extraction
        |                          |
        |               SpeciesNet inference (CUDA GPU)
        |                          |
        |               taxonomic rollup + temporal consensus
        |               bounding boxes drawn onto snapshot
        |                          |
        v                          v
 [Supabase]  <──── detections + snapshots + daily pre-computed stats
        |
        v
 [Next.js Web App]  (grid · map · explore · species · analytics)
        |
        v
   Browser
```

---

## Features

### Detection & labeling
- **Real-time detection** — SpeciesNet (MegaDetector v5 + species classifier) runs on each frame
- **Baked-in bounding boxes** — boxes are drawn directly onto the snapshot at inference time (NMS-deduplicated, ≥60% detection confidence), so what you see is exactly what the model saw
- **Granular, stable species labels** — a taxonomic probability-mass rollup promotes uncertain guesses to the deepest confident rank (e.g. *Penguin* rather than ten flip-flopping species), and a per-camera temporal consensus votes across recent frames so labels don't flicker
- **Multi-detection per frame** — every distinct animal in a frame is recorded, not just the top one

### Views
- **Live grid** — filter by Mammals / Birds / Aquatic, by species, or toggle "active detections only"
- **Map** — dark CARTO basemap with marker clustering; nearby cameras collapse into a count bubble that splits apart as you zoom
- **Explore** — a cinematic camera-by-camera experience with a radial 24-hour activity clock, an activity-scaled ambient field, a species constellation, and keyboard/swipe navigation
- **Species index** — browse every species detected across the network
- **Per-camera analytics** — hourly activity for the last **24h / 48h / 7d / 30d**, peak-hour and day/night breakdown, and a species leaderboard

### Platform
- **Pre-computed stats** — activity is aggregated once per day per camera and cached (one read per visitor instead of hundreds), using server-side SQL aggregation so counts are never capped
- **Automated weekly digest** — every Monday the agent generates a "Weekly Wild Report" (text + branded stat-card image) and uploads it to Supabase for social posting
- **SEO ready** — dynamic `sitemap.xml` and `robots.txt` covering all stream and species pages
- **Storage-efficient** — snapshots are pruned after 3 days; lightweight detection rows are retained for stats
- **Editorial design** — "Sage Forest" theme with Source Serif 4 / DM Sans / JetBrains Mono
- **Free-tier friendly** — cached stream list, duplicate/blank-frame skipping, batched GPU inference

---

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Docker](https://www.docker.com/) with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) (for the GPU agent), **or** Python 3.10+ with an NVIDIA GPU for a bare-metal agent
- [Supabase](https://supabase.com/) account (free tier works)

### 1. Clone

```bash
git clone https://github.com/bpmxjordy/WildWatch.git
cd WildWatch
```

### 2. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com/).
2. Run every migration in `supabase/migrations/` (in order) via the SQL Editor, or `supabase db push`. These create the `streams`, `detections`, `species_events`, and `stream_stats` tables plus the analytics functions (`get_hourly_activity`, `get_species_breakdown`, `get_hourly_since`, `get_species_since`).
3. Seed streams with `supabase/seed.sql`.
4. Create a **public** storage bucket named `thumbnails`.

### 3. Web app

```bash
cd web
npm install
```

Create `web/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
# Optional — used for sitemap/robots/canonical URLs (defaults to the Vercel URL)
NEXT_PUBLIC_SITE_URL=https://thewildwatch.vercel.app
```

```bash
npm run dev   # http://localhost:3000
```

### 4. Detection agent (Docker — recommended)

```bash
cd agent
cp .env.example .env   # then fill in the values below
docker compose up -d --build
```

`agent/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

On first run SpeciesNet downloads its model weights (~1 GB) into a cached volume; subsequent starts are fast. The agent immediately runs a maintenance pass (stats refresh + image pruning), then processes streams on a rolling schedule.

<details>
<summary>Bare-metal agent (no Docker)</summary>

```bash
cd agent
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
python main.py
```
</details>

---

## Configuration

Agent settings live in `agent/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | — | Supabase project URL + service-role key |
| `FRAME_INTERVAL_SECONDS` | `60` | Seconds between captures per stream |
| `MAX_CONCURRENT_EXTRACTIONS` | `4` | Parallel frame-extraction threads |
| `BATCH_SIZE` | `5` | Frames per GPU inference batch |
| `FRAME_MAX_DIMENSION` | `1280` | Max image dimension for inference |
| `DETECTION_MIN_CONFIDENCE` | `0.6` | Min box confidence to **draw** on the snapshot |
| `DETECTION_RECORD_CONFIDENCE` | `0.5` | Min box confidence to **store** a detection |
| `ROLLUP_THRESHOLD` | tiered | Override the per-rank taxonomic rollup thresholds with one value (lower = more granular) |
| `SPECIES_TRUST` | `0.5` | Trust SpeciesNet's own species call at/above this score |
| `CONSENSUS_WINDOW` / `CONSENSUS_MIN_FRAMES` / `CONSENSUS_FRACTION` | `15` / `3` / `0.5` | Temporal-consensus voting window and agreement thresholds |
| `IMAGE_TTL_DAYS` | `3` | Days before snapshots are pruned from storage |
| `DETECTION_RETENTION_DAYS` | `365` | Days of detection metadata to retain |
| `LABEL_DEBUG` | — | Set to `1` to log raw-vs-committed labels and box confidences |

---

## Deploying to Vercel

1. Import the repo in [Vercel](https://vercel.com/new) with **Root Directory** = `web`.
2. Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and (optionally) `NEXT_PUBLIC_SITE_URL`.
3. Deploy. Push-to-deploy is automatic thereafter.

---

## Project Structure

```
WildWatch/
├── agent/                      # Python detection agent (Docker)
│   ├── main.py                 # Batch loop + daily maintenance + weekly digest
│   ├── detector.py             # SpeciesNet wrapper, NMS, taxonomic rollup
│   ├── consensus.py            # Per-camera temporal consensus voting
│   ├── stats.py                # Daily pre-computed activity stats (SQL aggregation)
│   ├── weekly_digest.py        # Weekly Wild Report generator (text + image)
│   ├── extractor.py            # Frame extraction (yt-dlp + ffmpeg)
│   ├── scheduler.py            # Round-robin stream scheduler with backoff
│   ├── uploader.py             # Snapshot rendering, uploads, pruning
│   └── docker-compose.yml
├── web/                        # Next.js 14 web app
│   └── src/app/
│       ├── page.tsx            # Live grid
│       ├── map/                # Clustered dark map
│       ├── explore/            # Cinematic explorer (clock, ambient field)
│       ├── species/            # Species index + detail
│       ├── stream/[slug]/      # Stream detail + analytics
│       ├── sitemap.ts, robots.ts
├── supabase/
│   ├── migrations/             # Schema + analytics functions + stream_stats
│   └── seed.sql
└── pipeline/                   # WildSight — self-hostable detection pipeline (see pipeline/README.md)
```

---

## Database Schema

**`streams`** — livestream metadata + latest detection state (name, slug, coordinates, `latest_detection_*`, `is_live`).

**`detections`** — per-frame detection history (species label, common name, category, confidence, bbox, `thumbnail_path`, `detected_at`). Retained 365 days; the confidence field holds the MegaDetector box score.

**`species_events`** — species presence windows per stream (start/end, peak confidence, frame count).

**`stream_stats`** — one JSONB row per stream holding pre-computed 24h/48h/7d/30d hourly activity + species breakdowns, refreshed daily by the agent.

Analytics functions (`get_hourly_since`, `get_species_since`, …) aggregate with server-side `GROUP BY` so counts are never truncated by the 1000-row REST limit.

---

## How It Works

1. **Frame extraction** — yt-dlp resolves the stream (cached), ffmpeg grabs one frame; extraction is parallelized across streams.
2. **Batch inference** — frames are grouped by country code and sent to SpeciesNet in GPU batches.
3. **Rollup** — the raw top-k classifier scores are summed up the taxonomy tree; the deepest rank clearing a per-rank threshold wins (species when confident, otherwise family/order/class).
4. **Consensus** — each camera votes the label across a rolling window of recent frames, so the displayed species is stable and sharpens over time.
5. **Snapshot rendering** — NMS-deduplicated boxes above the draw threshold are drawn onto the frame (with confidence labels) before upload.
6. **Smart writes** — detections are recorded per frame; low-confidence noise is filtered; snapshots are timestamped and a `latest.jpg` alias is kept.
7. **Daily maintenance** — stats are pre-computed, old snapshots pruned, and (on Mondays) the weekly digest generated.

---

## License

MIT
