from __future__ import annotations

import logging

from inference.base import BaseDetector

logger = logging.getLogger(__name__)

FRAMEWORK_MAP = {
    "yolov5": "inference.yolov5:YOLOv5Detector",
    "yolov8": "inference.yolo:YOLODetector",
    "yolov10": "inference.yolo:YOLODetector",
    "yolo_nas": "inference.yolo_nas:YOLONASDetector",
    "speciesnet": "inference.speciesnet:SpeciesNetDetector",
    "onnx": "inference.onnx_model:ONNXDetector",
    "tensorrt": "inference.tensorrt_model:TensorRTDetector",
    "torchscript": "inference.torchscript_model:TorchScriptDetector",
}


def _import_detector(dotted_path: str) -> type[BaseDetector]:
    module_path, class_name = dotted_path.rsplit(":", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ModelPool:
    def __init__(self):
        self._loaded: dict[str, BaseDetector] = {}

    def get(self, model_id: str, framework: str, model_path: str, **kwargs) -> BaseDetector:
        if model_id in self._loaded:
            return self._loaded[model_id]

        dotted = FRAMEWORK_MAP.get(framework)
        if not dotted:
            raise ValueError(f"Unsupported framework: {framework}")

        detector_cls = _import_detector(dotted)
        detector = detector_cls()
        detector.load(model_path, **kwargs)
        self._loaded[model_id] = detector
        logger.info("Loaded model %s (%s) into pool", model_id, framework)
        return detector

    def unload(self, model_id: str) -> None:
        detector = self._loaded.pop(model_id, None)
        if detector:
            detector.unload()
            logger.info("Unloaded model %s from pool", model_id)

    def unload_all(self) -> None:
        for model_id in list(self._loaded.keys()):
            self.unload(model_id)

    @property
    def loaded_ids(self) -> list[str]:
        return list(self._loaded.keys())
