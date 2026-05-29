from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config import FRAMES_DIR, MAX_CONCURRENT_EXTRACTIONS, DETECTION_RETENTION_DAYS
from extractors import extract_frame
from inference import ModelPool, DetectionResult
from notifications import evaluate_and_dispatch
from overlay import draw_detections
from scheduler import Scheduler

logger = logging.getLogger(__name__)


def fetch_active_streams(session: Session, project_id: str) -> list[dict]:
    result = session.execute(
        text("""
            SELECT s.id, s.project_id, s.name, s.source_url, s.platform, s.model_id,
                   s.active_classes, s.min_confidence, s.frame_interval_seconds, s.latitude, s.longitude,
                   m.storage_path AS model_path, m.framework, m.class_names AS model_classes
            FROM streams s
            LEFT JOIN models m ON s.model_id = m.id
            WHERE s.project_id = :pid AND s.is_active = true
        """),
        {"pid": project_id},
    )
    return [dict(row._mapping) for row in result]


def _extract_for_stream(stream: dict) -> tuple[dict, str | None]:
    slug = stream["id"]
    frame_path = os.path.join(FRAMES_DIR, f"{slug}.jpg")
    success = extract_frame(stream["source_url"], frame_path, stream["platform"])
    return (stream, frame_path if success else None)


def process_batch(
    streams: list[dict],
    model_pool: ModelPool,
    session: Session,
    scheduler: Scheduler,
    redis_client=None,
) -> None:
    t0 = time.time()

    extracted = []
    failed = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_EXTRACTIONS) as pool:
        futures = {pool.submit(_extract_for_stream, s): s for s in streams}
        for future in as_completed(futures):
            stream, frame_path = future.result()
            if frame_path:
                extracted.append((stream, frame_path))
            else:
                failed.append(stream)

    for stream in failed:
        failures = scheduler.mark_failure(stream["id"])
        if failures >= 3:
            session.execute(
                text("UPDATE streams SET status = 'offline', consecutive_failures = :f WHERE id = :id"),
                {"f": failures, "id": stream["id"]},
            )
            session.commit()

    if not extracted:
        return

    t1 = time.time()
    logger.info("Extracted %d/%d frames in %.1fs", len(extracted), len(streams), t1 - t0)

    now = datetime.now(timezone.utc).isoformat()

    for stream, frame_path in extracted:
        model_id = stream.get("model_id")
        framework = stream.get("framework")
        model_path = stream.get("model_path")

        if not model_id or not framework or not model_path:
            scheduler.mark_success(stream["id"])
            session.execute(
                text("UPDATE streams SET status = 'running', last_frame_at = :now, consecutive_failures = 0 WHERE id = :id"),
                {"now": now, "id": stream["id"]},
            )
            session.commit()
            continue

        try:
            detector = model_pool.get(
                str(model_id), framework, model_path,
                class_names=stream.get("model_classes", []),
            )
            detections = detector.predict(frame_path)
        except Exception:
            logger.exception("[%s] Inference failed", stream["name"])
            scheduler.mark_failure(stream["id"])
            continue

        # Apply confidence threshold (default 0.5)
        min_conf = stream.get("min_confidence") or 0.5
        detections = [d for d in detections if d.confidence >= min_conf]

        # Apply class filter if set
        active_classes = stream.get("active_classes") or []
        if active_classes:
            detections = [d for d in detections if d.class_name in active_classes]

        # Filter out blanks, persons, vehicles
        SKIP_LABELS = {"blank", "person", "vehicle", "unknown"}
        detections = [d for d in detections if d.class_name.lower() not in SKIP_LABELS]

        if detections:
            annotated_path = os.path.join(FRAMES_DIR, f"{stream['id']}_annotated.jpg")
            draw_detections(frame_path, detections, annotated_path)

            for det in detections:
                import uuid as uuid_mod
                session.execute(
                    text("""
                        INSERT INTO detections (id, stream_id, species_label, common_name, confidence,
                                                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                                                thumbnail_path, frame_path, detected_at)
                        VALUES (:id, :sid, :label, :name, :conf, :x1, :y1, :x2, :y2, :thumb, :frame, :at)
                    """),
                    {
                        "id": str(uuid_mod.uuid4()),
                        "sid": stream["id"],
                        "label": det.class_name,
                        "name": det.class_name.replace("_", " ").title(),
                        "conf": det.confidence,
                        "x1": det.bbox_x1, "y1": det.bbox_y1,
                        "x2": det.bbox_x2, "y2": det.bbox_y2,
                        "thumb": frame_path,
                        "frame": annotated_path,
                        "at": now,
                    },
                )

            if redis_client:
                import json
                event = {
                    "stream_id": str(stream["id"]),
                    "stream_name": stream["name"],
                    "detections": [
                        {"class": d.class_name, "confidence": d.confidence}
                        for d in detections
                    ],
                    "timestamp": now,
                }
                redis_client.publish("detections", json.dumps(event))

            # Dispatch notifications
            det_dicts = [{"class_name": d.class_name, "confidence": d.confidence} for d in detections]
            try:
                evaluate_and_dispatch(
                    session, redis_client,
                    str(stream.get("project_id", "")), str(stream["id"]), stream["name"],
                    det_dicts,
                )
            except Exception:
                logger.exception("[%s] Notification dispatch error", stream["name"])

        session.execute(
            text("UPDATE streams SET status = 'running', last_frame_at = :now, consecutive_failures = 0 WHERE id = :id"),
            {"now": now, "id": stream["id"]},
        )
        session.commit()
        scheduler.mark_success(stream["id"])

        if detections:
            species_summary = ", ".join(f"{d.class_name} ({d.confidence:.0%})" for d in detections)
            logger.info("[%s] %d detection(s): %s", stream["name"], len(detections), species_summary)
        else:
            logger.info("[%s] no detections (threshold: %.0f%%)", stream["name"], min_conf * 100)

    # Prune old detections periodically
    _prune_counter[0] = _prune_counter[0] + 1
    if _prune_counter[0] % 20 == 0:
        _prune_old_detections(session, [s["id"] for s, _ in extracted])

    t2 = time.time()
    logger.info("Batch complete: %d streams in %.1fs", len(extracted), t2 - t0)


_prune_counter = [0]


def _prune_old_detections(session: Session, stream_ids: list[str]) -> None:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=DETECTION_RETENTION_DAYS)).isoformat()
    for sid in stream_ids:
        result = session.execute(
            text("DELETE FROM detections WHERE stream_id = :sid AND detected_at < :cutoff"),
            {"sid": sid, "cutoff": cutoff},
        )
        session.commit()
