from flask import Blueprint, request, make_response, jsonify

from extensions import db
from models.project import Project
from services.export_service import generate_report

export_bp = Blueprint("export", __name__, url_prefix="/api/v1")


@export_bp.route("/projects/<uuid:project_id>/export", methods=["GET"])
def export_pdf(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    range_param = request.args.get("range", "7d")
    if range_param not in ("24h", "7d", "30d", "all"):
        range_param = "7d"

    try:
        pdf_bytes = generate_report(project, range_param)
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {e}"}), 500

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    filename = f"wildsight_{project.name.replace(' ', '_')}_{range_param}.pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
