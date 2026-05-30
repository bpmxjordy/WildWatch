"""Single-image inference endpoint — upload an image and get detections."""
import os
import uuid

from flask import Blueprint, jsonify, request, current_app

from extensions import db
from models.ml_model import MLModel

inference_bp = Blueprint("inference", __name__, url_prefix="/api/v1")


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

    # Save uploaded image temporarily
    upload_dir = os.path.join(current_app.config["FRAMES_DIR"], "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    try:
        detections = _run_model(model, filepath)
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

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


def _run_model(model, image_path: str) -> list[dict]:
    framework = model.framework
    storage_path = model.storage_path

    if framework == "speciesnet":
        from speciesnet import SpeciesNet
        sn = SpeciesNet("kaggle:google/speciesnet/pyTorch/v4.0.2a/1", components="all")
        result = sn.predict(filepaths=[image_path], run_mode="single_thread", progress_bars=False)
        predictions = result.get("predictions", [])
        if not predictions:
            return []
        pred = predictions[0]
        label = pred.get("prediction", "")
        score = pred.get("prediction_score", 0)
        parts = [p.strip() for p in label.split(";") if p.strip()]
        if not parts or parts[0].lower() in ("blank", "person", "vehicle"):
            return []
        common_name = " ".join(w.capitalize() for w in parts[-1].split())
        dets = pred.get("detections", [])
        results = []
        for det in dets:
            if det.get("label") != "animal":
                continue
            bbox = det.get("bbox")
            if bbox:
                x, y, w, h = bbox
                results.append({
                    "class_name": common_name,
                    "confidence": det.get("conf", score),
                    "bbox": {"x1": x, "y1": y, "x2": x + w, "y2": y + h},
                })
        if not results and score > 0.3:
            results.append({
                "class_name": common_name,
                "confidence": score,
                "bbox": {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
            })
        return results

    elif framework in ("yolov5", "yolov8", "yolov10"):
        from ultralytics import YOLO
        yolo = YOLO(storage_path)
        results = yolo(image_path, verbose=False)
        names = yolo.names
        if isinstance(names, dict):
            names = list(names.values())
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxyn[0].tolist()
                detections.append({
                    "class_name": names[cls_id] if cls_id < len(names) else str(cls_id),
                    "confidence": conf,
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                })
        return detections

    else:
        return [{"class_name": "unsupported_framework", "confidence": 0, "bbox": None}]
