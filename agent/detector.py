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

    return {
        "category": category,
        "label": label,
        "confidence": result.get("prediction_score", 0),
        "prediction_source": result.get("prediction_source", ""),
        "detection_conf": det_conf,
        "bbox": top_detection.get("bbox"),
    }


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
