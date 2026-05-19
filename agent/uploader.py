from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import Client

logger = logging.getLogger(__name__)

PRUNE_AGE_DAYS = 8  # Keep detections for 8 days (analytics looks at 7)
PRUNE_EVERY_N = 20

_last_detection: dict[str, str | None] = {}
_insert_count: dict[str, int] = {}


def upload_thumbnail(supabase: Client, stream_slug: str, frame_path: str) -> str | None:
    """Upload a single latest.jpg per stream, overwriting the previous one."""
    storage_path = f"{stream_slug}/latest.jpg"

    with open(frame_path, "rb") as f:
        data = f.read()

    try:
        supabase.storage.from_("thumbnails").upload(
            storage_path,
            data,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
    except Exception as e:
        logger.warning("Thumbnail upload failed: %s", e)
        return None

    return supabase.storage.from_("thumbnails").get_public_url(storage_path)


def upsert_detection(
    supabase: Client,
    stream_id: str,
    parsed: dict,
    thumbnail_url: str | None,
) -> None:
    from detector import extract_common_name

    label = parsed.get("label")
    common_name = extract_common_name(label)
    category = parsed.get("category", "blank")
    confidence = parsed.get("confidence", 0)

    prev = _last_detection.get(stream_id)
    detection_key = f"{category}:{label}"
    changed = prev != detection_key

    if category == "blank" and not changed:
        # Still blank — only update the thumbnail, skip the detections insert
        if thumbnail_url:
            supabase.table("streams").update(
                {
                    "latest_detection_thumbnail_url": thumbnail_url,
                    "latest_detection_at": datetime.now(timezone.utc).isoformat(),
                    "is_live": True,
                }
            ).eq("id", stream_id).execute()
        return

    _last_detection[stream_id] = detection_key
    now = datetime.now(timezone.utc).isoformat()

    if changed:
        supabase.table("streams").update(
            {
                "latest_detection_species": label,
                "latest_detection_common_name": common_name,
                "latest_detection_confidence": confidence,
                "latest_detection_category": category,
                "latest_detection_thumbnail_url": thumbnail_url,
                "latest_detection_at": now,
                "is_live": True,
            }
        ).eq("id", stream_id).execute()
    else:
        supabase.table("streams").update(
            {
                "latest_detection_thumbnail_url": thumbnail_url,
                "latest_detection_at": now,
                "is_live": True,
            }
        ).eq("id", stream_id).execute()

    # Only insert into detections table for actual wildlife sightings
    if category != "animal":
        return

    bbox = parsed.get("bbox")
    supabase.table("detections").insert(
        {
            "stream_id": stream_id,
            "species_label": label,
            "common_name": common_name,
            "category": category,
            "confidence": confidence,
            "classification_confidence": parsed.get("confidence"),
            "prediction_source": parsed.get("prediction_source"),
            "bbox_x1": bbox[0] if bbox else None,
            "bbox_y1": bbox[1] if bbox else None,
            "bbox_x2": (bbox[0] + bbox[2]) if bbox else None,
            "bbox_y2": (bbox[1] + bbox[3]) if bbox else None,
            "thumbnail_path": thumbnail_url,
            "detected_at": now,
        }
    ).execute()

    count = _insert_count.get(stream_id, 0) + 1
    _insert_count[stream_id] = count
    if count % PRUNE_EVERY_N == 0:
        _prune_old_detections(supabase, stream_id)


def _prune_old_detections(supabase: Client, stream_id: str) -> None:
    """Delete detections older than PRUNE_AGE_DAYS to keep the table lean."""
    cutoff = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    from datetime import timedelta
    cutoff = (cutoff - timedelta(days=PRUNE_AGE_DAYS)).isoformat()

    result = (
        supabase.table("detections")
        .delete()
        .eq("stream_id", stream_id)
        .lt("detected_at", cutoff)
        .execute()
    )
    deleted = len(result.data) if result.data else 0
    if deleted:
        logger.debug("Pruned %d detections older than %d days for stream %s", deleted, PRUNE_AGE_DAYS, stream_id)


def mark_stream_offline(supabase: Client, stream_id: str) -> None:
    supabase.table("streams").update({"is_live": False}).eq("id", stream_id).execute()
