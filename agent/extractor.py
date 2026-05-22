from __future__ import annotations

import logging
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from threading import Lock

from config import FRAME_MAX_DIMENSION

logger = logging.getLogger(__name__)

_url_cache: dict[str, tuple[str, float]] = {}
_cache_lock = Lock()
URL_CACHE_TTL = 10800  # 3 hours — YouTube HLS URLs typically valid for 6h


# ---------------------------------------------------------------------------
# Platform-specific frame extraction
# ---------------------------------------------------------------------------

def _extract_jpeg(source_url: str, output_path: str) -> bool:
    """Download a single JPEG snapshot (e.g. HDOnTap cameras)."""
    try:
        req = urllib.request.Request(source_url, headers={"User-Agent": "WildWatch/1.0"})
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


def _extract_mjpeg(source_url: str, output_path: str) -> bool:
    """Grab one frame from an MJPEG stream using ffmpeg."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", source_url,
                "-frames:v", "1",
                "-q:v", "2",
                "-vf", f"scale='min({FRAME_MAX_DIMENSION},iw)':-2",
                output_path,
            ],
            timeout=15,
            capture_output=True,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg mjpeg failed: %s", result.stderr.decode(errors="replace")[:200])
            return False
        return Path(output_path).exists()
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg mjpeg timed out for %s", source_url)
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found")
        return False


def _resolve_hls_chunklist(master_url: str) -> str | None:
    """Fetch an HLS master playlist and return the highest-bandwidth chunklist URL.

    Wowza servers embed rotating tokens in chunklist filenames, so we must
    fetch the master playlist each time to get a fresh, valid chunklist URL.
    """
    try:
        req = urllib.request.Request(master_url, headers={"User-Agent": "WildWatch/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to fetch HLS master playlist %s: %s", master_url, e)
        return None

    # Parse variant streams — pick the first chunklist (highest bandwidth listed first)
    from urllib.parse import urljoin
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return urljoin(master_url, line)
    return None


def _extract_hls(source_url: str, output_path: str) -> bool:
    """Grab one frame from an HLS (.m3u8) stream using ffmpeg.

    For Wowza-style streams with rotating chunklist tokens, we resolve a
    fresh chunklist URL from the master playlist before passing to ffmpeg.
    """
    # Try resolving a fresh chunklist from the master playlist first
    stream_url = _resolve_hls_chunklist(source_url)
    if not stream_url:
        stream_url = source_url  # Fallback to direct URL

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", stream_url,
                "-frames:v", "1",
                "-q:v", "2",
                "-vf", f"scale='min({FRAME_MAX_DIMENSION},iw)':-2",
                output_path,
            ],
            timeout=20,
            capture_output=True,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg hls failed: %s", result.stderr.decode(errors="replace")[:200])
            return False
        return Path(output_path).exists()
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg hls timed out for %s", source_url)
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found")
        return False


# ---------------------------------------------------------------------------
# YouTube extraction (yt-dlp → ffmpeg)
# ---------------------------------------------------------------------------

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


def _extract_youtube(source_url: str, output_path: str) -> bool:
    """Extract a frame from YouTube via yt-dlp + ffmpeg."""
    direct_url = _get_direct_url(source_url)
    if not direct_url:
        return False

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", direct_url,
                "-frames:v", "1",
                "-q:v", "2",
                "-vf", f"scale='min({FRAME_MAX_DIMENSION},iw)':-2",
                output_path,
            ],
            timeout=15,
            capture_output=True,
        )
        if result.returncode != 0:
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_EXTRACTORS = {
    "jpeg": _extract_jpeg,
    "mjpeg": _extract_mjpeg,
    "hls": _extract_hls,
    "youtube": _extract_youtube,
}


def extract_frame(source_url: str, output_path: str, platform: str = "youtube") -> bool:
    """Extract a single frame. Platform selects the extraction strategy."""
    extractor = _EXTRACTORS.get(platform)
    if extractor is None:
        logger.error("Unknown platform %r for %s", platform, source_url)
        return False
    return extractor(source_url, output_path)
