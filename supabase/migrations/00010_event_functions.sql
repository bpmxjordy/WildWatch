-- Aggregation over species_events (distinct sightings) rather than detections
-- (per-frame samples). The two answer different questions and are deliberately
-- kept apart: "how much movement did this camera see" vs "how many animals
-- actually turned up".
--
-- No pre-computation here. stream_stats exists because detections has hundreds
-- of thousands of rows; species_events holds one row per sighting, so these are
-- cheap enough to run live.

-- Per-species sighting summary for a stream.
CREATE OR REPLACE FUNCTION get_events_since(p_stream_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (
  common_name TEXT,
  sighting_count BIGINT,
  total_seconds DOUBLE PRECISION,
  avg_seconds DOUBLE PRECISION,
  longest_seconds DOUBLE PRECISION,
  peak_confidence DOUBLE PRECISION,
  last_seen TIMESTAMPTZ,
  best_thumbnail_path TEXT
) AS $$
  WITH scoped AS (
    SELECT
      e.common_name,
      e.peak_confidence,
      e.best_thumbnail_path,
      e.started_at,
      -- An open event is still running, so measure it to now().
      EXTRACT(EPOCH FROM (COALESCE(e.ended_at, now()) - e.started_at)) AS seconds
    FROM species_events e
    WHERE e.stream_id = p_stream_id
      AND e.started_at >= p_since
  )
  SELECT
    s.common_name,
    COUNT(*)::BIGINT,
    SUM(s.seconds)::DOUBLE PRECISION,
    AVG(s.seconds)::DOUBLE PRECISION,
    MAX(s.seconds)::DOUBLE PRECISION,
    MAX(s.peak_confidence)::DOUBLE PRECISION,
    MAX(s.started_at),
    -- Thumbnail from the most confident sighting of this species.
    (ARRAY_AGG(s.best_thumbnail_path ORDER BY s.peak_confidence DESC NULLS LAST))[1]
  FROM scoped s
  GROUP BY s.common_name
  ORDER BY COUNT(*) DESC, SUM(s.seconds) DESC;
$$ LANGUAGE sql STABLE SECURITY DEFINER;


-- Sightings per hour of day, bucketed by when each sighting began.
CREATE OR REPLACE FUNCTION get_event_hourly_since(p_stream_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (hour INT, sighting_count BIGINT) AS $$
  SELECT
    EXTRACT(HOUR FROM e.started_at AT TIME ZONE 'UTC')::INT AS hour,
    COUNT(*)::BIGINT
  FROM species_events e
  WHERE e.stream_id = p_stream_id
    AND e.started_at >= p_since
  GROUP BY 1
  ORDER BY 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;


-- Headline totals for a stream over the window.
CREATE OR REPLACE FUNCTION get_event_summary_since(p_stream_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (
  sighting_count BIGINT,
  species_count BIGINT,
  total_seconds DOUBLE PRECISION,
  longest_seconds DOUBLE PRECISION,
  open_count BIGINT
) AS $$
  SELECT
    COUNT(*)::BIGINT,
    COUNT(DISTINCT e.common_name)::BIGINT,
    COALESCE(SUM(EXTRACT(EPOCH FROM (COALESCE(e.ended_at, now()) - e.started_at))), 0)::DOUBLE PRECISION,
    COALESCE(MAX(EXTRACT(EPOCH FROM (COALESCE(e.ended_at, now()) - e.started_at))), 0)::DOUBLE PRECISION,
    COUNT(*) FILTER (WHERE e.ended_at IS NULL)::BIGINT
  FROM species_events e
  WHERE e.stream_id = p_stream_id
    AND e.started_at >= p_since;
$$ LANGUAGE sql STABLE SECURITY DEFINER;


-- Supports the started_at range scans above.
CREATE INDEX IF NOT EXISTS idx_species_events_started
  ON species_events(stream_id, started_at DESC);

GRANT EXECUTE ON FUNCTION get_events_since(UUID, TIMESTAMPTZ) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_event_hourly_since(UUID, TIMESTAMPTZ) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_event_summary_since(UUID, TIMESTAMPTZ) TO anon, authenticated, service_role;
