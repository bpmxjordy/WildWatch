from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont
from supabase import Client

logger = logging.getLogger(__name__)

# Detection metadata is kept long enough to fully cover the 30-day stats
# window (with margin). Only the snapshot images are pruned aggressively.
PRUNE_AGE_DAYS = int(os.getenv("DETECTION_RETENTION_DAYS", "365"))
# Once blank frames stopped being archived the daily write volume dropped by
# roughly 10x, so snapshots can be kept far longer than the old 3 days.
IMAGE_TTL_DAYS = int(os.getenv("IMAGE_TTL_DAYS", "14"))
PRUNE_EVERY_N = 200

# Full frame quality — storage headroom is spent on resolution, not volume.
SNAPSHOT_QUALITY = int(os.getenv("SNAPSHOT_QUALITY", "85"))

# Storage list() pages at 100 by default; page through instead of silently
# seeing only the first 100 objects in a folder that holds thousands.
LIST_PAGE_SIZE = 500

# Pruning is a long sequential walk over Storage. Bound how much one pass may
# delete so it always returns promptly, and keep a kill switch for when a bulk
# cleanup (scripts/cleanup-storage.py) is already clearing the same bucket.
PRUNE_ENABLED = os.getenv("PRUNE_ENABLED", "1") not in ("0", "false", "False")
PRUNE_MAX_DELETES = int(os.getenv("PRUNE_MAX_DELETES", "5000"))

# Generated weekly digests live in the bucket too and are not regenerable.
PRUNE_EXCLUDE = {"reports"}

_last_detection: dict[str, str | None] = {}
_insert_count: dict[str, int] = {}

BOX_COLOR = (106, 155, 90)
LABEL_BG = (106, 155, 90, 200)
LABEL_TEXT = (255, 255, 255)


def _draw_bboxes(frame_path: str, bboxes: list[dict]) -> Image.Image:
    """Draw bounding boxes onto the image and return it (encoding is caller's job)."""
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

    return Image.alpha_composite(img, overlay).convert("RGB")


def _encode(frame_path: str, bboxes: list[dict] | None) -> bytes:
    """Draw any boxes onto the frame and return full-resolution JPEG bytes."""
    if bboxes:
        img = _draw_bboxes(frame_path, bboxes)
    else:
        img = Image.open(frame_path).convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=SNAPSHOT_QUALITY, optimize=True)
    return buf.getvalue()


def upload_thumbnail(
    supabase: Client,
    stream_slug: str,
    frame_path: str,
    bboxes: list[dict] | None = None,
    keep_snapshot: bool = True,
) -> str | None:
    """Refresh latest.jpg, and archive a timestamped snapshot when it's worth keeping.

    A blank frame's only job is to refresh the card thumbnail, so `keep_snapshot`
    is False for those. Archiving every frame regardless is what filled the
    bucket: ~1,440 permanent objects per camera per day, the overwhelming
    majority of them empty scenery.
    """
    storage = supabase.storage.from_("thumbnails")
    data = _encode(frame_path, bboxes)

    try:
        storage.upload(
            f"{stream_slug}/latest.jpg",
            data,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
    except Exception as e:
        logger.warning("[%s] latest.jpg upload failed: %s", stream_slug, e)

    if not keep_snapshot:
        # No archive for this frame, so point the card at the rolling alias.
        # latest.jpg is a stable path behind a CDN, hence the cache-buster.
        url = storage.get_public_url(f"{stream_slug}/latest.jpg")
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}v={int(datetime.now(timezone.utc).timestamp())}"

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_path = f"{stream_slug}/{ts}.jpg"
    try:
        storage.upload(
            snapshot_path,
            data,
            {"content-type": "image/jpeg"},
        )
    except Exception as e:
        logger.warning("[%s] snapshot upload failed: %s", stream_slug, e)
        return None

    return storage.get_public_url(snapshot_path)


def upsert_detection(
    supabase: Client,
    stream_id: str,
    parsed: dict,
    committed: dict,
    thumbnail_url: str | None,
) -> None:
    # `committed` is the temporally-smoothed label from the consensus voter;
    # `parsed` carries this frame's bounding boxes and prediction source.
    category = committed.get("category", "blank")
    common_name = committed.get("common_name")
    label = committed.get("species_label")
    confidence = committed.get("confidence", 0)

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

    # Insert detection rows only when THIS frame actually saw an animal, using
    # the temporally-committed species label for consistency across frames.
    all_bboxes = parsed.get("all_animal_bboxes", [])
    if category != "animal" or not all_bboxes:
        return

    rows = []
    for det in all_bboxes:
        bbox = det["bbox"]
        rows.append({
            "stream_id": stream_id,
            "species_label": label,
            "common_name": common_name,
            "category": category,
            "confidence": det["conf"],
            "classification_confidence": confidence,
            "prediction_source": parsed.get("prediction_source"),
            "bbox_x1": bbox[0],
            "bbox_y1": bbox[1],
            "bbox_x2": bbox[0] + bbox[2],
            "bbox_y2": bbox[1] + bbox[3],
            "thumbnail_path": thumbnail_url,
            "detected_at": now,
        })
    supabase.table("detections").insert(rows).execute()

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


def _list_all(storage, path: str | None) -> list[dict]:
    """List every entry under `path`, paging past Storage's 100-item default."""
    entries: list[dict] = []
    offset = 0
    while True:
        page = storage.list(
            path,
            {
                "limit": LIST_PAGE_SIZE,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if not page:
            break
        entries.extend(page)
        if len(page) < LIST_PAGE_SIZE:
            break
        offset += len(page)
    return entries


def prune_old_images(supabase: Client) -> None:
    """Delete thumbnail images older than IMAGE_TTL_DAYS from storage."""
    from datetime import timedelta
    import re

    if not PRUNE_ENABLED:
        logger.info("Image pruning disabled (PRUNE_ENABLED=0)")
        return

    try:
        storage = supabase.storage.from_("thumbnails")
        folders = _list_all(storage, None)
        if not folders:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=IMAGE_TTL_DAYS)
        total_deleted = 0

        for folder in folders:
            folder_name = folder.get("name", "")
            if not folder_name or folder_name in PRUNE_EXCLUDE:
                continue
            files = _list_all(storage, folder_name)
            to_delete = []
            for f in files or []:
                name = f.get("name", "")
                # Match timestamped files like 20260625_164300.jpg
                m = re.match(r"(\d{8})_(\d{6})\.jpg$", name)
                if not m:
                    continue
                try:
                    file_dt = datetime.strptime(f"{m.group(1)}{m.group(2)}", "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    if file_dt < cutoff:
                        to_delete.append(f"{folder_name}/{name}")
                except ValueError:
                    continue
            for i in range(0, len(to_delete), 100):
                storage.remove(to_delete[i : i + 100])
                total_deleted += len(to_delete[i : i + 100])
                if total_deleted >= PRUNE_MAX_DELETES:
                    logger.info(
                        "Pruned %d images (hit PRUNE_MAX_DELETES); resuming next pass",
                        total_deleted,
                    )
                    return

        if total_deleted:
            logger.info("Pruned %d images older than %d days", total_deleted, IMAGE_TTL_DAYS)
    except Exception:
        logger.exception("Image pruning failed")


def mark_stream_offline(supabase: Client, stream_id: str) -> None:
    supabase.table("streams").update({"is_live": False}).eq("id", stream_id).execute()
