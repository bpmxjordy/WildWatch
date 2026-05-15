from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class SpeciesDetector:
    def predict(
        self, image_paths: list[str], country_code: str | None = None
    ) -> list[dict]:
        if not image_paths:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            for p in image_paths:
                shutil.copy(p, tmpdir)

            predictions_path = os.path.join(tmpdir, "predictions.json")
            cmd = [
                "python",
                "-m",
                "speciesnet.scripts.run_model",
                "--folders",
                tmpdir,
                "--predictions_json",
                predictions_path,
            ]
            if country_code:
                cmd.extend(["--country", country_code])

            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            except subprocess.CalledProcessError as e:
                logger.error(
                    "SpeciesNet failed: %s", e.stderr.decode(errors="replace")[:300]
                )
                return []
            except subprocess.TimeoutExpired:
                logger.error("SpeciesNet timed out")
                return []

            if not os.path.exists(predictions_path):
                logger.error("SpeciesNet did not produce predictions.json")
                return []

            with open(predictions_path) as f:
                data = json.load(f)

            predictions = []
            for filepath, result in data.items():
                if filepath == "predictions":
                    continue
                predictions.append(result)
            return predictions


def extract_common_name(label: str | None) -> str | None:
    if not label:
        return None
    parts = label.split(";")
    name = parts[-1].strip() if parts else None
    if not name:
        return None
    return " ".join(w.capitalize() for w in name.split())
