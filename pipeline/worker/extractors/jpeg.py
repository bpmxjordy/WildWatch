import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_jpeg(source_url: str, output_path: str) -> bool:
    try:
        req = urllib.request.Request(source_url, headers={"User-Agent": "WildSight/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 1000:
            logger.warning("JPEG too small (%d bytes) from %s", len(data), source_url)
            return False
        Path(output_path).write_bytes(data)
        return True
    except Exception as e:
        logger.warning("JPEG download failed for %s: %s", source_url, e)
        return False
