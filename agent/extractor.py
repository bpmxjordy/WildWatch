from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from threading import Lock

from config import FRAME_MAX_DIMENSION

logger = logging.getLogger(__name__)

_url_cache: dict[str, tuple[str, float]] = {}
_cache_lock = Lock()
URL_CACHE_TTL = 10800  # 3 hours — YouTube HLS URLs typically valid for 6h


def _get_direct_url(source_url: str) -> str | None:
    now = time.time()
    with _cache_lock:
        if source_url in _url_cache:
            url, ts = _url_cache[source_url]
            if now - ts < URL_CACHE_TTL:
                return url

    try:
        cookies_path = os.path.join(os.path.dirname(__file__), "cookies.txt")
        cmd = ["yt-dlp", "--get-url", "-f", "best[height<=720]", "--remote-components", "ejs:github"]
        if os.path.exists(cookies_path):
            cmd += ["--cookies", cookies_path]
        cmd.append(source_url)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
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
        logger.error("yt-dlp not found — install it with: pip install yt-dlp")
        return None


def invalidate_cache(source_url: str) -> None:
    with _cache_lock:
        _url_cache.pop(source_url, None)


def extract_frame(source_url: str, output_path: str) -> bool:
    direct_url = _get_direct_url(source_url)
    if not direct_url:
        return False

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                direct_url,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                "-vf",
                f"scale='min({FRAME_MAX_DIMENSION},iw)':-2",
                output_path,
            ],
            timeout=15,
            capture_output=True,
        )
        if result.returncode != 0:
            # Cached URL may have expired — invalidate and let next cycle retry
            invalidate_cache(source_url)
            logger.warning("ffmpeg failed: %s", result.stderr.decode(errors="replace")[:200])
            return False
        return Path(output_path).exists()
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg timed out for %s", source_url)
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found — install it and add to PATH")
        return False
