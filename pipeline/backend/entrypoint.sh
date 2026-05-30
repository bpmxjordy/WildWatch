#!/bin/sh
set -e

echo "Running database migrations..."
python -c "
from app import create_app
from extensions import db
# Import all models so SQLAlchemy knows about them
from models.project import Project
from models.stream import Stream
from models.ml_model import MLModel
from models.detection import Detection
from models.notification import NotificationRule
from models.gpu import GPUDevice

app = create_app()
with app.app_context():
    db.create_all()
    print('All tables created successfully')
"

echo "Registering built-in models..."
python -c "
from app import create_app
from extensions import db
from models.ml_model import MLModel
app = create_app()
with app.app_context():
    # SpeciesNet v4
    if not MLModel.query.filter_by(framework='speciesnet', filename='built-in').first():
        db.session.add(MLModel(
            name='SpeciesNet v4 (Built-in)',
            filename='built-in', storage_path='built-in',
            framework='speciesnet', class_names=[],
            input_size=0, gpu_memory_mb=1500, precision='fp32',
            file_size_bytes=0, project_id=None,
        ))
        print('Registered SpeciesNet v4')
    # Kea Detector v2 (YOLO11m)
    if not MLModel.query.filter_by(name='Kea Detector v2 (Built-in)').first():
        db.session.add(MLModel(
            name='Kea Detector v2 (Built-in)',
            filename='built-in', storage_path='/data/models/kea_detector_v2/best.pt',
            framework='yolov8', class_names=['kea'],
            input_size=640, gpu_memory_mb=200, precision='fp16',
            file_size_bytes=40500000, project_id=None,
        ))
        print('Registered Kea Detector v2')
    db.session.commit()
    print('Built-in models ready')
"

echo "Starting backend..."
exec python -c "from app import create_app; from extensions import socketio; app = create_app(); socketio.run(app, host='0.0.0.0', port=5000)"
