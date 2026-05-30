"""Single-image inference endpoint — upload an image, route to worker via Redis."""
import json
import os
import uuid

from flask import Blueprint, jsonify, request, current_app

from extensions import db, redis_client
from models.ml_model import MLModel

inference_bp = Blueprint("inference", __name__, url_prefix="/api/v1")

INFERENCE_REQUEST_QUEUE = "inference:requests"
INFERENCE_TIMEOUT = 60  # seconds to wait for worker result


@inference_bp.route("/inference", methods=["POST"])
def run_inference():
    if "file" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["file"]
    model_id = request.form.get("model_id")
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400

    model = db.session.get(MLModel, model_id)
    if not model:
        return jsonify({"error": "Model not found"}), 404

    if not redis_client:
        return jsonify({"error": "Redis not available — cannot reach worker"}), 503

    # Save uploaded image to shared volume
    upload_dir = os.path.join(current_app.config["FRAMES_DIR"], "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Create inference job
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "model_id": str(model.id),
        "framework": model.framework,
        "model_path": model.storage_path,
        "image_path": filepath,
    }

    # Push job to Redis queue
    redis_client.rpush(INFERENCE_REQUEST_QUEUE, json.dumps(job))

    # Wait for result from worker
    response_key = f"inference:result:{job_id}"
    channel = f"inference:done:{job_id}"

    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)

    try:
        import time
        deadline = time.time() + INFERENCE_TIMEOUT
        while time.time() < deadline:
            # Check if result already arrived
            if redis_client.exists(response_key):
                break
            msg = pubsub.get_message(timeout=2.0)
            if msg and msg["type"] == "message":
                break
        else:
            return jsonify({"error": "Inference timed out — worker may be busy"}), 504
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()

    raw = redis_client.get(response_key)
    if not raw:
        return jsonify({"error": "No result from worker"}), 504

    result = json.loads(raw)
    redis_client.delete(response_key)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    detections = result.get("detections", [])

    # Generate annotated image
    annotated_filename = f"{uuid.uuid4()}_annotated.jpg"
    annotated_path = os.path.join(upload_dir, annotated_filename)

    if detections:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.open(filepath).convert("RGB")
            draw = ImageDraw.Draw(img)
            w, h = img.size
            colors = [
                (46, 125, 50), (0, 121, 107), (21, 101, 192), (106, 27, 154),
                (173, 20, 87), (230, 81, 0), (62, 39, 35), (38, 50, 56),
            ]
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except (OSError, IOError):
                font = ImageFont.load_default()

            for i, det in enumerate(detections):
                color = colors[i % len(colors)]
                x1 = int(det["bbox"]["x1"] * w)
                y1 = int(det["bbox"]["y1"] * h)
                x2 = int(det["bbox"]["x2"] * w)
                y2 = int(det["bbox"]["y2"] * h)
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                label = f"{det['class_name']} {det['confidence']:.0%}"
                bbox = font.getbbox(label)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                ly = max(y1 - th - 6, 0)
                draw.rectangle([x1, ly, x1 + tw + 8, ly + th + 6], fill=color)
                draw.text((x1 + 4, ly + 2), label, fill="white", font=font)
            img.save(annotated_path, quality=90)
        except Exception:
            annotated_filename = filename
    else:
        annotated_filename = filename

    return jsonify({
        "detections": detections,
        "image_url": f"/frames/uploads/{filename}",
        "annotated_url": f"/frames/uploads/{annotated_filename}",
        "model": model.to_dict(),
    })
