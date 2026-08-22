"""Behavioural tests for EventTracker against a stubbed Supabase client."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import events
from events import EventTracker


class FakeTable:
    def __init__(self, store, log):
        self._store, self._log = store, log
        self._op = None
        self._payload = None
        self._filters = {}

    def insert(self, row):
        self._op, self._payload = "insert", row
        return self

    def update(self, payload):
        self._op, self._payload = "update", payload
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def is_(self, col, _val):
        self._filters[col] = "null"
        return self

    def execute(self):
        if self._op == "insert":
            row = dict(self._payload)
            row["id"] = str(uuid.uuid4())
            row.setdefault("ended_at", None)
            self._store[row["id"]] = row
            self._log.append(("insert", row["common_name"]))
            return type("R", (), {"data": [row]})()

        touched = []
        for rid, row in self._store.items():
            if "id" in self._filters and rid != self._filters["id"]:
                continue
            if self._filters.get("ended_at") == "null" and row.get("ended_at") is not None:
                continue
            row.update(self._payload)
            touched.append(row)
        self._log.append(("update", tuple(sorted(self._payload))))
        return type("R", (), {"data": touched})()


class FakeClient:
    def __init__(self):
        self.store, self.log = {}, []

    def table(self, _name):
        return FakeTable(self.store, self.log)

    def rows(self):
        return list(self.store.values())


def animal(label, common, conf):
    return {"category": "animal", "species_label": label, "common_name": common, "confidence": conf}


BLANK = {"category": "blank", "species_label": None, "common_name": None, "confidence": 0.0}
SID = "stream-1"


def check(name, got, want):
    status = "PASS" if got == want else "FAIL"
    print(f"  [{status}] {name}: got {got!r}, want {want!r}")
    return got == want


def main() -> int:
    ok = True
    events.EVENT_FLUSH_FRAMES = 10

    # --- one animal lingering across many frames = ONE event -----------------
    print("lingering animal collapses to one event")
    c, t = FakeClient(), EventTracker()
    for _ in range(40):
        t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.8), "thumb.jpg")
    ok &= check("event rows", len(c.rows()), 1)
    ok &= check("inserts", sum(1 for e in c.log if e[0] == "insert"), 1)
    ok &= check("still open", c.rows()[0]["ended_at"], None)
    # While open, the DB count trails by less than one flush interval; the
    # in-memory count is authoritative until the event closes.
    ok &= check("in-memory count", t._open[SID]["frame_count"], 40)
    lag = 40 - c.rows()[0]["frame_count"]
    ok &= check("db lag < flush interval", lag < events.EVENT_FLUSH_FRAMES, True)
    # Closing must reconcile it exactly.
    t._open[SID]["last_seen"] -= timedelta(seconds=events.EVENT_GAP_SECONDS + 1)
    t.sweep(c)
    ok &= check("frame_count after close", c.rows()[0]["frame_count"], 40)

    # --- a brief blank gap must NOT split the event --------------------------
    print("brief blank gap does not split the sighting")
    c, t = FakeClient(), EventTracker()
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.8), "a.jpg")
    t.observe(c, SID, BLANK, None)          # one empty frame
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.8), "b.jpg")
    ok &= check("event rows", len(c.rows()), 1)

    # --- species change closes and opens -------------------------------------
    print("different species starts a new event")
    c, t = FakeClient(), EventTracker()
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.8), "a.jpg")
    t.observe(c, SID, animal("cervus;elaphus", "Red Deer", 0.7), "b.jpg")
    rows = sorted(c.rows(), key=lambda r: r["common_name"])
    ok &= check("event rows", len(rows), 2)
    ok &= check("bear closed", rows[0]["ended_at"] is not None, True)
    ok &= check("deer open", rows[1]["ended_at"], None)

    # --- absence beyond the gap closes the event -----------------------------
    print("absence beyond EVENT_GAP_SECONDS closes it")
    c, t = FakeClient(), EventTracker()
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.9), "a.jpg")
    t._open[SID]["last_seen"] -= timedelta(seconds=events.EVENT_GAP_SECONDS + 1)
    t.observe(c, SID, BLANK, None)
    ok &= check("closed", c.rows()[0]["ended_at"] is not None, True)
    ok &= check("tracker empty", t.open_count(), 0)

    # --- peak confidence + best thumbnail track the best frame ---------------
    print("peak confidence keeps the most confident frame's image")
    c, t = FakeClient(), EventTracker()
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.55), "low.jpg")
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.92), "high.jpg")
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.60), "mid.jpg")
    ok &= check("peak_confidence", c.rows()[0]["peak_confidence"], 0.92)
    ok &= check("best_thumbnail", c.rows()[0]["best_thumbnail_path"], "high.jpg")

    # --- offline camera is swept ---------------------------------------------
    print("sweep closes events for cameras that stopped reporting")
    c, t = FakeClient(), EventTracker()
    t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.9), "a.jpg")
    t._open[SID]["last_seen"] -= timedelta(seconds=events.EVENT_GAP_SECONDS + 1)
    ok &= check("swept", t.sweep(c), 1)
    ok &= check("closed", c.rows()[0]["ended_at"] is not None, True)

    # --- write volume: 40 frames must not mean 40 writes ---------------------
    print("write volume stays low across a long sighting")
    c, t = FakeClient(), EventTracker()
    for _ in range(60):
        t.observe(c, SID, animal("ursus;arctos", "Brown Bear", 0.8), "t.jpg")
    writes = len(c.log)
    ok &= check("writes for 60 frames (<=8)", writes <= 8, True)
    print(f"        (actual writes: {writes})")

    # --- restart closes dangling events --------------------------------------
    print("close_stale closes events left open by a previous run")
    c = FakeClient()
    c.store["x"] = {"id": "x", "common_name": "Bear", "ended_at": None}
    c.store["y"] = {"id": "y", "common_name": "Deer", "ended_at": "2026-01-01T00:00:00+00:00"}
    ok &= check("closed count", EventTracker().close_stale(c), 1)
    ok &= check("x closed", c.store["x"]["ended_at"] is not None, True)

    print("\nALL PASS" if ok else "\nFAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
