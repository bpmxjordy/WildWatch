from __future__ import annotations

import logging
import time
from supabase import Client

logger = logging.getLogger(__name__)

_stream_cache: list[dict] = []
_cache_ts: float = 0.0
STREAM_CACHE_TTL = 300  # 5 minutes


def fetch_active_streams(supabase: Client) -> list[dict]:
    global _stream_cache, _cache_ts
    now = time.time()
    if _stream_cache and now - _cache_ts < STREAM_CACHE_TTL:
        return _stream_cache
    result = supabase.table("streams").select("*").eq("is_active", True).execute()
    _stream_cache = result.data
    _cache_ts = now
    logger.info("Refreshed stream list: %d active streams", len(result.data))
    return _stream_cache


def invalidate_stream_cache() -> None:
    global _stream_cache, _cache_ts
    _stream_cache = []
    _cache_ts = 0.0
