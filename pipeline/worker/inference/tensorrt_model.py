from __future__ import annotations

import logging

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class TensorRTDetector(BaseDetector):
    def __init__(self):
        self._class_names: list[str] = []
        self._engine = None
        self._context = None

    def load(self, model_path: str, **kwargs) -> None:
        try:
            import tensorrt as trt

            trt_logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(trt_logger)
            with open(model_path, "rb") as f:
                self._engine = runtime.deserialize_cuda_engine(f.read())
            self._context = self._engine.create_execution_context()
            self._class_names = kwargs.get("class_names", [])
            logger.info("Loaded TensorRT engine from %s", model_path)
        except ImportError:
            logger.error("TensorRT not installed — cannot load .engine files")
            raise

    def predict(self, image_path: str) -> list[DetectionResult]:
        logger.warning("TensorRT predict not yet fully implemented — returning empty")
        return []

    def unload(self) -> None:
        self._context = None
        self._engine = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
