-- Period-parameterized aggregation used by the agent's daily stats job.
-- Counting happens server-side via GROUP BY, so it scans ALL matching rows
-- (no 1000-row REST cap) while returning only the small grouped result.

CREATE OR REPLACE FUNCTION get_hourly_since(p_stream_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (hour INT, detection_count BIGINT) AS $$
  SELECT
    EXTRACT(HOUR FROM d.detected_at AT TIME ZONE 'UTC')::INT AS hour,
    COUNT(*)::BIGINT AS detection_count
  FROM detections d
  WHERE d.stream_id = p_stream_id
    AND d.detected_at >= p_since
    AND d.category = 'animal'
    AND d.confidence >= 0.5
  GROUP BY 1
  ORDER BY 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_species_since(p_stream_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (
  common_name TEXT,
  detection_count BIGINT,
  avg_confidence DOUBLE PRECISION
) AS $$
  SELECT
    d.common_name,
    COUNT(*)::BIGINT AS detection_count,
    AVG(d.confidence)::DOUBLE PRECISION AS avg_confidence
  FROM detections d
  WHERE d.stream_id = p_stream_id
    AND d.detected_at >= p_since
    AND d.category = 'animal'
    AND d.confidence >= 0.5
    AND d.common_name IS NOT NULL
  GROUP BY d.common_name
  ORDER BY COUNT(*) DESC
  LIMIT 10;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_hourly_since(UUID, TIMESTAMPTZ) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_species_since(UUID, TIMESTAMPTZ) TO anon, authenticated, service_role;
