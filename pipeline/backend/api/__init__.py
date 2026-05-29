from flask import Flask


def register_blueprints(app: Flask):
    from api.health import health_bp
    from api.projects import projects_bp
    from api.streams import streams_bp
    from api.models_api import models_bp
    from api.detections import detections_bp
    from api.notifications import notifications_bp
    from api.analytics import analytics_bp
    from api.gpu import gpu_bp
    from api.export import export_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(streams_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(detections_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gpu_bp)
    app.register_blueprint(export_bp)
