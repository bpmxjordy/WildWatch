from __future__ import annotations

import logging

import numpy as np
from PIL import Image

from inference.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class ONNXDetector(BaseDetector):
    def __init__(self):
        self._session = None
        self._class_names: list[str] = []
        self._input_size = 640
        self._is_classifier = False  # True if model outputs class logits, not bboxes

    def load(self, model_path: str, **kwargs) -> None:
        import onnxruntime as ort

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self._session = ort.InferenceSession(model_path, providers=providers)
        self._class_names = kwargs.get("class_names", [])

        # Auto-detect input size from model metadata
        inp = self._session.get_inputs()[0]
        input_shape = inp.shape  # e.g. [1, 3, 224, 224] or ['batch', 3, 640, 640]
        logger.info("ONNX model input: name=%s shape=%s dtype=%s", inp.name, input_shape, inp.type)

        # Extract H, W from shape (handle dynamic dims)
        h = input_shape[2] if len(input_shape) >= 4 and isinstance(input_shape[2], int) else None
        w = input_shape[3] if len(input_shape) >= 4 and isinstance(input_shape[3], int) else None

        if h and w:
            self._input_size = h  # assume square; use h
            logger.info("Auto-detected input size: %dx%d", h, w)
        else:
            # Dynamic dims — check if model name/architecture hints at ViT (expects 224)
            # ViT positional embeddings are fixed: 197 patches = (224/16)^2 + 1
            model_meta = self._session.get_modelmeta()
            desc = (model_meta.description or "").lower() + (model_meta.graph_name or "").lower()
            node_names = [n.name for n in self._session.get_outputs()] + [inp.name for inp in self._session.get_inputs()]
            all_text = desc + " ".join(node_names).lower()

            if "vit" in all_text or "vision_transformer" in all_text or "pixel_values" in all_text:
                self._input_size = kwargs.get("input_size", 224)
                logger.info("ViT model detected with dynamic dims, using input size: %d", self._input_size)
            else:
                self._input_size = kwargs.get("input_size", 640)
                logger.info("Using configured input size: %d", self._input_size)

        # Detect if this is a classifier (output is class logits) vs detector (output is bboxes)
        out = self._session.get_outputs()[0]
        out_shape = out.shape
        logger.info("ONNX model output: name=%s shape=%s", out.name, out_shape)

        # Classifiers typically output [1, num_classes] or [1, 1, num_classes]
        # Detectors output [1, num_detections, 6+] or [1, 6+, num_detections]
        if len(out_shape) == 2 or (len(out_shape) == 3 and isinstance(out_shape[-1], int) and out_shape[-1] < 20):
            self._is_classifier = True
            logger.info("Model detected as CLASSIFIER")
        else:
            self._is_classifier = False
            logger.info("Model detected as DETECTOR")

        logger.info("Loaded ONNX model from %s (%d classes)", model_path, len(self._class_names))

    def predict(self, image_path: str) -> list[DetectionResult]:
        if self._session is None:
            return []

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        img_resized = img.resize((self._input_size, self._input_size))
        arr = np.array(img_resized, dtype=np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)[np.newaxis, ...]

        input_name = self._session.get_inputs()[0].name

        try:
            outputs = self._session.run(None, {input_name: arr})
        except Exception as e:
            logger.error("ONNX inference failed: %s", e)
            return []

        if self._is_classifier:
            return self._parse_classifier_output(outputs)
        else:
            return self._parse_detector_output(outputs)

    def _parse_classifier_output(self, outputs) -> list[DetectionResult]:
        """Parse output from a classification model (e.g. ViT, ResNet)."""
        logits = outputs[0]
        if logits.ndim > 2:
            logits = logits.squeeze()
        if logits.ndim == 1:
            logits = logits[np.newaxis, :]

        # Softmax to get probabilities
        probs = logits[0]
        exp_probs = np.exp(probs - np.max(probs))
        probs = exp_probs / exp_probs.sum()

        # Get top predictions above threshold
        detections = []
        top_indices = np.argsort(probs)[::-1][:5]  # top 5
        for idx in top_indices:
            conf = float(probs[idx])
            if conf < 0.1:
                break
            class_name = self._class_names[idx] if idx < len(self._class_names) else str(idx)
            detections.append(DetectionResult(
                class_name=class_name,
                confidence=conf,
                bbox_x1=0.0, bbox_y1=0.0, bbox_x2=1.0, bbox_y2=1.0,  # full frame for classifiers
            ))

        return detections

    def _parse_detector_output(self, outputs) -> list[DetectionResult]:
        """Parse output from a detection model (e.g. YOLO-exported ONNX)."""
        detections = []
        if len(outputs) > 0:
            preds = outputs[0]
            if preds.ndim == 3:
                preds = preds[0]

            # Handle transposed output: some YOLO ONNX exports use [num_classes+4, num_detections]
            if preds.shape[0] < preds.shape[1] and preds.shape[0] < 100:
                preds = preds.T

            for row in preds:
                if len(row) >= 6:
                    x1, y1, x2, y2, conf, cls_id = row[:6]
                    if conf < 0.25:
                        continue
                    cls_id = int(cls_id)
                    detections.append(DetectionResult(
                        class_name=self._class_names[cls_id] if cls_id < len(self._class_names) else str(cls_id),
                        confidence=float(conf),
                        bbox_x1=float(x1 / self._input_size),
                        bbox_y1=float(y1 / self._input_size),
                        bbox_x2=float(x2 / self._input_size),
                        bbox_y2=float(y2 / self._input_size),
                    ))
                elif len(row) >= 5:
                    # Format: [x1, y1, x2, y2, class_scores...]
                    x1, y1, x2, y2 = row[:4]
                    class_scores = row[4:]
                    cls_id = int(np.argmax(class_scores))
                    conf = float(class_scores[cls_id])
                    if conf < 0.25:
                        continue
                    detections.append(DetectionResult(
                        class_name=self._class_names[cls_id] if cls_id < len(self._class_names) else str(cls_id),
                        confidence=conf,
                        bbox_x1=float(x1 / self._input_size),
                        bbox_y1=float(y1 / self._input_size),
                        bbox_x2=float(x2 / self._input_size),
                        bbox_y2=float(y2 / self._input_size),
                    ))
        return detections

    def unload(self) -> None:
        self._session = None
        self._class_names = []

    @property
    def class_names(self) -> list[str]:
        return self._class_names
