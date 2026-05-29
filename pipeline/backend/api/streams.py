import csv
import io
import urllib.request

from flask import Blueprint, jsonify, request

from extensions import db
from models.project import Project
from models.stream import Stream, SUPPORTED_PLATFORMS

streams_bp = Blueprint("streams", __name__, url_prefix="/api/v1")


@streams_bp.route("/projects/<uuid:project_id>/streams", methods=["GET"])
def list_streams(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    streams = Stream.query.filter_by(project_id=project_id).order_by(Stream.created_at.desc()).all()
    return jsonify([s.to_dict() for s in streams])


@streams_bp.route("/projects/<uuid:project_id>/streams", methods=["POST"])
def create_stream(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if not data or not data.get("name") or not data.get("source_url"):
        return jsonify({"error": "name and source_url are required"}), 400

    platform = data.get("platform", "youtube")
    if platform not in SUPPORTED_PLATFORMS:
        return jsonify({"error": f"Unsupported platform. Must be one of: {SUPPORTED_PLATFORMS}"}), 400

    tz = data.get("timezone")
    if not tz and data.get("latitude") is not None and data.get("longitude") is not None:
        try:
            from timezonefinder import TimezoneFinder
            tf = TimezoneFinder()
            tz = tf.timezone_at(lat=float(data["latitude"]), lng=float(data["longitude"]))
        except Exception:
            pass

    stream = Stream(
        project_id=project_id,
        name=data["name"],
        source_url=data["source_url"],
        platform=platform,
        location_name=data.get("location_name"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        timezone=tz,
        model_id=data.get("model_id"),
        active_classes=data.get("active_classes", []),
        min_confidence=data.get("min_confidence", 0.5),
        frame_interval_seconds=data.get("frame_interval_seconds", 60),
    )
    db.session.add(stream)
    db.session.commit()
    return jsonify(stream.to_dict()), 201


@streams_bp.route("/streams/<uuid:stream_id>", methods=["GET"])
def get_stream(stream_id):
    stream = db.session.get(Stream, stream_id)
    if not stream:
        return jsonify({"error": "Stream not found"}), 404
    return jsonify(stream.to_dict())


@streams_bp.route("/streams/<uuid:stream_id>", methods=["PUT"])
def update_stream(stream_id):
    stream = db.session.get(Stream, stream_id)
    if not stream:
        return jsonify({"error": "Stream not found"}), 404

    data = request.get_json()
    for field in ["name", "source_url", "platform", "location_name", "model_id",
                  "frame_interval_seconds", "is_active", "min_confidence"]:
        if field in data:
            setattr(stream, field, data[field])
    if "latitude" in data:
        stream.latitude = data["latitude"]
    if "longitude" in data:
        stream.longitude = data["longitude"]
    if "active_classes" in data:
        stream.active_classes = data["active_classes"]
    if "timezone" in data:
        stream.timezone = data["timezone"]

    db.session.commit()
    return jsonify(stream.to_dict())


@streams_bp.route("/streams/test-url", methods=["POST"])
def test_stream_url():
    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"reachable": False, "error": "No URL provided"}), 400
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WildSight/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            size = len(resp.read(4096))
        return jsonify({"reachable": True, "status": status, "content_type": content_type, "bytes_read": size})
    except Exception as e:
        return jsonify({"reachable": False, "error": str(e)})


@streams_bp.route("/projects/<uuid:project_id>/streams/import-csv", methods=["POST"])
def import_csv(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No CSV file provided"}), 400

    file = request.files["file"]
    content = file.stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    created = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        source_url = row.get("source_url", "").strip()
        platform = row.get("platform", "youtube").strip()

        if not name or not source_url:
            errors.append(f"Row {i}: missing name or source_url")
            continue
        if platform not in SUPPORTED_PLATFORMS:
            errors.append(f"Row {i}: unsupported platform '{platform}'")
            continue

        lat = row.get("latitude")
        lng = row.get("longitude")

        tz = row.get("timezone")
        if not tz and lat and lng:
            try:
                from timezonefinder import TimezoneFinder
                tf = TimezoneFinder()
                tz = tf.timezone_at(lat=float(lat), lng=float(lng))
            except Exception:
                pass

        stream = Stream(
            project_id=project_id,
            name=name,
            source_url=source_url,
            platform=platform,
            location_name=row.get("location_name", "").strip() or None,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            timezone=tz,
            frame_interval_seconds=int(row.get("frame_interval_seconds", 60)),
        )
        db.session.add(stream)
        created += 1

    db.session.commit()
    return jsonify({"created": created, "errors": errors}), 201


@streams_bp.route("/streams/<uuid:stream_id>", methods=["DELETE"])
def delete_stream(stream_id):
    stream = db.session.get(Stream, stream_id)
    if not stream:
        return jsonify({"error": "Stream not found"}), 404

    db.session.delete(stream)
    db.session.commit()
    return jsonify({"message": "Stream deleted"}), 200
