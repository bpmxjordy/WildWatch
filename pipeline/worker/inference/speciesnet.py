from __future__ import annotations

import logging

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)

SPECIESNET_DEFAULT_MODEL = "kaggle:google/speciesnet/pyTorch/v4.0.2a/1"
SKIP_LABELS = {"blank", "person", "vehicle", "unknown"}


class SpeciesNetDetector(BaseDetector):
    def __init__(self):
        self._model = None
        self._class_names: list[str] = []

    def load(self, model_path: str, **kwargs) -> None:
        from speciesnet import SpeciesNet as SpeciesNetModel

        if not model_path or model_path == "built-in":
            model_path = SPECIESNET_DEFAULT_MODEL

        logger.info("Loading SpeciesNet model from %s (first run downloads ~420MB)...", model_path)
        self._model = SpeciesNetModel(model_path, components="all")
        logger.info("SpeciesNet model loaded successfully.")

    def predict(self, image_path: str, country_code: str | None = None) -> list[DetectionResult]:
        if self._model is None:
            return []

        try:
            result = self._model.predict(
                filepaths=[image_path],
                country=country_code,
                run_mode="single_thread",
                progress_bars=False,
            )
        except Exception:
            logger.exception("SpeciesNet inference failed")
            return []

        predictions = result.get("predictions", [])
        if not predictions:
            return []

        pred = predictions[0]
        label = pred.get("prediction", "")
        score = pred.get("prediction_score", 0)

        # Parse the top-level classification for species name
        parts = [p.strip() for p in label.split(";") if p.strip()]
        if not parts or parts[0].lower() in SKIP_LABELS:
            return []
        if any(skip in label.lower() for skip in SKIP_LABELS):
            return []

        common_name = parts[-1] if len(parts) > 1 else parts[0]
        common_name = " ".join(w.capitalize() for w in common_name.split())

        # Get ALL detections (bounding boxes) from the detector component
        dets = pred.get("detections", [])
        results = []

        if dets:
            for det in dets:
                det_label = det.get("label", "")
                det_conf = det.get("conf", 0)

                # Only keep animal detections
                if det_label and det_label != "animal":
                    continue

                bbox = det.get("bbox")
                if bbox:
                    x, y, w, h = bbox
                    results.append(DetectionResult(
                        class_name=common_name,
                        confidence=det_conf if det_conf > 0 else score,
                        bbox_x1=x,
                        bbox_y1=y,
                        bbox_x2=x + w,
                        bbox_y2=y + h,
                    ))
                else:
                    results.append(DetectionResult(
                        class_name=common_name,
                        confidence=det_conf if det_conf > 0 else score,
                        bbox_x1=0, bbox_y1=0, bbox_x2=1, bbox_y2=1,
                    ))
        else:
            # No detector output — return the classification as a full-frame detection
            results.append(DetectionResult(
                class_name=common_name,
                confidence=score,
                bbox_x1=0, bbox_y1=0, bbox_x2=1, bbox_y2=1,
            ))

        logger.debug("SpeciesNet found %d detection(s) in %s: %s",
                     len(results), image_path,
                     ", ".join(f"{r.class_name} ({r.confidence:.0%})" for r in results))

        return results

    def unload(self) -> None:
        self._model = None

    @property
    def class_names(self) -> list[str]:
        return self._class_names
