import uuid

from extensions import db
from sqlalchemy.dialects.postgresql import UUID


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="stopped")
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    streams = db.relationship("Stream", backref="project", cascade="all, delete-orphan")
    models = db.relationship("MLModel", backref="project", cascade="all, delete-orphan")
    notification_rules = db.relationship(
        "NotificationRule", backref="project", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "stream_count": len(self.streams) if self.streams else 0,
            "model_count": len(self.models) if self.models else 0,
        }
