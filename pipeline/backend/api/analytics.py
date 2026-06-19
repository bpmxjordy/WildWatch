from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from extensions import db
from models.detection import Detection
from models.stream import Stream

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1")

RANGE_MAP = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _get_cutoff(range_param: str) -> datetime | None:
    delta = RANGE_MAP.get(range_param)
    if delta:
        return datetime.now(timezone.utc) - delta
    return None


def _get_stream_ids(project_id):
    streams = Stream.query.filter_by(project_id=project_id).all()
    return [s.id for s in streams], streams


@analytics_bp.route("/projects/<uuid:project_id>/analytics/summary", methods=["GET"])
def project_summary(project_id):
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, streams = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({
            "total_detections": 0, "unique_species": 0, "species_list": [],
            "stream_count": 0, "active_streams": 0, "detections_today": 0,
        })

    query = Detection.query.filter(Detection.stream_id.in_(stream_ids))
    if cutoff:
        query = query.filter(Detection.detected_at >= cutoff)
    detections = query.all()
    species_set = {d.common_name for d in detections if d.common_name}

    today_cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = Detection.query.filter(
        Detection.stream_id.in_(stream_ids),
        Detection.detected_at >= today_cutoff,
    ).count()

    return jsonify({
        "total_detections": len(detections),
        "unique_species": len(species_set),
        "species_list": sorted(species_set),
        "stream_count": len(streams),
        "active_streams": sum(1 for s in streams if s.status == "running"),
        "detections_today": today_count,
    })


@analytics_bp.route("/projects/<uuid:project_id>/analytics/hourly", methods=["GET"])
def hourly_activity(project_id):
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, _ = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"hours": []})

    result = db.session.execute(
        db.text("""
            SELECT date_trunc('hour', detected_at) AS hour, COUNT(*) AS count
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY hour
            ORDER BY hour
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    hours = [{"hour": row.hour.isoformat(), "count": row.count} for row in result]
    return jsonify({"hours": hours})


@analytics_bp.route("/projects/<uuid:project_id>/analytics/species", methods=["GET"])
def species_breakdown(project_id):
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, _ = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"species": []})

    result = db.session.execute(
        db.text("""
            SELECT common_name, COUNT(*) AS count,
                   ROUND(AVG(confidence)::numeric, 3) AS avg_confidence
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND common_name IS NOT NULL
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY common_name
            ORDER BY count DESC
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    species = [{"name": row.common_name, "count": row.count, "avg_confidence": float(row.avg_confidence)} for row in result]
    return jsonify({"species": species})


@analytics_bp.route("/projects/<uuid:project_id>/analytics/recent", methods=["GET"])
def recent_detections(project_id):
    """Recent detections across all streams in a project."""
    limit = request.args.get("limit", 20, type=int)
    stream_ids, _ = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"detections": []})

    result = db.session.execute(
        db.text("""
            SELECT d.id, d.stream_id, d.species_label, d.common_name,
                   d.confidence, d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2,
                   d.thumbnail_path, d.frame_path, d.detected_at,
                   s.name AS stream_name
            FROM detections d
            JOIN streams s ON d.stream_id = s.id
            WHERE d.stream_id = ANY(:stream_ids)
            ORDER BY d.detected_at DESC
            LIMIT :lim
        """),
        {"stream_ids": stream_ids, "lim": min(limit, 100)},
    )
    detections = []
    for row in result:
        detections.append({
            "id": str(row.id),
            "stream_id": str(row.stream_id),
            "stream_name": row.stream_name,
            "species_label": row.species_label,
            "common_name": row.common_name,
            "confidence": row.confidence,
            "bbox": {"x1": row.bbox_x1, "y1": row.bbox_y1, "x2": row.bbox_x2, "y2": row.bbox_y2}
            if row.bbox_x1 is not None else None,
            "thumbnail_path": row.thumbnail_path,
            "frame_path": row.frame_path,
            "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        })
    return jsonify({"detections": detections})


@analytics_bp.route("/projects/<uuid:project_id>/analytics/species/<species_name>", methods=["GET"])
def species_detail(project_id, species_name):
    """Stats and hourly activity for a single species."""
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, _ = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"count": 0, "hourly": []})

    # Basic stats
    stats = db.session.execute(
        db.text("""
            SELECT COUNT(*) AS count,
                   ROUND(AVG(confidence)::numeric, 3) AS avg_confidence,
                   MIN(detected_at) AS first_seen,
                   MAX(detected_at) AS last_seen
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND common_name = :species
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
        """),
        {"stream_ids": stream_ids, "species": species_name, "cutoff": cutoff},
    ).fetchone()

    # Hourly breakdown for this species
    hourly = db.session.execute(
        db.text("""
            SELECT date_trunc('hour', detected_at) AS hour, COUNT(*) AS count
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND common_name = :species
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY hour
            ORDER BY hour
        """),
        {"stream_ids": stream_ids, "species": species_name, "cutoff": cutoff},
    )

    return jsonify({
        "species": species_name,
        "count": stats.count if stats else 0,
        "avg_confidence": float(stats.avg_confidence) if stats and stats.avg_confidence else None,
        "first_seen": stats.first_seen.strftime("%d %b %Y %H:%M") if stats and stats.first_seen else None,
        "last_seen": stats.last_seen.strftime("%d %b %Y %H:%M") if stats and stats.last_seen else None,
        "hourly": [{"hour": row.hour.isoformat(), "count": row.count} for row in hourly],
    })


@analytics_bp.route("/projects/<uuid:project_id>/analytics/heatmap", methods=["GET"])
def heatmap_data(project_id):
    """Geographic heatmap: detection counts per stream location."""
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, streams = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"points": [], "time_grid": []})

    # Per-stream detection counts with coordinates
    result = db.session.execute(
        db.text("""
            SELECT d.stream_id, COUNT(*) AS count
            FROM detections d
            WHERE d.stream_id = ANY(:stream_ids)
              AND (:cutoff IS NULL OR d.detected_at >= :cutoff)
            GROUP BY d.stream_id
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    counts_map = {str(row.stream_id): row.count for row in result}

    points = []
    for s in streams:
        if s.latitude and s.longitude:
            count = counts_map.get(str(s.id), 0)
            points.append({
                "lat": s.latitude,
                "lng": s.longitude,
                "count": count,
                "name": s.name,
                "stream_id": str(s.id),
            })

    # Time-of-day × day-of-week heatmap grid
    time_result = db.session.execute(
        db.text("""
            SELECT EXTRACT(DOW FROM detected_at) AS dow,
                   EXTRACT(HOUR FROM detected_at) AS hour,
                   COUNT(*) AS count
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY dow, hour
            ORDER BY dow, hour
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    time_grid = [{"dow": int(row.dow), "hour": int(row.hour), "count": row.count} for row in time_result]

    # Hourly distribution (all days combined)
    hourly_dist = db.session.execute(
        db.text("""
            SELECT EXTRACT(HOUR FROM detected_at) AS hour, COUNT(*) AS count
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY hour
            ORDER BY hour
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    hourly_distribution = [{"hour": int(row.hour), "count": row.count} for row in hourly_dist]

    return jsonify({
        "points": points,
        "time_grid": time_grid,
        "hourly_distribution": hourly_distribution,
    })


@analytics_bp.route("/projects/<uuid:project_id>/analytics/map_timeline", methods=["GET"])
def map_timeline(project_id):
    """Time-bucketed detection counts per stream, for animated map playback.

    Returns buckets aligned to the range:
      24h → 1h buckets (24 frames)
      7d  → 6h buckets (28 frames)
      30d → 1d buckets (30 frames)

    Optional ?species=Kea,Bear filters to only those common_names.
    """
    range_param = request.args.get("range", "7d")
    species_filter = request.args.get("species")  # comma-separated

    bucket_map = {
        "24h": ("hour", timedelta(hours=24), "hour"),
        "7d": ("6h", timedelta(days=7), "6h"),
        "30d": ("day", timedelta(days=30), "day"),
    }
    bucket_kind, range_delta, _ = bucket_map.get(range_param, bucket_map["7d"])
    cutoff = datetime.now(timezone.utc) - range_delta

    stream_ids, streams = _get_stream_ids(project_id)
    if not stream_ids:
        return jsonify({"buckets": [], "streams": [], "species": []})

    # Build trunc expression — avoid % operator (psycopg2 paramstyle eats it)
    trunc_exprs = {
        "hour": "date_trunc('hour', detected_at)",
        "6h": "date_trunc('hour', detected_at) - "
              "(mod(EXTRACT(hour FROM detected_at)::int, 6) * interval '1 hour')",
        "day": "date_trunc('day', detected_at)",
    }
    trunc_expr = trunc_exprs[bucket_kind]

    params = {"stream_ids": stream_ids, "cutoff": cutoff}
    species_where = ""
    if species_filter:
        names = [s.strip() for s in species_filter.split(",") if s.strip()]
        if names:
            species_where = "AND common_name = ANY(:species_list)"
            params["species_list"] = names

    sql = f"""
        SELECT {trunc_expr} AS bucket,
               stream_id,
               COUNT(*) AS count
        FROM detections
        WHERE stream_id = ANY(:stream_ids)
          AND detected_at >= :cutoff
          {species_where}
        GROUP BY bucket, stream_id
        ORDER BY bucket
    """
    rows = db.session.execute(db.text(sql), params).fetchall()

    # Generate all buckets in the range so playback has continuous frames
    bucket_step = {"hour": timedelta(hours=1), "6h": timedelta(hours=6), "day": timedelta(days=1)}[bucket_kind]
    bucket_starts = []
    t = cutoff
    # Align to bucket boundary
    if bucket_kind == "hour":
        t = t.replace(minute=0, second=0, microsecond=0)
    elif bucket_kind == "6h":
        t = t.replace(minute=0, second=0, microsecond=0)
        t = t - timedelta(hours=t.hour % 6)
    else:
        t = t.replace(hour=0, minute=0, second=0, microsecond=0)

    now = datetime.now(timezone.utc)
    while t <= now:
        bucket_starts.append(t)
        t += bucket_step

    # Map of bucket → {stream_id: count}
    buckets_map: dict[datetime, dict[str, int]] = {b: {} for b in bucket_starts}
    for row in rows:
        b = row.bucket
        # Normalize: row.bucket should be timezone-aware
        if b.tzinfo is None:
            b = b.replace(tzinfo=timezone.utc)
        if b in buckets_map:
            buckets_map[b][str(row.stream_id)] = row.count

    buckets_out = [
        {"t": b.isoformat(), "counts": buckets_map[b]}
        for b in bucket_starts
    ]

    # Available species (for the filter UI)
    species_rows = db.session.execute(
        db.text("""
            SELECT common_name, COUNT(*) AS count
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND common_name IS NOT NULL
              AND detected_at >= :cutoff
            GROUP BY common_name
            ORDER BY count DESC
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    species_list = [{"name": r.common_name, "count": r.count} for r in species_rows]

    streams_out = [
        {
            "id": str(s.id),
            "name": s.name,
            "lat": s.latitude,
            "lng": s.longitude,
            "status": s.status,
            "location_name": s.location_name,
        }
        for s in streams if s.latitude and s.longitude
    ]

    return jsonify({
        "buckets": buckets_out,
        "streams": streams_out,
        "species": species_list,
        "bucket_kind": bucket_kind,
        "range": range_param,
    })


@analytics_bp.route("/projects/<uuid:project_id>/analytics/stream_stats", methods=["GET"])
def stream_stats(project_id):
    """Per-stream detection stats."""
    range_param = request.args.get("range", "7d")
    cutoff = _get_cutoff(range_param)
    stream_ids, streams = _get_stream_ids(project_id)

    if not stream_ids:
        return jsonify({"streams": []})

    result = db.session.execute(
        db.text("""
            SELECT stream_id, COUNT(*) AS count,
                   COUNT(DISTINCT common_name) AS unique_species,
                   MAX(detected_at) AS last_detection
            FROM detections
            WHERE stream_id = ANY(:stream_ids)
              AND (:cutoff IS NULL OR detected_at >= :cutoff)
            GROUP BY stream_id
        """),
        {"stream_ids": stream_ids, "cutoff": cutoff},
    )
    stats_map = {str(row.stream_id): {
        "count": row.count,
        "unique_species": row.unique_species,
        "last_detection": row.last_detection.isoformat() if row.last_detection else None,
    } for row in result}

    stream_stats = []
    for s in streams:
        sid = str(s.id)
        stats = stats_map.get(sid, {"count": 0, "unique_species": 0, "last_detection": None})
        stream_stats.append({
            "id": sid,
            "name": s.name,
            "status": s.status,
            "platform": s.platform,
            "location_name": s.location_name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "last_frame_at": s.last_frame_at.isoformat() if s.last_frame_at else None,
            **stats,
        })

    return jsonify({"streams": stream_stats})
