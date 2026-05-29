from __future__ import annotations

import logging

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class YOLONASDetector(BaseDetector):
    def __init__(self):
        self._model = None
        self._class_names: list[str] = []

    def load(self, model_path: str, **kwargs) -> None:
        from super_gradients.training import models as sg_models
        import torch

        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        arch = kwargs.get("arch", "yolo_nas_s")
        num_classes = kwargs.get("num_classes", len(checkpoint.get("net", {}).get("heads", {}).get("class_names", [])))

        self._model = sg_models.get(arch, num_classes=num_classes, checkpoint_path=model_path)
        self._class_names = kwargs.get("class_names", [])
        logger.info("Loaded YOLO-NAS model from %s", model_path)

    def predict(self, image_path: str) -> list[DetectionResult]:
        if self._model is None:
            return []
        predictions = self._model.predict(image_path, conf=0.25)
        detections = []
        for pred in predictions:
            bboxes = pred.prediction.bboxes_xyxy
            confs = pred.prediction.confidence
            labels = pred.prediction.labels
            h, w = pred.image.shape[:2]
            for bbox, conf, label in zip(bboxes, confs, labels):
                x1, y1, x2, y2 = bbox
                cls_id = int(label)
                detections.append(DetectionResult(
                    class_name=self._class_names[cls_id] if cls_id < len(self._class_names) else str(cls_id),
                    confidence=float(conf),
                    bbox_x1=float(x1 / w), bbox_y1=float(y1 / h),
                    bbox_x2=float(x2 / w), bbox_y2=float(y2 / h),
                ))
        return detections

    def unload(self) -> None:
        self._model = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
