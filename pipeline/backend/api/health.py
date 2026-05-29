from flask import Blueprint, jsonify

from extensions import db, redis_client

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/v1/health")
def health():
    checks = {"api": "ok"}

    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        if redis_client:
            redis_client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not configured"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    healthy = all(v == "ok" for v in checks.values())
    return jsonify({"status": "healthy" if healthy else "degraded", "checks": checks}), (
        200 if healthy else 503
    )
