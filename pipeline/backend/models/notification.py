import uuid

from extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB


class NotificationRule(db.Model):
    __tablename__ = "notification_rules"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    stream_id = db.Column(UUID(as_uuid=True), db.ForeignKey("streams.id"), nullable=True)
    species_filter = db.Column(JSONB, default=list)
    min_confidence = db.Column(db.Float, default=0.5)
    channel = db.Column(db.String(30), nullable=False)
    destination = db.Column(db.Text, nullable=False)
    cooldown_seconds = db.Column(db.Integer, default=300)
    is_active = db.Column(db.Boolean, default=True)
    last_triggered_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    stream = db.relationship("Stream", foreign_keys=[stream_id])

    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "stream_id": str(self.stream_id) if self.stream_id else None,
            "species_filter": self.species_filter or [],
            "min_confidence": self.min_confidence,
            "channel": self.channel,
            "destination": self.destination,
            "cooldown_seconds": self.cooldown_seconds,
            "is_active": self.is_active,
            "last_triggered_at": self.last_triggered_at.isoformat()
            if self.last_triggered_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
