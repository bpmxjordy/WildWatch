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
