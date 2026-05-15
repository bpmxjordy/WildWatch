from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

from supabase import create_client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, FRAMES_DIR
from detector import SpeciesDetector, extract_common_name
from extractor import extract_frame
from scheduler import Scheduler
from stream_sources import fetch_active_streams
from uploader import upload_thumbnail, upsert_detection, mark_stream_offline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def process_stream(
    stream: dict,
    detector: SpeciesDetector,
    supabase,
    scheduler: Scheduler,
) -> None:
    slug = stream["slug"]
    frame_path = os.path.join(FRAMES_DIR, f"{slug}.jpg")

    success = extract_frame(stream["source_url"], frame_path)
    if not success:
        logger.warning("[%s] Frame extraction failed", slug)
        scheduler.mark_failed(stream["id"])
        mark_stream_offline(supabase, stream["id"])
        return

    results = detector.predict(
        [frame_path], country_code=stream.get("country_code")
    )
    if not results:
        logger.warning("[%s] No prediction returned", slug)
        scheduler.mark_failed(stream["id"])
        return

    prediction = results[0].get("prediction", {})
    category = prediction.get("category", "blank")

    thumbnail_url = None
    if category == "animal":
        thumbnail_url = upload_thumbnail(supabase, slug, frame_path)

    upsert_detection(supabase, stream["id"], prediction, thumbnail_url)
    scheduler.mark_processed(stream["id"])

    common_name = extract_common_name(prediction.get("label"))
    logger.info(
        "[%s] %s — %s (%.0f%%)",
        slug,
        category,
        common_name or "n/a",
        prediction.get("confidence", 0) * 100,
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

            for stream in ready:
                try:
                    await process_stream(stream, detector, supabase, scheduler)
                except Exception:
                    logger.exception("[%s] Unhandled error", stream.get("slug", "?"))
                    scheduler.mark_failed(stream["id"])
                await asyncio.sleep(0.5)

        except Exception:
            logger.exception("Error in main loop")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
