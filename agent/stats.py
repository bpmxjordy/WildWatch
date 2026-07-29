"""Pre-calculate activity stats once per day to reduce API calls."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from supabase import Client

logger = logging.getLogger(__name__)

PERIODS = {
    "24h": timedelta(hours=24),
    "48h": timedelta(hours=48),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

MIN_CONFIDENCE = 0.5


def compute_stream_stats(supabase: Client, stream_id: str) -> dict:
    """Compute hourly activity and species breakdown for all time periods.

    Uses server-side SQL aggregation (GROUP BY via RPCs) rather than fetching
    raw rows, so counts scan ALL matching detections instead of being capped at
    the 1000-row REST limit — and transfer only the small grouped result.
    """
    now = datetime.now(timezone.utc)
    stats: dict = {}

    for period_key, delta in PERIODS.items():
        since = (now - delta).isoformat()

        # Hourly activity (24 grouped rows)
        hourly_rows = supabase.rpc(
            "get_hourly_since", {"p_stream_id": stream_id, "p_since": since}
        ).execute().data or []
        hourly = [0] * 24
        for row in hourly_rows:
            h = row["hour"]
            if 0 <= h < 24:
                hourly[h] = row["detection_count"]

        # Species breakdown (<=10 grouped rows)
        species_rows = supabase.rpc(
            "get_species_since", {"p_stream_id": stream_id, "p_since": since}
        ).execute().data or []
        species = [
            {
                "common_name": row["common_name"],
                "count": row["detection_count"],
                "avg_confidence": round(row["avg_confidence"] or 0, 3),
            }
            for row in species_rows
        ]

        stats[period_key] = {
            "hourly": hourly,
            "total": sum(hourly),
            "species": species,
        }

    return stats


def refresh_all_stats(supabase: Client) -> None:
    """Compute and store stats for all active streams."""
    result = supabase.table("streams").select("id").eq("is_active", True).execute()
    streams = result.data or []
    now = datetime.now(timezone.utc).isoformat()

    logger.info("Computing stats for %d streams...", len(streams))

    for stream in streams:
        stream_id = stream["id"]
        try:
            stats = compute_stream_stats(supabase, stream_id)
            supabase.table("stream_stats").upsert({
                "stream_id": stream_id,
                "stats": json.dumps(stats),
                "computed_at": now,
            }).execute()
        except Exception:
            logger.exception("Failed to compute stats for %s", stream_id)

    logger.info("Stats refresh complete.")
