import json

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    api = app.config["BACKEND_URL"]

    @app.template_filter("api_url")
    def api_url_filter(path):
        return f"{api}{path}"

    @app.context_processor
    def inject_backend_url():
        # Public URL for browser JS to call the backend API directly
        return {"backend_url": app.config.get("BACKEND_PUBLIC_URL", "http://localhost:5000")}

    # ── Project routes ─────────────────────────────────
    @app.route("/")
    def index():
        resp = requests.get(f"{api}/api/v1/projects", timeout=5)
        projects = resp.json() if resp.ok else []
        return render_template("projects/list.html", projects=projects)

    @app.route("/projects/new", methods=["GET", "POST"])
    def project_create():
        if request.method == "POST":
            data = {
                "name": request.form["name"],
                "description": request.form.get("description", ""),
            }
            resp = requests.post(f"{api}/api/v1/projects", json=data, timeout=5)
            if resp.ok:
                project = resp.json()
                return redirect(url_for("project_overview", project_id=project["id"]))
            flash("Failed to create project", "error")
        return render_template("projects/create.html")

    @app.route("/projects/<project_id>")
    def project_overview(project_id):
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        streams = requests.get(f"{api}/api/v1/projects/{project_id}/streams", timeout=5).json()
        models = requests.get(f"{api}/api/v1/projects/{project_id}/models", timeout=5).json()
        return render_template(
            "projects/overview.html", project=project, streams=streams, models=models
        )

    @app.route("/projects/<project_id>/edit", methods=["GET", "POST"])
    def project_edit(project_id):
        if request.method == "POST":
            data = {
                "name": request.form["name"],
                "description": request.form.get("description", ""),
            }
            requests.put(f"{api}/api/v1/projects/{project_id}", json=data, timeout=5)
            return redirect(url_for("project_overview", project_id=project_id))
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        return render_template("projects/edit.html", project=project)

    @app.route("/projects/<project_id>/delete", methods=["POST"])
    def project_delete(project_id):
        requests.delete(f"{api}/api/v1/projects/{project_id}", timeout=5)
        return redirect(url_for("index"))

    @app.route("/projects/<project_id>/toggle", methods=["POST"])
    def project_toggle(project_id):
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        new_status = "stopped" if project["status"] == "running" else "running"
        requests.put(
            f"{api}/api/v1/projects/{project_id}",
            json={"status": new_status},
            timeout=5,
        )
        return redirect(url_for("project_overview", project_id=project_id))

    # ── Stream routes ──────────────────────────────────
    @app.route("/projects/<project_id>/streams/new", methods=["GET", "POST"])
    def stream_add(project_id):
        if request.method == "POST":
            min_conf_pct = int(request.form.get("min_confidence", 50))
            data = {
                "name": request.form["name"],
                "source_url": request.form["source_url"],
                "platform": request.form["platform"],
                "location_name": request.form.get("location_name", ""),
                "frame_interval_seconds": int(request.form.get("frame_interval", 60)),
                "min_confidence": min_conf_pct / 100.0,
            }
            lat = request.form.get("latitude")
            lng = request.form.get("longitude")
            if lat and lng:
                data["latitude"] = float(lat)
                data["longitude"] = float(lng)
            model_id = request.form.get("model_id")
            if model_id:
                data["model_id"] = model_id

            resp = requests.post(
                f"{api}/api/v1/projects/{project_id}/streams", json=data, timeout=5
            )
            if resp.ok:
                return redirect(url_for("project_overview", project_id=project_id))
            flash("Failed to add stream", "error")

        models = requests.get(f"{api}/api/v1/projects/{project_id}/models", timeout=5).json()
        return render_template("streams/add.html", project_id=project_id, models=models)

    @app.route("/streams/<stream_id>")
    def stream_detail(stream_id):
        stream = requests.get(f"{api}/api/v1/streams/{stream_id}", timeout=5).json()
        detections = requests.get(
            f"{api}/api/v1/streams/{stream_id}/detections?limit=50", timeout=5
        ).json()
        return render_template("streams/detail.html", stream=stream, detections=detections)

    @app.route("/streams/<stream_id>/edit", methods=["GET"])
    def stream_edit(stream_id):
        stream = requests.get(f"{api}/api/v1/streams/{stream_id}", timeout=5).json()
        project_id = stream["project_id"]
        models = requests.get(f"{api}/api/v1/projects/{project_id}/models", timeout=5).json()
        return render_template(
            "streams/edit.html",
            stream=stream,
            models=models,
            models_json=json.dumps(models),
        )

    @app.route("/streams/<stream_id>/delete", methods=["POST"])
    def stream_delete(stream_id):
        stream = requests.get(f"{api}/api/v1/streams/{stream_id}", timeout=5).json()
        project_id = stream["project_id"]
        requests.delete(f"{api}/api/v1/streams/{stream_id}", timeout=5)
        return redirect(url_for("project_overview", project_id=project_id))

    # ── Model routes ───────────────────────────────────
    @app.route("/projects/<project_id>/models/upload", methods=["GET", "POST"])
    def model_upload(project_id):
        if request.method == "POST":
            file = request.files.get("file")
            if not file:
                flash("No file selected", "error")
                return redirect(request.url)

            files = {"file": (file.filename, file.stream, file.content_type)}
            form_data = {
                "name": request.form.get("name", file.filename),
                "framework": request.form["framework"],
                "precision": request.form.get("precision", "fp16"),
                "input_size": request.form.get("input_size", "640"),
                "class_names": request.form.get("class_names", ""),
            }
            resp = requests.post(
                f"{api}/api/v1/projects/{project_id}/models",
                files=files,
                data=form_data,
                timeout=120,
            )
            if resp.ok:
                return redirect(url_for("project_overview", project_id=project_id))
            flash("Failed to upload model", "error")

        return render_template("models/upload.html", project_id=project_id)

    @app.route("/models/<model_id>/delete", methods=["POST"])
    def model_delete(model_id):
        model = requests.get(f"{api}/api/v1/models/{model_id}", timeout=5).json()
        project_id = model["project_id"]
        requests.delete(f"{api}/api/v1/models/{model_id}", timeout=5)
        return redirect(url_for("project_overview", project_id=project_id))

    # ── Analytics routes ──────────────────────────────
    @app.route("/projects/<project_id>/analytics")
    def project_analytics(project_id):
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        return render_template("analytics/dashboard.html", project=project)

    # ── Notification routes ─────────────────────────────
    @app.route("/projects/<project_id>/notifications")
    def project_notifications(project_id):
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        streams = requests.get(f"{api}/api/v1/projects/{project_id}/streams", timeout=5).json()
        return render_template("notifications/rules.html", project=project, streams=streams)

    # ── Map routes ────────────────────────────────────
    @app.route("/projects/<project_id>/map")
    def project_map(project_id):
        project = requests.get(f"{api}/api/v1/projects/{project_id}", timeout=5).json()
        streams = requests.get(f"{api}/api/v1/projects/{project_id}/streams", timeout=5).json()
        return render_template(
            "map/view.html",
            project=project,
            streams_json=json.dumps(streams),
        )

    return app
