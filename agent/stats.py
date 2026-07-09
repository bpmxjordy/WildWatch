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
    """Compute hourly activity and species breakdown for all time periods."""
    now = datetime.now(timezone.utc)
    stats: dict = {}

    for period_key, delta in PERIODS.items():
        cutoff = (now - delta).isoformat()

        # Hourly activity
        result = supabase.table("detections").select(
            "detected_at"
        ).eq(
            "stream_id", stream_id
        ).eq(
            "category", "animal"
        ).gte(
            "confidence", MIN_CONFIDENCE
        ).gte(
            "detected_at", cutoff
        ).limit(10000).execute()

        hourly = [0] * 24
        for row in result.data or []:
            dt = datetime.fromisoformat(row["detected_at"].replace("Z", "+00:00"))
            hourly[dt.hour] += 1

        # Species breakdown
        species_result = supabase.table("detections").select(
            "common_name, confidence"
        ).eq(
            "stream_id", stream_id
        ).eq(
            "category", "animal"
        ).gte(
            "confidence", MIN_CONFIDENCE
        ).gte(
            "detected_at", cutoff
        ).not_.is_("common_name", "null").limit(10000).execute()

        species_map: dict[str, dict] = {}
        for row in species_result.data or []:
            name = row["common_name"]
            if name not in species_map:
                species_map[name] = {"count": 0, "total_conf": 0.0}
            species_map[name]["count"] += 1
            species_map[name]["total_conf"] += row["confidence"]

        species = sorted(
            [
                {
                    "common_name": k,
                    "count": v["count"],
                    "avg_confidence": round(v["total_conf"] / v["count"], 3),
                }
                for k, v in species_map.items()
            ],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

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
