from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from supabase import Client

logger = logging.getLogger(__name__)


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

    url = supabase.storage.from_("thumbnails").get_public_url(storage_path)
    return url


def upsert_detection(
    supabase: Client,
    stream_id: str,
    prediction: dict,
    thumbnail_url: str | None,
) -> None:
    from detector import extract_common_name

    label = prediction.get("label")
    common_name = extract_common_name(label)
    category = prediction.get("category", "blank")
    confidence = prediction.get("confidence", 0)
    now = datetime.now(timezone.utc).isoformat()

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

    supabase.table("detections").insert(
        {
            "stream_id": stream_id,
            "species_label": label,
            "common_name": common_name,
            "category": category,
            "confidence": confidence,
            "thumbnail_path": thumbnail_url,
            "detected_at": now,
        }
    ).execute()


def mark_stream_offline(supabase: Client, stream_id: str) -> None:
    supabase.table("streams").update({"is_live": False}).eq("id", stream_id).execute()
