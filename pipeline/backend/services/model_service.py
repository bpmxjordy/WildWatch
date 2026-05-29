import logging
import os

logger = logging.getLogger(__name__)

GPU_MEMORY_ESTIMATES = {
    "yolov5": {"fp16": 50, "fp32": 100, "multiplier": 1.0},
    "yolov8": {"fp16": 50, "fp32": 100, "multiplier": 1.0},
    "yolov10": {"fp16": 50, "fp32": 100, "multiplier": 1.0},
    "yolo_nas": {"fp16": 80, "fp32": 160, "multiplier": 1.2},
    "speciesnet": {"fp16": 1500, "fp32": 1500, "multiplier": 1.0},
    "onnx": {"fp16": 0, "fp32": 0, "multiplier": 2.5},
    "tensorrt": {"fp16": 0, "fp32": 0, "multiplier": 1.5},
    "torchscript": {"fp16": 0, "fp32": 0, "multiplier": 2.0},
}

YOLO_SIZE_TIERS = {
    5_000_000: ("nano", 50, 100),
    20_000_000: ("small", 80, 160),
    50_000_000: ("medium", 200, 400),
    100_000_000: ("large", 400, 800),
    float("inf"): ("xlarge", 700, 1400),
}


def estimate_gpu_memory(framework: str, file_size_bytes: int, precision: str = "fp16") -> int:
    estimates = GPU_MEMORY_ESTIMATES.get(framework, {"fp16": 0, "fp32": 0, "multiplier": 2.5})

    if framework in ("yolov5", "yolov8", "yolov10"):
        for threshold, (tier, fp16_mb, fp32_mb) in YOLO_SIZE_TIERS.items():
            if file_size_bytes <= threshold:
                return fp16_mb if precision == "fp16" else fp32_mb
        return 700

    base = estimates.get(precision, estimates["fp16"])
    if base > 0:
        return base

    file_size_mb = file_size_bytes / (1024 * 1024)
    return int(file_size_mb * estimates["multiplier"])


def extract_class_names(file_path: str, framework: str) -> list[str]:
    if framework in ("yolov5", "yolov8", "yolov10"):
        try:
            import torch
            data = torch.load(file_path, map_location="cpu", weights_only=False)
            if isinstance(data, dict):
                model_data = data.get("model", data)
                if hasattr(model_data, "names"):
                    names = model_data.names
                    if isinstance(names, dict):
                        return list(names.values())
                    return list(names)
                if "names" in data:
                    names = data["names"]
                    if isinstance(names, dict):
                        return list(names.values())
                    return list(names)
        except Exception as e:
            logger.warning("Failed to extract class names from %s: %s", file_path, e)
    return []
