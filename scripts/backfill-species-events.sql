-- One-time backfill of species_events from historical detections.
--
-- species_events was never written to, so it starts empty while detections holds
-- ~179k rows of history. This reconstructs the sightings that already happened
-- by collapsing runs of consecutive same-species detections on a camera into a
-- single event (a gaps-and-islands grouping).
--
-- Side benefit: the Ozolio cameras serve a snapshot cached ~15 minutes while the
-- agent samples every 60s, so the same image was inferred and recorded ~15 times
-- over. Collapsing runs into events removes that inflation retroactively.
--
-- Run these steps in order in the Supabase SQL Editor. Steps 1 and 2 are
-- read-only; only step 3 writes.

-- ---------------------------------------------------------------- STEP 1
-- Build the reconstruction as a view so the logic is defined once.
-- The 5 minute gap matches EVENT_GAP_SECONDS in agent/events.py, so backfilled
-- history and live events follow the same rule. Change both together.

CREATE OR REPLACE VIEW species_events_backfill AS
WITH ordered AS (
  SELECT
    d.stream_id,
    d.common_name,
    d.species_label,
    d.confidence,
    d.thumbnail_path,
    d.detected_at,
    LAG(d.detected_at) OVER w AS prev_at,
    LAG(d.common_name) OVER w AS prev_name
  FROM detections d
  WHERE d.category = 'animal'
    AND d.common_name IS NOT NULL
  WINDOW w AS (PARTITION BY d.stream_id ORDER BY d.detected_at)
),
marked AS (
  SELECT *,
    CASE
      WHEN prev_at IS NULL
        OR prev_name IS DISTINCT FROM common_name
        OR detected_at - prev_at > INTERVAL '5 minutes'
      THEN 1 ELSE 0
    END AS starts_new
  FROM ordered
),
grouped AS (
  SELECT *,
    SUM(starts_new) OVER (
      PARTITION BY stream_id ORDER BY detected_at
      ROWS UNBOUNDED PRECEDING
    ) AS run_id
  FROM marked
)
SELECT
  stream_id,
  common_name,
  MIN(detected_at) AS started_at,
  MAX(detected_at) AS ended_at,
  MAX(confidence)  AS peak_confidence,
  -- detections holds one row per bounding box, so several rows can share a
  -- timestamp. Count frames, not boxes.
  COUNT(DISTINCT detected_at)::INT AS frame_count,
  (ARRAY_AGG(species_label  ORDER BY confidence DESC NULLS LAST))[1] AS species_label,
  (ARRAY_AGG(thumbnail_path ORDER BY confidence DESC NULLS LAST))[1] AS best_thumbnail_path
FROM grouped
GROUP BY stream_id, common_name, run_id;


-- ---------------------------------------------------------------- STEP 2
-- Preview. Read-only -- check these numbers before writing anything.
-- avg_frames_per_event well above 1 is the duplicate inflation being collapsed.

SELECT
  COUNT(*)                                                  AS events_to_create,
  SUM(frame_count)                                          AS frames_collapsed,
  ROUND(AVG(frame_count), 1)                                AS avg_frames_per_event,
  ROUND(AVG(EXTRACT(EPOCH FROM (ended_at - started_at))))   AS avg_seconds,
  ROUND(MAX(EXTRACT(EPOCH FROM (ended_at - started_at))))   AS longest_seconds,
  COUNT(DISTINCT common_name)                               AS distinct_species
FROM species_events_backfill;


-- ---------------------------------------------------------------- STEP 3
-- The write. Safe to re-run: NOT EXISTS skips anything already inserted.

INSERT INTO species_events (
  stream_id, species_label, common_name,
  started_at, ended_at, peak_confidence, frame_count, best_thumbnail_path
)
SELECT
  b.stream_id, b.species_label, b.common_name,
  b.started_at, b.ended_at, b.peak_confidence, b.frame_count, b.best_thumbnail_path
FROM species_events_backfill b
WHERE NOT EXISTS (
  SELECT 1 FROM species_events x
  WHERE x.stream_id  = b.stream_id
    AND x.started_at = b.started_at
    AND x.common_name = b.common_name
);


-- ---------------------------------------------------------------- STEP 4
-- Optional tidy-up once you're happy with the result.
-- DROP VIEW species_events_backfill;
