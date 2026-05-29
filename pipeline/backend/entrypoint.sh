#!/bin/sh
set -e

echo "Running database migrations..."
flask db upgrade 2>/dev/null || python -c "
from app import create_app
from extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created via db.create_all()')
"

echo "Registering built-in models..."
python -c "
from app import create_app
from extensions import db
from models.ml_model import MLModel
app = create_app()
with app.app_context():
    existing = MLModel.query.filter_by(framework='speciesnet', filename='built-in').first()
    if not existing:
        m = MLModel(
            name='SpeciesNet v4 (Built-in)',
            filename='built-in',
            storage_path='built-in',
            framework='speciesnet',
            class_names=[],
            input_size=0,
            gpu_memory_mb=1500,
            precision='fp32',
            file_size_bytes=0,
            project_id=None,
        )
        db.session.add(m)
        db.session.commit()
        print('Registered SpeciesNet as built-in model')
    else:
        print('SpeciesNet already registered')
"

echo "Starting backend..."
exec python -c "from app import create_app; from extensions import socketio; app = create_app(); socketio.run(app, host='0.0.0.0', port=5000)"
