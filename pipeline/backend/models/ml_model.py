import uuid

from extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB


SUPPORTED_FRAMEWORKS = [
    "yolov5",
    "yolov8",
    "yolov10",
    "yolo_nas",
    "speciesnet",
    "onnx",
    "tensorrt",
    "torchscript",
]


class MLModel(db.Model):
    __tablename__ = "models"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    name = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    framework = db.Column(db.String(50), nullable=False)
    class_names = db.Column(JSONB, default=list)
    input_size = db.Column(db.Integer, default=640)
    gpu_memory_mb = db.Column(db.Integer)
    precision = db.Column(db.String(10), default="fp16")
    file_size_bytes = db.Column(db.BigInteger)
    uploaded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    streams = db.relationship("Stream", backref="model", lazy="dynamic")

    @property
    def is_builtin(self):
        return self.project_id is None

    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "is_builtin": self.is_builtin,
            "name": self.name,
            "filename": self.filename,
            "framework": self.framework,
            "class_names": self.class_names or [],
            "input_size": self.input_size,
            "gpu_memory_mb": self.gpu_memory_mb,
            "precision": self.precision,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
