from __future__ import annotations

import logging

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class YOLODetector(BaseDetector):
    def __init__(self):
        self._model = None
        self._class_names: list[str] = []

    def load(self, model_path: str, **kwargs) -> None:
        from ultralytics import YOLO
        self._model = YOLO(model_path)
        names = self._model.names
        if isinstance(names, dict):
            self._class_names = list(names.values())
        else:
            self._class_names = list(names)
        logger.info("Loaded YOLO model from %s (%d classes)", model_path, len(self._class_names))

    def predict(self, image_path: str) -> list[DetectionResult]:
        if self._model is None:
            return []
        results = self._model(image_path, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxyn[0].tolist()
                detections.append(DetectionResult(
                    class_name=self._class_names[cls_id] if cls_id < len(self._class_names) else str(cls_id),
                    confidence=conf,
                    bbox_x1=x1, bbox_y1=y1, bbox_x2=x2, bbox_y2=y2,
                ))
        return detections

    def unload(self) -> None:
        self._model = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
