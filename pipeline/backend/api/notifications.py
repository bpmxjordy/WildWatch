from flask import Blueprint, jsonify, request

from extensions import db
from models.project import Project
from models.notification import NotificationRule

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1")


@notifications_bp.route("/projects/<uuid:project_id>/notifications", methods=["GET"])
def list_rules(project_id):
    rules = NotificationRule.query.filter_by(project_id=project_id).order_by(
        NotificationRule.created_at.desc()
    ).all()
    return jsonify([r.to_dict() for r in rules])


@notifications_bp.route("/projects/<uuid:project_id>/notifications", methods=["POST"])
def create_rule(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if not data or not data.get("channel") or not data.get("destination"):
        return jsonify({"error": "channel and destination are required"}), 400

    if data["channel"] not in ("email", "webhook", "browser"):
        return jsonify({"error": "channel must be email, webhook, or browser"}), 400

    rule = NotificationRule(
        project_id=project_id,
        stream_id=data.get("stream_id"),
        species_filter=data.get("species_filter", []),
        min_confidence=data.get("min_confidence", 0.5),
        channel=data["channel"],
        destination=data["destination"],
        cooldown_seconds=data.get("cooldown_seconds", 300),
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify(rule.to_dict()), 201


@notifications_bp.route("/notifications/<uuid:rule_id>", methods=["PUT"])
def update_rule(rule_id):
    rule = db.session.get(NotificationRule, rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    data = request.get_json()
    for field in ["species_filter", "min_confidence", "channel", "destination",
                  "cooldown_seconds", "is_active", "stream_id"]:
        if field in data:
            setattr(rule, field, data[field])

    db.session.commit()
    return jsonify(rule.to_dict())


@notifications_bp.route("/notifications/<uuid:rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    rule = db.session.get(NotificationRule, rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "Rule deleted"}), 200
