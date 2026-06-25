"""Photosentinel (msc.imagegallery.co) extractor.

Source URLs look like: https://msc.imagegallery.co/gallery/#/installation/19493
                      https://<hostname>/gallery/#/installation/<id>

Flow:
  1. GET https://{hostname}/api/login/apiKey  → returns
     {user_api_key: {api_key, expiry_utc}, api_server_url}
  2. GET {api_server_url}v1/installations/{id} with
     `Authorization: apiKey <api_key>`
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

_API_KEY_CACHE: dict[str, tuple[str, str, float]] = {}  # hostname → (api_key, api_server_url, expires_at)
_REFRESH_SLACK = 60  # refresh 1 min before expiry


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


def _parse_iso_to_epoch(iso: str) -> float:
    """Parse an ISO8601 UTC timestamp like 2026-06-25T23:16:14.4911541Z to a unix epoch."""
    try:
        # Trim sub-second precision past 6 digits (Python max) and normalize Z
        s = iso.rstrip("Z")
        # Truncate fractional seconds to 6 digits
        if "." in s:
            head, frac = s.split(".", 1)
            s = f"{head}.{frac[:6]}"
        # Make tz-aware
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return time.time() + 600  # default 10 min ahead


def _get_api_key(hostname: str) -> tuple[str, str] | None:
    """Return (api_key, api_server_url) for the hostname, cached until expiry."""
    now = time.time()
    cached = _API_KEY_CACHE.get(hostname)
    if cached and cached[2] - _REFRESH_SLACK > now:
        return cached[0], cached[1]

    url = f"https://{hostname}/api/login/apiKey"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; WildSight/1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        logger.warning("Photosentinel apiKey fetch failed for %s: %s", hostname, e)
        return None

    if not payload.get("ok"):
        logger.warning("Photosentinel apiKey response not ok for %s: %s", hostname, payload)
        return None

    user_api_key = payload.get("user_api_key") or {}
    api_key = user_api_key.get("api_key")
    expiry_iso = user_api_key.get("expiry_utc") or user_api_key.get("expiry")
    api_server_url = (payload.get("api_server_url") or "https://api.photosentinel.com/").rstrip("/") + "/"

    if not api_key:
        logger.warning("Photosentinel apiKey response missing api_key: %s", payload)
        return None

    expires_at = _parse_iso_to_epoch(expiry_iso) if expiry_iso else now + 600
    _API_KEY_CACHE[hostname] = (api_key, api_server_url, expires_at)
    return api_key, api_server_url


def _fetch_latest_photo_url(hostname: str, installation_id: str) -> str | None:
    cached = _get_api_key(hostname)
    if not cached:
        return None
    api_key, api_server_url = cached

    req = urllib.request.Request(
        f"{api_server_url}v1/installations/{installation_id}",
        headers={
            "Authorization": f"apiKey {api_key}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; WildSight/1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        # Token might be invalid — drop the cache so the next call re-auths
        _API_KEY_CACHE.pop(hostname, None)
        logger.warning("Photosentinel installation fetch failed for %s/%s: %s",
                       hostname, installation_id, e)
        return None

    installation = payload.get("installation") or {}
    latest = installation.get("latest_photo") or {}
    return latest.get("original_url") or latest.get("preview_url") or latest.get("thumb_url")


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
        req = urllib.request.Request(
            photo_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WildSight/1.0)"},
        )
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
