from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from extensions import db
from models.detection import Detection
from models.stream import Stream

detections_bp = Blueprint("detections", __name__, url_prefix="/api/v1")


@detections_bp.route("/streams/<uuid:stream_id>/detections", methods=["GET"])
def list_detections(stream_id):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    query = (
        Detection.query.filter_by(stream_id=stream_id)
        .order_by(Detection.detected_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
    )
    detections = query.all()
    return jsonify([d.to_dict() for d in detections])


@detections_bp.route("/detections/<uuid:detection_id>", methods=["GET"])
def get_detection(detection_id):
    detection = db.session.get(Detection, detection_id)
    if not detection:
        return jsonify({"error": "Detection not found"}), 404
    return jsonify(detection.to_dict())


@detections_bp.route("/projects/<uuid:project_id>/detections", methods=["GET"])
def list_project_detections(project_id):
    """Paginated detection list for the whole project, with filters."""
    limit = min(request.args.get("limit", 60, type=int), 200)
    offset = request.args.get("offset", 0, type=int)
    species = request.args.get("species")  # comma-separated common_name list
    stream_id = request.args.get("stream_id")
    range_param = request.args.get("range")  # 24h / 7d / 30d
    min_conf = request.args.get("min_confidence", type=float)

    streams = Stream.query.filter_by(project_id=project_id).all()
    stream_ids = [s.id for s in streams]
    stream_name_map = {str(s.id): s.name for s in streams}

    if not stream_ids:
        return jsonify({"detections": [], "total": 0})

    query = Detection.query.filter(Detection.stream_id.in_(stream_ids))

    if stream_id:
        query = query.filter(Detection.stream_id == stream_id)

    if species:
        names = [s.strip() for s in species.split(",") if s.strip()]
        if names:
            query = query.filter(Detection.common_name.in_(names))

    if min_conf is not None:
        query = query.filter(Detection.confidence >= min_conf)

    if range_param:
        delta = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}.get(range_param)
        if delta:
            cutoff = datetime.now(timezone.utc) - delta
            query = query.filter(Detection.detected_at >= cutoff)

    total = query.count()
    rows = query.order_by(Detection.detected_at.desc()).offset(offset).limit(limit).all()

    detections = []
    for d in rows:
        item = d.to_dict()
        item["stream_name"] = stream_name_map.get(str(d.stream_id), "")
        detections.append(item)

    return jsonify({"detections": detections, "total": total, "limit": limit, "offset": offset})
