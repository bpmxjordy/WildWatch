import logging
import urllib.request
from urllib.parse import urljoin

from extractors.base import ffmpeg_single_frame

logger = logging.getLogger(__name__)


def _resolve_chunklist(master_url: str) -> str | None:
    try:
        req = urllib.request.Request(master_url, headers={"User-Agent": "WildSight/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to fetch HLS master playlist %s: %s", master_url, e)
        return None

    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return urljoin(master_url, line)
    return None


def extract_hls(source_url: str, output_path: str) -> bool:
    stream_url = _resolve_chunklist(source_url)
    if not stream_url:
        stream_url = source_url
    return ffmpeg_single_frame(stream_url, output_path, timeout=20)
