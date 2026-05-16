from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from supabase import create_client

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    FRAMES_DIR,
    MAX_CONCURRENT_EXTRACTIONS,
    BATCH_SIZE,
)
from detector import SpeciesDetector, parse_prediction, extract_common_name
from extractor import extract_frame
from scheduler import Scheduler
from stream_sources import fetch_active_streams
from stream_sources import invalidate_stream_cache
from uploader import upload_thumbnail, upsert_detection, mark_stream_offline

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
    success = extract_frame(stream["source_url"], frame_path)
    if success:
        return (stream, frame_path)
    return (stream, None)


def process_batch(
    streams: list[dict],
    detector: SpeciesDetector,
    supabase,
    scheduler: Scheduler,
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
            category = parsed["category"]

            frame_path = os.path.join(FRAMES_DIR, f"{stream['slug']}.jpg")
            thumbnail_url = upload_thumbnail(supabase, stream["slug"], frame_path)

            upsert_detection(supabase, stream["id"], parsed, thumbnail_url)
            scheduler.mark_processed(stream["id"])

            common_name = extract_common_name(parsed.get("label"))
            logger.info(
                "[%s] %s — %s (%.0f%%)",
                stream["slug"],
                category,
                common_name or "n/a",
                parsed.get("confidence", 0) * 100,
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

    logger.info("WildWatch agent starting...")

    while True:
        try:
            streams = fetch_active_streams(supabase)
            ready = scheduler.get_next_streams(streams)

            if not ready:
                await asyncio.sleep(1)
                continue

            # Process in batches for GPU efficiency
            for i in range(0, len(ready), BATCH_SIZE):
                batch = ready[i : i + BATCH_SIZE]
                process_batch(batch, detector, supabase, scheduler)

        except Exception:
            logger.exception("Error in main loop")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
