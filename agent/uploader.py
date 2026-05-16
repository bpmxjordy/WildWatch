from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import Client

logger = logging.getLogger(__name__)

MAX_DETECTIONS_PER_STREAM = 5
PRUNE_EVERY_N = 5

_last_detection: dict[str, str | None] = {}
_insert_count: dict[str, int] = {}


def upload_thumbnail(supabase: Client, stream_slug: str, frame_path: str) -> str | None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    storage_path = f"{stream_slug}/{today}/{timestamp}.jpg"

    with open(frame_path, "rb") as f:
        data = f.read()

    try:
        supabase.storage.from_("thumbnails").upload(
            storage_path,
            data,
            {"content-type": "image/jpeg"},
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
    result = (
        supabase.table("detections")
        .select("id, thumbnail_path")
        .eq("stream_id", stream_id)
        .order("detected_at", desc=True)
        .execute()
    )
    rows = result.data or []
    if len(rows) <= MAX_DETECTIONS_PER_STREAM:
        return

    old_rows = rows[MAX_DETECTIONS_PER_STREAM:]
    old_ids = [r["id"] for r in old_rows]

    paths_to_delete = []
    for r in old_rows:
        thumb = r.get("thumbnail_path")
        if thumb and "/thumbnails/" in thumb:
            path = thumb.split("/thumbnails/", 1)[1]
            paths_to_delete.append(path)

    if paths_to_delete:
        try:
            supabase.storage.from_("thumbnails").remove(paths_to_delete)
        except Exception as e:
            logger.warning("Failed to delete old thumbnails: %s", e)

    for oid in old_ids:
        supabase.table("detections").delete().eq("id", oid).execute()

    logger.debug("Pruned %d old detections for stream %s", len(old_ids), stream_id)


def mark_stream_offline(supabase: Client, stream_id: str) -> None:
    supabase.table("streams").update({"is_live": False}).eq("id", stream_id).execute()
