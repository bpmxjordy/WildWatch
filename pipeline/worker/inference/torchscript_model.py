from __future__ import annotations

import logging

import numpy as np
from PIL import Image

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class TorchScriptDetector(BaseDetector):
    def __init__(self):
        self._model = None
        self._class_names: list[str] = []
        self._input_size = 640

    def load(self, model_path: str, **kwargs) -> None:
        import torch
        self._model = torch.jit.load(model_path)
        self._model.eval()
        self._class_names = kwargs.get("class_names", [])
        self._input_size = kwargs.get("input_size", 640)
        logger.info("Loaded TorchScript model from %s", model_path)

    def predict(self, image_path: str) -> list[DetectionResult]:
        if self._model is None:
            return []

        import torch

        img = Image.open(image_path).convert("RGB")
        img_resized = img.resize((self._input_size, self._input_size))
        arr = np.array(img_resized, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0)

        with torch.no_grad():
            output = self._model(tensor)

        if isinstance(output, torch.Tensor):
            preds = output.squeeze(0).cpu().numpy()
            detections = []
            for row in preds:
                if len(row) >= 6 and row[4] >= 0.25:
                    x1, y1, x2, y2, conf, cls_id = row[:6]
                    cls_id = int(cls_id)
                    detections.append(DetectionResult(
                        class_name=self._class_names[cls_id] if cls_id < len(self._class_names) else str(cls_id),
                        confidence=float(conf),
                        bbox_x1=float(x1 / self._input_size),
                        bbox_y1=float(y1 / self._input_size),
                        bbox_x2=float(x2 / self._input_size),
                        bbox_y2=float(y2 / self._input_size),
                    ))
            return detections
        return []

    def unload(self) -> None:
        self._model = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
