from flask import Blueprint, jsonify, request

from extensions import db
from models.detection import Detection

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
