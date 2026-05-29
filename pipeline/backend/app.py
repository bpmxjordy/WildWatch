import logging
import os

from flask import Flask, jsonify, send_from_directory

from config import Config
from extensions import db, migrate, socketio, cors, csrf, limiter, init_redis


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    csrf.init_app(app)
    limiter.init_app(app)
    init_redis(app)

    csrf.exempt("api")

    os.makedirs(app.config["MODELS_DIR"], exist_ok=True)
    os.makedirs(app.config["FRAMES_DIR"], exist_ok=True)
    os.makedirs(app.config["EXPORTS_DIR"], exist_ok=True)

    from api import register_blueprints
    register_blueprints(app)

    # Serve frame images from /data/frames/
    @app.route("/frames/<path:filename>")
    def serve_frame(filename):
        return send_from_directory(app.config["FRAMES_DIR"], filename)

    # Worker log buffer endpoint
    @app.route("/api/v1/logs/worker")
    def worker_log_buffer():
        from extensions import redis_client as rc
        if not rc:
            return jsonify({"lines": []})
        lines = rc.lrange("worker:log_buffer", 0, -1)
        return jsonify({"lines": [l.decode("utf-8", errors="replace") if isinstance(l, bytes) else l for l in lines]})

    # WebSocket: subscribe to live detection events
    @socketio.on("connect")
    def handle_connect():
        pass

    @socketio.on("subscribe_project")
    def handle_subscribe(data):
        from flask_socketio import join_room
        project_id = data.get("project_id")
        if project_id:
            join_room(f"project_{project_id}")

    @socketio.on("subscribe_logs")
    def handle_subscribe_logs(data=None):
        """Stream worker logs to the client via WebSocket."""
        import threading
        from extensions import redis_client as rc
        if not rc:
            return

        def _stream_logs():
            pubsub = rc.pubsub()
            pubsub.subscribe("worker:logs")
            for message in pubsub.listen():
                if message["type"] == "message":
                    line = message["data"]
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="replace")
                    socketio.emit("log_line", {"line": line})

        t = threading.Thread(target=_stream_logs, daemon=True)
        t.start()

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Validation error", "details": str(e)}), 422

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
