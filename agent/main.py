from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from supabase import create_client

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    FRAMES_DIR,
    MAX_CONCURRENT_EXTRACTIONS,
    BATCH_SIZE,
)
from consensus import Consensus
from detector import SpeciesDetector, parse_prediction, DRAW_MIN_CONF
from extractor import extract_frame
from scheduler import Scheduler
from stats import refresh_all_stats
from stream_sources import fetch_active_streams
from stream_sources import invalidate_stream_cache
from uploader import upload_thumbnail, upsert_detection, mark_stream_offline, prune_old_images
from weekly_digest import generate as generate_weekly_digest

# Weekday the weekly digest is generated on (0 = Monday, UTC).
DIGEST_WEEKDAY = 0

_prune_thread: threading.Thread | None = None


def _prune_running() -> bool:
    return _prune_thread is not None and _prune_thread.is_alive()


def _start_prune() -> None:
    """Run one bounded pruning pass off the main loop."""

    def run() -> None:
        try:
            # Its own client: this runs concurrently with the inference loop.
            prune_old_images(create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY))
        except Exception:
            logger.exception("Image pruning error")

    global _prune_thread
    _prune_thread = threading.Thread(target=run, name="prune", daemon=True)
    _prune_thread.start()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_frame_for_stream(stream: dict) -> tuple[dict, str | None]:
    """Extract a frame for a stream. Returns (stream, frame_path or None)."""
    slug = stream["slug"]
    frame_path = os.path.join(FRAMES_DIR, f"{slug}.jpg")
    platform = stream.get("platform") or "youtube"
    success = extract_frame(stream["source_url"], frame_path, platform=platform)
    if success:
        return (stream, frame_path)
    return (stream, None)


def process_batch(
    streams: list[dict],
    detector: SpeciesDetector,
    supabase,
    scheduler: Scheduler,
    consensus: Consensus,
) -> None:
    """Extract frames in parallel, batch inference, upload results."""
    t0 = time.time()

    # Phase 1: Extract frames in parallel (I/O bound)
    extracted: list[tuple[dict, str]] = []
    failed: list[dict] = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_EXTRACTIONS) as pool:
        futures = {
            pool.submit(extract_frame_for_stream, s): s for s in streams
        }
        for future in as_completed(futures):
            stream, frame_path = future.result()
            if frame_path:
                extracted.append((stream, frame_path))
            else:
                failed.append(stream)

    for stream in failed:
        logger.warning("[%s] Frame extraction failed", stream["slug"])
        state = scheduler._states.get(stream["id"])
        was_online = not state or state.consecutive_failures < 3
        scheduler.mark_failed(stream["id"])
        if was_online and scheduler._states[stream["id"]].consecutive_failures >= 3:
            mark_stream_offline(supabase, stream["id"])

    if not extracted:
        return

    t1 = time.time()
    logger.info(
        "Extracted %d/%d frames in %.1fs",
        len(extracted), len(streams), t1 - t0,
    )

    # Phase 2: Batch inference on GPU
    image_paths = [fp for _, fp in extracted]
    country_codes = [s.get("country_code") for s, _ in extracted]

    # Group by country code for geofencing accuracy
    by_country: dict[str | None, list[tuple[int, dict, str]]] = {}
    for i, (stream, fp) in enumerate(extracted):
        cc = stream.get("country_code")
        by_country.setdefault(cc, []).append((i, stream, fp))

    all_results: list[tuple[dict, dict | None]] = [(s, None) for s, _ in extracted]

    for country_code, group in by_country.items():
        paths = [fp for _, _, fp in group]
        results = detector.predict(paths, country_code=country_code)

        for j, (i, stream, fp) in enumerate(group):
            if j < len(results):
                all_results[i] = (stream, results[j])
            else:
                all_results[i] = (stream, None)

    t2 = time.time()
    logger.info(
        "Inference on %d frames in %.1fs (%.0fms/frame)",
        len(extracted), t2 - t1, (t2 - t1) / len(extracted) * 1000,
    )

    # Phase 3: Upload results
    for stream, result in all_results:
        if result is None:
            scheduler.mark_failed(stream["id"])
            continue

        try:
            parsed = parse_prediction(result)
            committed = consensus.observe(stream["id"], parsed)
            frame_has_animal = parsed["category"] == "animal"

            # Record all boxes; draw only the confident ones on the snapshot.
            all_boxes = parsed.get("all_animal_bboxes") or []
            draw_boxes = (
                [b for b in all_boxes if b["conf"] >= DRAW_MIN_CONF]
                if frame_has_animal else None
            )

            # Blank frames refresh latest.jpg but aren't archived — keeping a
            # permanent snapshot of every empty frame is what filled storage.
            frame_path = os.path.join(FRAMES_DIR, f"{stream['slug']}.jpg")
            thumbnail_url = upload_thumbnail(
                supabase,
                stream["slug"],
                frame_path,
                bboxes=draw_boxes,
                keep_snapshot=frame_has_animal,
            )

            upsert_detection(supabase, stream["id"], parsed, committed, thumbnail_url)
            scheduler.mark_processed(stream["id"])

            if os.getenv("LABEL_DEBUG"):
                cls = (result.get("classifications") or {}).get("classes") or []
                raw_top = cls[0].split(";")[-1].strip() if cls else "n/a"
                box_confs = [round(b["conf"], 2) for b in all_boxes]
                logger.info(
                    "[%s] DEBUG raw_top=%r frame=%s committed=%s(%s) boxes=%s",
                    stream["slug"], raw_top,
                    parsed.get("common_name"),
                    committed.get("common_name"), committed.get("rank"),
                    box_confs,
                )

            logger.info(
                "[%s] %s — %s (%.0f%%)",
                stream["slug"],
                committed.get("category", "blank"),
                committed.get("common_name") or "n/a",
                (committed.get("confidence") or 0) * 100,
            )
        except Exception:
            logger.exception("[%s] Upload error", stream["slug"])
            scheduler.mark_failed(stream["id"])

    t3 = time.time()
    logger.info(
        "Full cycle: %d streams in %.1fs (extract=%.1fs, infer=%.1fs, upload=%.1fs)",
        len(streams), t3 - t0, t1 - t0, t2 - t1, t3 - t2,
    )


async def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    detector = SpeciesDetector()
    scheduler = Scheduler()
    consensus = Consensus()

    logger.info("WildWatch agent starting...")

    # Stats aggregation is expensive and only feeds daily charts, but pruning
    # has to keep pace with uploads, so the two run on separate clocks.
    last_prune: float = 0
    last_maintenance: float = 0
    PRUNE_INTERVAL = 3600  # 1 hour
    MAINTENANCE_INTERVAL = 86400  # 24 hours
    last_digest_week: int | None = None  # ISO week number of the last digest

    while True:
        try:
            now = time.time()
            if now - last_prune > PRUNE_INTERVAL and not _prune_running():
                # Pruning is a long sequential walk over Storage -- running it
                # inline starved inference completely while it worked through a
                # backlog. It gets its own thread (and its own client, since the
                # Supabase client isn't documented as thread-safe).
                _start_prune()
                last_prune = now

            # Daily maintenance: refresh stats, then the weekly digest
            if now - last_maintenance > MAINTENANCE_INTERVAL:
                try:
                    logger.info("Running daily maintenance...")
                    refresh_all_stats(supabase)
                    last_maintenance = now
                    logger.info("Daily maintenance complete.")
                except Exception:
                    logger.exception("Maintenance error")
                    last_maintenance = now  # Don't retry immediately

                # Weekly digest: once per ISO week, on the chosen weekday (UTC)
                today = datetime.now(timezone.utc)
                iso_week = today.isocalendar()[1]
                if today.weekday() == DIGEST_WEEKDAY and iso_week != last_digest_week:
                    try:
                        logger.info("Generating weekly digest...")
                        result = generate_weekly_digest(supabase)
                        if result:
                            last_digest_week = iso_week
                            logger.info(
                                "Weekly digest ready: %s",
                                result.get("img_url") or result.get("txt_url") or "saved locally",
                            )
                        else:
                            logger.info("Weekly digest skipped (no stats yet).")
                    except Exception:
                        logger.exception("Weekly digest error")

            streams = fetch_active_streams(supabase)
            ready = scheduler.get_next_streams(streams)

            if not ready:
                await asyncio.sleep(1)
                continue

            # Process in batches for GPU efficiency
            for i in range(0, len(ready), BATCH_SIZE):
                batch = ready[i : i + BATCH_SIZE]
                process_batch(batch, detector, supabase, scheduler, consensus)

        except Exception:
            logger.exception("Error in main loop")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
