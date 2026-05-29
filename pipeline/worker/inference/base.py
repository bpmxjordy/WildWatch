from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float


class BaseDetector(ABC):
    @abstractmethod
    def load(self, model_path: str, **kwargs) -> None:
        ...

    @abstractmethod
    def predict(self, image_path: str) -> list[DetectionResult]:
        ...

    @abstractmethod
    def unload(self) -> None:
        ...

    @property
    @abstractmethod
    def class_names(self) -> list[str]:
        ...
