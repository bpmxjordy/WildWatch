import os
import uuid as uuid_mod

from flask import Blueprint, jsonify, request, current_app

from extensions import db
from models.project import Project
from models.ml_model import MLModel, SUPPORTED_FRAMEWORKS
from services.model_service import estimate_gpu_memory, extract_class_names

models_bp = Blueprint("models_api", __name__, url_prefix="/api/v1")


@models_bp.route("/projects/<uuid:project_id>/models", methods=["GET"])
def list_models(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    # Include both project-specific models AND built-in models (project_id is NULL)
    from sqlalchemy import or_
    models = MLModel.query.filter(
        or_(MLModel.project_id == project_id, MLModel.project_id.is_(None))
    ).order_by(MLModel.uploaded_at.desc()).all()
    return jsonify([m.to_dict() for m in models])


@models_bp.route("/projects/<uuid:project_id>/models", methods=["POST"])
def upload_model(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    allowed = current_app.config["ALLOWED_MODEL_EXTENSIONS"]
    if ext not in allowed:
        return jsonify({"error": f"File type {ext} not allowed. Allowed: {allowed}"}), 400

    framework = request.form.get("framework", "")
    if framework not in SUPPORTED_FRAMEWORKS:
        return jsonify({"error": f"Unsupported framework. Must be one of: {SUPPORTED_FRAMEWORKS}"}), 400

    model_id = uuid_mod.uuid4()
    model_dir = os.path.join(current_app.config["MODELS_DIR"], str(model_id))
    os.makedirs(model_dir, exist_ok=True)

    storage_path = os.path.join(model_dir, file.filename)
    file.save(storage_path)
    file_size = os.path.getsize(storage_path)

    class_names_input = request.form.get("class_names", "")
    if class_names_input:
        class_names = [c.strip() for c in class_names_input.split(",") if c.strip()]
    else:
        class_names = extract_class_names(storage_path, framework)

    precision = request.form.get("precision", "fp16")
    gpu_memory = estimate_gpu_memory(framework, file_size, precision)

    model = MLModel(
        id=model_id,
        project_id=project_id,
        name=request.form.get("name", file.filename),
        filename=file.filename,
        storage_path=storage_path,
        framework=framework,
        class_names=class_names,
        input_size=int(request.form.get("input_size", 640)),
        gpu_memory_mb=gpu_memory,
        precision=precision,
        file_size_bytes=file_size,
    )
    db.session.add(model)
    db.session.commit()
    return jsonify(model.to_dict()), 201


@models_bp.route("/models", methods=["GET"])
def list_all_models():
    models = MLModel.query.order_by(MLModel.uploaded_at.desc()).all()
    return jsonify([m.to_dict() for m in models])


@models_bp.route("/models/<uuid:model_id>", methods=["GET"])
def get_model(model_id):
    model = db.session.get(MLModel, model_id)
    if not model:
        return jsonify({"error": "Model not found"}), 404
    return jsonify(model.to_dict())


@models_bp.route("/models/<uuid:model_id>", methods=["DELETE"])
def delete_model(model_id):
    model = db.session.get(MLModel, model_id)
    if not model:
        return jsonify({"error": "Model not found"}), 404

    import shutil
    model_dir = os.path.dirname(model.storage_path)
    if os.path.isdir(model_dir):
        shutil.rmtree(model_dir)

    db.session.delete(model)
    db.session.commit()
    return jsonify({"message": "Model deleted"}), 200
