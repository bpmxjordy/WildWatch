from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamState:
    last_processed: float = 0.0
    last_offline: float = 0.0
    consecutive_failures: int = 0


class Scheduler:
    def __init__(self, offline_retry_interval: int = 300):
        self._states: dict[str, StreamState] = {}
        self._offline_retry = offline_retry_interval

    def get_ready_streams(self, streams: list[dict]) -> list[dict]:
        now = time.time()
        ready = []
        for s in streams:
            sid = s["id"]
            if sid not in self._states:
                self._states[sid] = StreamState()
            state = self._states[sid]

            if state.last_offline and now - state.last_offline < self._offline_retry:
                continue

            interval = s.get("frame_interval_seconds", 60)
            if now - state.last_processed >= interval:
                ready.append(s)

        ready.sort(key=lambda s: self._states[s["id"]].last_processed)
        return ready

    def mark_success(self, stream_id: str) -> None:
        state = self._states.setdefault(stream_id, StreamState())
        state.last_processed = time.time()
        state.consecutive_failures = 0
        state.last_offline = 0.0

    def mark_failure(self, stream_id: str) -> int:
        state = self._states.setdefault(stream_id, StreamState())
        state.last_processed = time.time()
        state.consecutive_failures += 1
        if state.consecutive_failures >= 3:
            state.last_offline = time.time()
            logger.warning("Stream %s marked offline after %d failures", stream_id, state.consecutive_failures)
        return state.consecutive_failures
