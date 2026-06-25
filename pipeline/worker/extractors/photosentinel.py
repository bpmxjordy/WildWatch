"""Photosentinel (msc.imagegallery.co) extractor.

Source URLs look like: https://msc.imagegallery.co/gallery/#/installation/19493
                      https://<hostname>/gallery/#/installation/<id>

Flow:
  1. POST guest token to /v1/auth/guest with the project_hostname
  2. GET /v1/installations/<id> with Authorization header
  3. Download installation.latest_photo.original_url
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

API_BASE = "https://api.photosentinel.com/v1"
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}  # hostname → (token, expires_at)
_TOKEN_TTL_SECONDS = 30 * 60  # refresh every 30 min to be safe


def _parse_url(source_url: str) -> tuple[str, str] | None:
    """Extract (hostname, installation_id) from a gallery URL."""
    try:
        parsed = urllib.parse.urlparse(source_url)
        hostname = parsed.hostname
        if not hostname:
            return None
        # The installation id lives in the fragment: #/installation/<id>
        fragment = parsed.fragment or parsed.path
        m = re.search(r"/installation/(\d+)", fragment)
        if not m:
            # Maybe user pasted just the id, or the API URL directly
            m = re.search(r"/installations?/(\d+)", source_url)
        if not m:
            return None
        return hostname, m.group(1)
    except Exception:
        return None


def _get_token(hostname: str) -> str | None:
    """Return a cached or freshly-fetched guest API token for the hostname."""
    now = time.time()
    cached = _TOKEN_CACHE.get(hostname)
    if cached and cached[1] > now:
        return cached[0]

    body = json.dumps({"project_hostname": hostname}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/auth/guest",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "WildSight/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        logger.warning("Photosentinel auth failed for %s: %s", hostname, e)
        return None

    token = payload.get("token")
    if not token:
        logger.warning("Photosentinel auth returned no token: %s", payload)
        return None

    _TOKEN_CACHE[hostname] = (token, now + _TOKEN_TTL_SECONDS)
    return token


def _fetch_latest_photo_url(hostname: str, installation_id: str) -> str | None:
    token = _get_token(hostname)
    if not token:
        return None
    req = urllib.request.Request(
        f"{API_BASE}/installations/{installation_id}",
        headers={"Authorization": token, "User-Agent": "WildSight/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        # Token might be expired — drop the cache so the next call re-auths
        _TOKEN_CACHE.pop(hostname, None)
        logger.warning("Photosentinel installation fetch failed for %s/%s: %s",
                       hostname, installation_id, e)
        return None

    installation = payload.get("installation", {})
    latest = installation.get("latest_photo") or {}
    return latest.get("original_url") or latest.get("url")


def extract_photosentinel(source_url: str, output_path: str) -> bool:
    parsed = _parse_url(source_url)
    if not parsed:
        logger.warning("Could not parse Photosentinel URL: %s", source_url)
        return False
    hostname, installation_id = parsed

    photo_url = _fetch_latest_photo_url(hostname, installation_id)
    if not photo_url:
        return False

    try:
        req = urllib.request.Request(photo_url, headers={"User-Agent": "WildSight/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < 1000:
            logger.warning("Photosentinel image too small (%d bytes) from %s",
                           len(data), photo_url)
            return False
        Path(output_path).write_bytes(data)
        return True
    except Exception as e:
        logger.warning("Photosentinel download failed for %s: %s", photo_url, e)
        return False
