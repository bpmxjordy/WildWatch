# WildWatch

**Live wildlife camera dashboard with real-time AI species detection.**

WildWatch aggregates public wildlife camera livestreams and uses Google's [SpeciesNet](https://github.com/google/cameratrap-detection) AI model to detect animals in real-time. Browse the grid, filter by species or category, and see which streams have animals visible right now.

---

## Architecture

The platform has three components:

| Component | Stack | Runs on |
|-----------|-------|---------|
| **Web app** | Next.js 14, Tailwind CSS, Supabase Realtime | Vercel |
| **Detection agent** | Python, SpeciesNet (MegaDetector + EfficientNet V2), yt-dlp, ffmpeg | Local GPU machine |
| **Backend** | Supabase (PostgreSQL, Realtime, Storage) | Supabase Cloud |

```
 Livestreams (YouTube/explore.org)
        |
        v
 [Detection Agent]  ── yt-dlp ──> frame extraction
        |                          |
        |               SpeciesNet inference (CUDA GPU)
        |                          |
        v                          v
 [Supabase]  <──── detection results + thumbnails
        |
        v
 [Next.js Web App]  <── Realtime subscriptions
        |
        v
   Browser (live-updating grid)
```

---

## Features

- **Real-time detection** - SpeciesNet (MegaDetector v5 + species classifier) runs on each frame
- **Live-updating UI** - Supabase Realtime pushes detections to the browser instantly
- **Category filters** - Filter by Mammals, Birds, or Aquatic
- **"Active detections only"** - Toggle to show only streams with animals visible now
- **Species filter** - Filter by specific detected species
- **Editorial design** - Sage Forest theme with Source Serif 4 / DM Sans / JetBrains Mono
- **Detection history** - Last 5 detections per stream with snapshots and confidence bars
- **Optimized for free tier** - Caches stream list, skips duplicate blanks, prunes old detections

---

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Python](https://www.python.org/) 3.10+
- [Supabase](https://supabase.com/) account (free tier works)
- NVIDIA GPU with CUDA (for the detection agent)
- [ffmpeg](https://ffmpeg.org/) and [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed

### 1. Clone the repo

```bash
git clone https://github.com/bpmxjordy/WildWatch.git
cd WildWatch
```

### 2. Set up Supabase

1. Create a new Supabase project at [supabase.com](https://supabase.com/)
2. Run the migration to create tables:

```bash
# Using Supabase CLI
supabase db push

# Or manually: copy the contents of supabase/migrations/00001_initial_schema.sql
# into the Supabase SQL Editor and run it
```

3. Seed the database with livestream data:

```bash
# Copy supabase/seed.sql into the SQL Editor and run it
```

4. Create a storage bucket called `thumbnails` (set to public)

### 3. Set up the web app

```bash
cd web
npm install
```

Create `web/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Run the dev server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

### 4. Set up the detection agent

```bash
cd agent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install supabase python-dotenv speciesnet
```

Install PyTorch with CUDA support:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Install ffmpeg and yt-dlp:

```bash
# Windows (via winget)
winget install Gyan.FFmpeg
pip install yt-dlp

# macOS
brew install ffmpeg yt-dlp

# Linux
sudo apt install ffmpeg
pip install yt-dlp
```

Create `agent/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

Run the agent:

```bash
python main.py
```

On first run, SpeciesNet will download the model weights (~1.5 GB). Subsequent starts are fast.

---

## Configuration

The agent is configured via environment variables in `agent/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | - | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | - | Supabase service role key |
| `FRAME_INTERVAL_SECONDS` | `60` | Seconds between frame captures per stream |
| `MAX_CONCURRENT_EXTRACTIONS` | `4` | Parallel frame extraction threads |
| `BATCH_SIZE` | `5` | Frames per GPU inference batch |
| `OFFLINE_RETRY_INTERVAL` | `300` | Seconds before retrying an offline stream |
| `FRAME_MAX_DIMENSION` | `1280` | Max image dimension for inference |

---

## Deploying to Vercel

The web app deploys to Vercel with zero configuration:

1. Push the repo to GitHub
2. Import the project in [Vercel](https://vercel.com/new)
3. Set the **Root Directory** to `web`
4. Add environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. Deploy

Or use the Vercel CLI:

```bash
cd web
vercel --prod
```

---

## Project Structure

```
WildWatch/
├── agent/                  # Python detection agent
│   ├── main.py             # Entry point - batch processing loop
│   ├── detector.py         # SpeciesNet wrapper (in-process GPU inference)
│   ├── extractor.py        # Frame extraction (yt-dlp + ffmpeg)
│   ├── scheduler.py        # Round-robin stream scheduler with backoff
│   ├── stream_sources.py   # Cached stream list fetcher
│   ├── uploader.py         # Supabase upload + detection pruning
│   └── config.py           # Environment config
├── web/                    # Next.js 14 web app
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # React components
│   │   ├── hooks/          # Realtime subscription hooks
│   │   └── lib/            # Supabase client, types, utils
│   ├── tailwind.config.ts  # Sage Forest theme tokens
│   └── .env.local          # Supabase credentials
├── supabase/
│   ├── migrations/         # Database schema
│   └── seed.sql            # 22 explore.org livestreams
└── design/                 # Claude design prototype (HTML/JSX)
```

---

## Database Schema

**`streams`** - Livestream metadata + latest detection state

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key |
| `slug` | text | URL-friendly identifier |
| `name` | text | Display name |
| `source_url` | text | YouTube/livestream URL |
| `latest_detection_category` | text | animal, blank, person, vehicle |
| `latest_detection_common_name` | text | e.g. "White-Tailed Deer" |
| `latest_detection_confidence` | float | 0-1 confidence score |
| `latest_detection_thumbnail_url` | text | Latest frame snapshot |
| `is_live` | boolean | Whether agent can reach the stream |

**`detections`** - Detection history (pruned to 5 per stream)

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key |
| `stream_id` | uuid | FK to streams |
| `species_label` | text | Full taxonomy label |
| `common_name` | text | Human-readable species name |
| `category` | text | animal, blank, person, vehicle |
| `confidence` | float | Classification confidence |
| `thumbnail_path` | text | Snapshot URL |
| `detected_at` | timestamptz | When detected |

---

## How It Works

1. **Frame extraction** - yt-dlp resolves the livestream URL (cached 3 hours), ffmpeg grabs a single frame
2. **Parallel extraction** - ThreadPoolExecutor extracts frames from multiple streams simultaneously
3. **Batch inference** - Frames are grouped by country code and sent to SpeciesNet in batches for GPU efficiency
4. **Smart uploads** - Only writes to the database when the detection changes; skips consecutive blank frames
5. **Pruning** - Keeps only the 5 most recent detections per stream, cleaning up old thumbnails from storage
6. **Realtime** - Supabase Realtime pushes changes to connected browsers via WebSocket

---

## License

MIT
