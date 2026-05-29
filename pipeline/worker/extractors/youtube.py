import logging
import os
import subprocess
import time
from threading import Lock

from extractors.base import ffmpeg_single_frame

logger = logging.getLogger(__name__)

_url_cache: dict[str, tuple[str, float]] = {}
_cache_lock = Lock()
URL_CACHE_TTL = 10800


def _get_direct_url(source_url: str) -> str | None:
    now = time.time()
    with _cache_lock:
        if source_url in _url_cache:
            url, ts = _url_cache[source_url]
            if now - ts < URL_CACHE_TTL:
                return url

    try:
        cookies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
        cmd = ["yt-dlp", "--get-url", "-f", "best[height<=720]"]
        if os.path.exists(cookies_path):
            cmd += ["--cookies", cookies_path]
        cmd.append(source_url)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("yt-dlp failed for %s: %s", source_url, result.stderr.strip())
            return None
        direct_url = result.stdout.strip()
        if not direct_url:
            return None
        with _cache_lock:
            _url_cache[source_url] = (direct_url, now)
        return direct_url
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp timed out for %s", source_url)
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found")
        return None


def extract_youtube(source_url: str, output_path: str) -> bool:
    direct_url = _get_direct_url(source_url)
    if not direct_url:
        return False
    success = ffmpeg_single_frame(direct_url, output_path, timeout=15)
    if not success:
        with _cache_lock:
            _url_cache.pop(source_url, None)
    return success
