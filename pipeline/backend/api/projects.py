from flask import Blueprint, jsonify, request

from extensions import db
from models.project import Project

projects_bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


@projects_bp.route("", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify([p.to_dict() for p in projects])


@projects_bp.route("", methods=["POST"])
def create_project():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    project = Project(
        name=data["name"],
        description=data.get("description", ""),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@projects_bp.route("/<uuid:project_id>", methods=["GET"])
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project.to_dict())


@projects_bp.route("/<uuid:project_id>", methods=["PUT"])
def update_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if data.get("name"):
        project.name = data["name"]
    if "description" in data:
        project.description = data["description"]
    if data.get("status") in ("stopped", "running", "error"):
        project.status = data["status"]

    db.session.commit()
    return jsonify(project.to_dict())


@projects_bp.route("/<uuid:project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"}), 200
