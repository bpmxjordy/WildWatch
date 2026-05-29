import uuid

from extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB


SUPPORTED_PLATFORMS = ["youtube", "rtsp", "hls", "mjpeg", "jpeg"]


class Stream(db.Model):
    __tablename__ = "streams"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    source_url = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(30), nullable=False)
    location_name = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timezone = db.Column(db.String(50))
    model_id = db.Column(UUID(as_uuid=True), db.ForeignKey("models.id"), nullable=True)
    active_classes = db.Column(JSONB, default=list)
    min_confidence = db.Column(db.Float, default=0.5)
    frame_interval_seconds = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="idle")
    last_frame_at = db.Column(db.DateTime(timezone=True))
    consecutive_failures = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    detections = db.relationship(
        "Detection", backref="stream", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "source_url": self.source_url,
            "platform": self.platform,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "model_id": str(self.model_id) if self.model_id else None,
            "active_classes": self.active_classes or [],
            "min_confidence": self.min_confidence or 0.5,
            "frame_interval_seconds": self.frame_interval_seconds,
            "is_active": self.is_active,
            "status": self.status,
            "last_frame_at": self.last_frame_at.isoformat() if self.last_frame_at else None,
            "consecutive_failures": self.consecutive_failures,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
