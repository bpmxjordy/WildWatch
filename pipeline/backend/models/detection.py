import uuid

from extensions import db
from sqlalchemy.dialects.postgresql import UUID


class Detection(db.Model):
    __tablename__ = "detections"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("streams.id", ondelete="CASCADE"), nullable=False
    )
    species_label = db.Column(db.String(200))
    common_name = db.Column(db.String(200))
    confidence = db.Column(db.Float)
    bbox_x1 = db.Column(db.Float)
    bbox_y1 = db.Column(db.Float)
    bbox_x2 = db.Column(db.Float)
    bbox_y2 = db.Column(db.Float)
    thumbnail_path = db.Column(db.String(500))
    frame_path = db.Column(db.String(500))
    detected_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "stream_id": str(self.stream_id),
            "species_label": self.species_label,
            "common_name": self.common_name,
            "confidence": self.confidence,
            "bbox": {
                "x1": self.bbox_x1,
                "y1": self.bbox_y1,
                "x2": self.bbox_x2,
                "y2": self.bbox_y2,
            }
            if self.bbox_x1 is not None
            else None,
            "thumbnail_path": self.thumbnail_path,
            "frame_path": self.frame_path,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }
