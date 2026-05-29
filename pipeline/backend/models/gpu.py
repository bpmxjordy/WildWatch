from extensions import db


class GPUDevice(db.Model):
    __tablename__ = "gpu_inventory"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_index = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    total_memory_mb = db.Column(db.Integer, nullable=False)
    compute_capability = db.Column(db.String(20))
    detected_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "device_index": self.device_index,
            "name": self.name,
            "total_memory_mb": self.total_memory_mb,
            "compute_capability": self.compute_capability,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }
