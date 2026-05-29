from __future__ import annotations

import logging

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class YOLOv5Detector(BaseDetector):
    def __init__(self):
        self._model = None
        self._class_names: list[str] = []

    def load(self, model_path: str, **kwargs) -> None:
        import torch
        self._model = torch.hub.load("ultralytics/yolov5", "custom", path=model_path, force_reload=False)
        self._class_names = list(self._model.names.values()) if isinstance(self._model.names, dict) else list(self._model.names)
        logger.info("Loaded YOLOv5 model from %s (%d classes)", model_path, len(self._class_names))

    def predict(self, image_path: str) -> list[DetectionResult]:
        if self._model is None:
            return []
        results = self._model(image_path)
        detections = []
        df = results.pandas().xyxyn[0]
        for _, row in df.iterrows():
            detections.append(DetectionResult(
                class_name=row["name"],
                confidence=float(row["confidence"]),
                bbox_x1=float(row["xmin"]),
                bbox_y1=float(row["ymin"]),
                bbox_x2=float(row["xmax"]),
                bbox_y2=float(row["ymax"]),
            ))
        return detections

    def unload(self) -> None:
        self._model = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
