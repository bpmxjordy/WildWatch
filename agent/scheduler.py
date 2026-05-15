from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from config import FRAME_INTERVAL_SECONDS, OFFLINE_RETRY_INTERVAL

logger = logging.getLogger(__name__)


@dataclass
class StreamState:
    last_processed: float = 0.0
    last_offline: float = 0.0
    consecutive_failures: int = 0


class Scheduler:
    def __init__(self) -> None:
        self._states: dict[str, StreamState] = {}

    def get_next_streams(self, streams: list[dict]) -> list[dict]:
        now = time.time()
        ready = []
        for stream in streams:
            sid = stream["id"]
            if sid not in self._states:
                self._states[sid] = StreamState()
            state = self._states[sid]

            if state.last_offline and now - state.last_offline < OFFLINE_RETRY_INTERVAL:
                continue

            if now - state.last_processed >= FRAME_INTERVAL_SECONDS:
                ready.append(stream)

        ready.sort(key=lambda s: self._states[s["id"]].last_processed)
        return ready

    def mark_processed(self, stream_id: str) -> None:
        state = self._states.setdefault(stream_id, StreamState())
        state.last_processed = time.time()
        state.consecutive_failures = 0
        state.last_offline = 0.0

    def mark_failed(self, stream_id: str) -> None:
        state = self._states.setdefault(stream_id, StreamState())
        state.last_processed = time.time()
        state.consecutive_failures += 1
        if state.consecutive_failures >= 3:
            state.last_offline = time.time()
            logger.warning(
                "Stream %s marked offline after %d failures",
                stream_id,
                state.consecutive_failures,
            )
