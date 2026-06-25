from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SpeciesDetector:
    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from speciesnet import SpeciesNet as SpeciesNetModel
        logger.info("Loading SpeciesNet model (first run downloads ~420MB)...")
        self._model = SpeciesNetModel(
            "kaggle:google/speciesnet/pyTorch/v4.0.2a/1",
            components="all",
        )
        logger.info("SpeciesNet model loaded.")

    def predict(
        self, image_paths: list[str], country_code: str | None = None
    ) -> list[dict]:
        if not image_paths:
            return []

        self._load()
        try:
            result = self._model.predict(
                filepaths=image_paths,
                country=country_code,
                run_mode="single_thread",
                progress_bars=False,
            )
        except Exception:
            logger.exception("SpeciesNet inference failed")
            return []

        predictions = result.get("predictions", [])
        return predictions


def parse_prediction(result: dict) -> dict:
    label = result.get("prediction", "")
    parts = label.split(";") if label else []

    detections = result.get("detections", [])
    top_detection = detections[0] if detections else {}
    det_label = top_detection.get("label", "")
    det_conf = top_detection.get("conf", 0)

    if "blank" in label:
        category = "blank"
    elif det_label == "person" or "person" in label:
        category = "person"
    elif det_label == "vehicle" or "vehicle" in label:
        category = "vehicle"
    elif det_label == "animal" or len(parts) > 2:
        category = "animal"
    else:
        category = "blank"

    # Collect all animal detections with NMS to remove overlapping boxes
    animal_bboxes = []
    for det in detections:
        if det.get("label") == "animal" and det.get("bbox"):
            animal_bboxes.append({
                "bbox": det["bbox"],
                "conf": det.get("conf", 0),
            })
    animal_bboxes = _nms(animal_bboxes, iou_threshold=0.5)

    return {
        "category": category,
        "label": label,
        "confidence": result.get("prediction_score", 0),
        "prediction_source": result.get("prediction_source", ""),
        "detection_conf": det_conf,
        "bbox": top_detection.get("bbox"),
        "all_animal_bboxes": animal_bboxes,
    }


def _iou(box_a: list, box_b: list) -> float:
    """Compute IoU between two [x, y, w, h] boxes."""
    ax1, ay1 = box_a[0], box_a[1]
    ax2, ay2 = ax1 + box_a[2], ay1 + box_a[3]
    bx1, by1 = box_b[0], box_b[1]
    bx2, by2 = bx1 + box_b[2], by1 + box_b[3]

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = box_a[2] * box_a[3]
    area_b = box_b[2] * box_b[3]
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def _nms(detections: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Non-Maximum Suppression: keep only the highest-confidence non-overlapping boxes."""
    if not detections:
        return []
    dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    keep = []
    for det in dets:
        if all(_iou(det["bbox"], k["bbox"]) < iou_threshold for k in keep):
            keep.append(det)
    return keep


def extract_common_name(label: str | None) -> str | None:
    if not label:
        return None
    parts = [p.strip() for p in label.split(";") if p.strip()]
    if not parts:
        return None
    name = parts[-1]
    if name == "blank" or len(name) < 2:
        return None
    return " ".join(w.capitalize() for w in name.split())
