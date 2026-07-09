"""
Per-camera temporal consensus.

A fixed camera watches a stable habitat, so we decide the displayed label over
a rolling window of recent frames rather than trusting any single frame. This
collapses per-frame classifier flip-flopping into one stable answer, committing
to the deepest taxonomic rank that a majority of recent frames agree on.
"""
from __future__ import annotations

import os
import time
from collections import Counter, defaultdict, deque

from detector import RANK_SEQUENCE, CLASS_COMMON, common_for, tax_from_key

WINDOW = int(os.getenv("CONSENSUS_WINDOW", "15"))        # max frames retained
MIN_FRAMES = int(os.getenv("CONSENSUS_MIN_FRAMES", "3")) # min agreeing frames to commit
FRACTION = float(os.getenv("CONSENSUS_FRACTION", "0.5")) # share of animal frames needed
TTL_SECONDS = int(os.getenv("CONSENSUS_TTL", "3600"))    # forget frames older than 1h


class _Obs:
    __slots__ = ("ts", "category", "lineage", "confidence")

    def __init__(self, category: str, lineage: dict, confidence: float):
        self.ts = time.time()
        self.category = category
        self.lineage = lineage
        self.confidence = confidence


class Consensus:
    """Rolling per-stream voter over frame-level rolled-up classifications."""

    def __init__(self) -> None:
        self._buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=WINDOW))

    def observe(self, stream_id: str, frame: dict) -> dict:
        """Record a frame's rolled-up result and return the committed label."""
        buf = self._buffers[stream_id]
        buf.append(_Obs(frame.get("category", "blank"), frame.get("lineage", {}),
                        float(frame.get("confidence", 0) or 0)))
        # Drop stale observations
        cutoff = time.time() - TTL_SECONDS
        while buf and buf[0].ts < cutoff:
            buf.popleft()
        return self._commit(buf)

    def _commit(self, buf: deque) -> dict:
        if not buf:
            return {"category": "blank", "common_name": None,
                    "species_label": None, "rank": None, "confidence": 0.0}

        # Majority category across the window
        cat_counts = Counter(o.category for o in buf)
        top_cat, _ = cat_counts.most_common(1)[0]

        if top_cat != "animal":
            return {"category": top_cat, "common_name": None,
                    "species_label": None, "rank": None, "confidence": 0.0}

        animals = [o for o in buf if o.category == "animal"]
        n = len(animals)

        # Deepest rank where one lineage has majority support (class handled below)
        for rank in ["species", "genus", "family", "order"]:
            idx = RANK_SEQUENCE.index(rank)
            groups: Counter = Counter()
            confs: dict[tuple, list] = defaultdict(list)
            for o in animals:
                if not o.lineage.get(rank):
                    continue
                key = tuple(o.lineage.get(r, "") for r in RANK_SEQUENCE[: idx + 1])
                groups[key] += 1
                confs[key].append(o.confidence)
            if groups:
                best_key, cnt = groups.most_common(1)[0]
                if cnt >= MIN_FRAMES and cnt / n >= FRACTION:
                    tax = tax_from_key(best_key)
                    avg_conf = sum(confs[best_key]) / len(confs[best_key])
                    return {
                        "category": "animal",
                        "common_name": common_for(rank, tax),
                        "species_label": ";".join(v for v in best_key if v),
                        "rank": rank,
                        "confidence": round(avg_conf, 4),
                    }

        # Fallback: stable class-level generic ("Bird", "Mammal", ...)
        class_counts = Counter(o.lineage.get("class", "") for o in animals if o.lineage.get("class"))
        if class_counts:
            top_class, _ = class_counts.most_common(1)[0]
            avg_conf = sum(o.confidence for o in animals) / n
            return {
                "category": "animal",
                "common_name": CLASS_COMMON.get(top_class, "Animal"),
                "species_label": top_class,
                "rank": "class",
                "confidence": round(avg_conf, 4),
            }

        return {"category": "animal", "common_name": "Animal",
                "species_label": None, "rank": None,
                "confidence": round(sum(o.confidence for o in animals) / n, 4)}
