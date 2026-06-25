from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont
from supabase import Client

logger = logging.getLogger(__name__)

PRUNE_AGE_DAYS = 8  # Keep detections for 8 days (analytics looks at 7)
PRUNE_EVERY_N = 20

_last_detection: dict[str, str | None] = {}
_insert_count: dict[str, int] = {}

BOX_COLOR = (106, 155, 90)
LABEL_BG = (106, 155, 90, 200)
LABEL_TEXT = (255, 255, 255)


def _draw_bboxes(frame_path: str, bboxes: list[dict]) -> bytes:
    """Draw bounding boxes onto the image and return JPEG bytes."""
    img = Image.open(frame_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for det in bboxes:
        bbox = det["bbox"]  # [x, y, width, height] normalised 0-1
        conf = det.get("conf", 0)
        x1 = int(bbox[0] * w)
        y1 = int(bbox[1] * h)
        x2 = int((bbox[0] + bbox[2]) * w)
        y2 = int((bbox[1] + bbox[3]) * h)

        # Skip full-frame boxes
        if x1 == 0 and y1 == 0 and x2 >= w - 1 and y2 >= h - 1:
            continue

        draw.rectangle([x1, y1, x2, y2], outline=BOX_COLOR, width=3)

        label = f"{conf * 100:.0f}%"
        lbox = draw.textbbox((0, 0), label, font=font)
        lw, lh = lbox[2] - lbox[0], lbox[3] - lbox[1]
        draw.rectangle([x1, y1 - lh - 6, x1 + lw + 8, y1], fill=LABEL_BG)
        draw.text((x1 + 4, y1 - lh - 4), label, fill=LABEL_TEXT, font=font)

    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def upload_thumbnail(
    supabase: Client,
    stream_slug: str,
    frame_path: str,
    bboxes: list[dict] | None = None,
) -> str | None:
    """Upload a timestamped snapshot (with bboxes drawn) and update latest.jpg."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    snapshot_path = f"{stream_slug}/{ts}.jpg"

    if bboxes:
        data = _draw_bboxes(frame_path, bboxes)
    else:
        with open(frame_path, "rb") as f:
            data = f.read()

    try:
        supabase.storage.from_("thumbnails").upload(
            snapshot_path,
            data,
            {"content-type": "image/jpeg"},
        )
    except Exception as e:
        logger.warning("Thumbnail upload failed: %s", e)
        return None

    # Also update latest.jpg for the stream card thumbnail
    try:
        supabase.storage.from_("thumbnails").upload(
            f"{stream_slug}/latest.jpg",
            data,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
    except Exception:
        pass

    return supabase.storage.from_("thumbnails").get_public_url(snapshot_path)


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

    all_bboxes = parsed.get("all_animal_bboxes", [])
    if all_bboxes:
        rows = []
        for det in all_bboxes:
            bbox = det["bbox"]
            rows.append({
                "stream_id": stream_id,
                "species_label": label,
                "common_name": common_name,
                "category": category,
                "confidence": det["conf"],
                "classification_confidence": parsed.get("confidence"),
                "prediction_source": parsed.get("prediction_source"),
                "bbox_x1": bbox[0],
                "bbox_y1": bbox[1],
                "bbox_x2": bbox[0] + bbox[2],
                "bbox_y2": bbox[1] + bbox[3],
                "thumbnail_path": thumbnail_url,
                "detected_at": now,
            })
        supabase.table("detections").insert(rows).execute()
    else:
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
