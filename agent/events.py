"""
Species presence events.

`consensus.py` decides *what* the animal on a camera is called, smoothing
per-frame classifier flip-flopping into one stable label. It has no notion of
an episode beginning or ending, so every frame still landed in `detections` as
though it were a fresh sighting -- a bear standing in a river for twenty minutes
counted as twenty separate detections.

This module adds the missing layer: one `species_events` row per continuous
presence, updated in place while the animal stays, closed when it leaves. The
table and its partial index on open events (`ended_at IS NULL`) already existed;
nothing had ever written to them.

`detections` is still written per frame -- it's the raw signal the hourly
activity aggregation reads. Events sit alongside it as the de-duplicated view.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from supabase import Client

logger = logging.getLogger(__name__)

# How long a camera may go without an animal before the open event is closed.
# Generous by default: a fixed camera loses its subject behind a tree or to a
# bad frame constantly, and re-opening an event for that would recreate exactly
# the fragmentation this is meant to remove.
EVENT_GAP_SECONDS = int(os.getenv("EVENT_GAP_SECONDS", "300"))

# An open event is flushed to the DB on open, on close, whenever peak
# confidence improves, and every N frames -- so `ended_at IS NULL` rows stay
# reasonably fresh for "what's on screen right now" queries without paying a
# write per frame.
EVENT_FLUSH_FRAMES = int(os.getenv("EVENT_FLUSH_FRAMES", "10"))


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class EventTracker:
    """Maintains one open species_events row per stream."""

    def __init__(self) -> None:
        self._open: dict[str, dict] = {}

    # ------------------------------------------------------------------ setup

    def close_stale(self, supabase: Client) -> int:
        """Close events left open by a previous run.

        The agent can't know whether an animal was still present when it was
        last stopped, so anything still open at startup is closed at `now`.
        Only events open at the moment of a restart are affected.
        """
        try:
            rows = (
                supabase.table("species_events")
                .update({"ended_at": _iso(datetime.now(timezone.utc))})
                .is_("ended_at", "null")
                .execute()
            )
            n = len(rows.data or [])
            if n:
                logger.info("Closed %d event(s) left open by a previous run", n)
            return n
        except Exception:
            logger.exception("Failed closing stale events")
            return 0

    # ---------------------------------------------------------------- observe

    def observe(
        self,
        supabase: Client,
        stream_id: str,
        committed: dict,
        thumbnail_url: str | None,
    ) -> None:
        """Fold one frame's committed label into this stream's event state."""
        now = datetime.now(timezone.utc)
        current = self._open.get(stream_id)
        is_animal = committed.get("category") == "animal"

        if not is_animal:
            # Don't close on the first empty frame -- wait out the gap, so a
            # brief occlusion doesn't split one sighting into two events.
            if current and (now - current["last_seen"]) >= timedelta(seconds=EVENT_GAP_SECONDS):
                self._close(supabase, stream_id, current, now)
            return

        label = committed.get("species_label") or committed.get("common_name") or "Animal"
        common = committed.get("common_name") or "Animal"
        confidence = float(committed.get("confidence") or 0.0)

        if current and current["species_label"] == label:
            self._extend(supabase, current, confidence, thumbnail_url, now)
            return

        # A different species means the previous one is gone, even mid-window.
        if current:
            self._close(supabase, stream_id, current, now)

        self._open_event(supabase, stream_id, label, common, confidence, thumbnail_url, now)

    # --------------------------------------------------------------- internals

    def _open_event(
        self,
        supabase: Client,
        stream_id: str,
        label: str,
        common: str,
        confidence: float,
        thumbnail_url: str | None,
        now: datetime,
    ) -> None:
        row = {
            "stream_id": stream_id,
            "species_label": label,
            "common_name": common,
            "started_at": _iso(now),
            "peak_confidence": confidence,
            "frame_count": 1,
            "best_thumbnail_path": thumbnail_url,
        }
        try:
            result = supabase.table("species_events").insert(row).execute()
        except Exception:
            logger.exception("[%s] Failed opening event for %s", stream_id, common)
            return

        data = (result.data or [{}])[0]
        self._open[stream_id] = {
            "id": data.get("id"),
            "species_label": label,
            "common_name": common,
            "peak_confidence": confidence,
            "best_thumbnail_path": thumbnail_url,
            "frame_count": 1,
            "started_at": now,
            "last_seen": now,
            "unflushed": 0,
        }
        logger.info("[event] %s opened on %s", common, stream_id)

    def _extend(
        self,
        supabase: Client,
        current: dict,
        confidence: float,
        thumbnail_url: str | None,
        now: datetime,
    ) -> None:
        current["frame_count"] += 1
        current["last_seen"] = now
        current["unflushed"] += 1

        improved = confidence > current["peak_confidence"]
        if improved:
            current["peak_confidence"] = confidence
            # Keep the frame the model was most sure about as the event's image.
            if thumbnail_url:
                current["best_thumbnail_path"] = thumbnail_url

        if improved or current["unflushed"] >= EVENT_FLUSH_FRAMES:
            self._flush(supabase, current)

    def _flush(self, supabase: Client, current: dict, ended_at: datetime | None = None) -> None:
        if not current.get("id"):
            return
        payload = {
            "frame_count": current["frame_count"],
            "peak_confidence": current["peak_confidence"],
            "best_thumbnail_path": current["best_thumbnail_path"],
        }
        if ended_at is not None:
            payload["ended_at"] = _iso(ended_at)
        try:
            supabase.table("species_events").update(payload).eq("id", current["id"]).execute()
            current["unflushed"] = 0
        except Exception:
            logger.exception("Failed updating event %s", current["id"])

    def _close(self, supabase: Client, stream_id: str, current: dict, now: datetime) -> None:
        # The animal was last actually seen at `last_seen`; the frames since
        # were empty, so that -- not `now` -- is when the sighting ended.
        self._flush(supabase, current, ended_at=current["last_seen"])
        duration = (current["last_seen"] - current["started_at"]).total_seconds()
        logger.info(
            "[event] %s closed on %s after %.0fs over %d frames",
            current["common_name"], stream_id, duration, current["frame_count"],
        )
        self._open.pop(stream_id, None)

    def sweep(self, supabase: Client) -> int:
        """Close events whose stream has stopped reporting.

        `observe` can only close an event when a *new* frame arrives showing
        nothing. A camera that goes offline stops producing frames entirely, so
        without this its event would stay open indefinitely and pollute the
        "currently on screen" query.
        """
        now = datetime.now(timezone.utc)
        stale = [
            (sid, ev)
            for sid, ev in self._open.items()
            if (now - ev["last_seen"]) >= timedelta(seconds=EVENT_GAP_SECONDS)
        ]
        for stream_id, event in stale:
            self._close(supabase, stream_id, event, now)
        return len(stale)

    # ------------------------------------------------------------------ status

    def open_count(self) -> int:
        return len(self._open)
