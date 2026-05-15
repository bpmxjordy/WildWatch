from __future__ import annotations

import logging
from supabase import Client

logger = logging.getLogger(__name__)


def fetch_active_streams(supabase: Client) -> list[dict]:
    result = supabase.table("streams").select("*").eq("is_active", True).execute()
    logger.info("Fetched %d active streams", len(result.data))
    return result.data
