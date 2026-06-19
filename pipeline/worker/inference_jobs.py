"""Listen for inference job requests on Redis and return results."""
from __future__ import annotations

import json
import logging
import os
import threading

import redis.exceptions as redis_exc

from inference.model_pool import ModelPool
from inference.base import DetectionResult

logger = logging.getLogger(__name__)

INFERENCE_REQUEST_QUEUE = "inference:requests"
UPLOADS_DIR = "/data/frames/uploads"


def _run_inference(model_pool: ModelPool, job: dict) -> dict:
    """Run a single inference job and return the result dict."""
    model_id = job["model_id"]
    framework = job["framework"]
    model_path = job["model_path"]
    image_path = job["image_path"]

    if not os.path.exists(image_path):
        return {"error": f"Image not found: {image_path}"}

    try:
        detector = model_pool.get(model_id, framework, model_path)
        results: list[DetectionResult] = detector.predict(image_path)

        detections = []
        for r in results:
            detections.append({
                "class_name": r.class_name,
                "confidence": r.confidence,
                "bbox": {
                    "x1": r.bbox_x1,
                    "y1": r.bbox_y1,
                    "x2": r.bbox_x2,
                    "y2": r.bbox_y2,
                },
            })
        return {"detections": detections}

    except Exception as e:
        logger.exception("Inference failed for job %s", job.get("job_id"))
        return {"error": str(e)}


def start_inference_listener(redis_client, model_pool: ModelPool):
    """Start a background thread that listens for inference jobs on Redis."""

    def _listener():
        logger.info("Inference job listener started")
        while True:
            try:
                # BLPOP blocks until a job arrives (timeout then retry)
                result = redis_client.blpop(INFERENCE_REQUEST_QUEUE, timeout=2)
                if result is None:
                    continue

                _, raw = result
                job = json.loads(raw)
                job_id = job.get("job_id", "unknown")
                response_key = f"inference:result:{job_id}"

                logger.info("Processing inference job %s (model=%s)", job_id, job.get("framework"))
                result_data = _run_inference(model_pool, job)

                # Push result and set expiry so it doesn't linger
                redis_client.setex(response_key, 120, json.dumps(result_data))
                # Notify the backend that the result is ready
                redis_client.publish(f"inference:done:{job_id}", "done")

            except (redis_exc.TimeoutError, redis_exc.ConnectionError):
                # BLPOP timed out at the socket layer with no job — expected, just retry
                continue
            except Exception:
                logger.exception("Error in inference listener")

    thread = threading.Thread(target=_listener, daemon=True, name="inference-listener")
    thread.start()
    return thread
