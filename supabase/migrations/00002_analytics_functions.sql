-- Analytics RPC functions for camera detail pages

-- Hourly detection counts for the last 24 hours
CREATE OR REPLACE FUNCTION get_hourly_activity(p_stream_id UUID)
RETURNS TABLE (hour INT, detection_count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT
    EXTRACT(HOUR FROM d.detected_at AT TIME ZONE 'UTC')::INT AS hour,
    COUNT(*)::BIGINT AS detection_count
  FROM detections d
  WHERE d.stream_id = p_stream_id
    AND d.detected_at >= NOW() - INTERVAL '24 hours'
    AND d.category = 'animal'
    AND d.confidence >= 0.5
  GROUP BY EXTRACT(HOUR FROM d.detected_at AT TIME ZONE 'UTC')
  ORDER BY hour;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Species breakdown for the last 7 days
CREATE OR REPLACE FUNCTION get_species_breakdown(p_stream_id UUID)
RETURNS TABLE (
  common_name TEXT,
  species_label TEXT,
  detection_count BIGINT,
  avg_confidence DOUBLE PRECISION,
  last_seen TIMESTAMPTZ
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.common_name,
    d.species_label,
    COUNT(*)::BIGINT AS detection_count,
    AVG(d.confidence)::DOUBLE PRECISION AS avg_confidence,
    MAX(d.detected_at) AS last_seen
  FROM detections d
  WHERE d.stream_id = p_stream_id
    AND d.detected_at >= NOW() - INTERVAL '7 days'
    AND d.category = 'animal'
    AND d.confidence >= 0.5
    AND d.common_name IS NOT NULL
  GROUP BY d.common_name, d.species_label
  ORDER BY detection_count DESC
  LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant public access (matches existing RLS policy)
GRANT EXECUTE ON FUNCTION get_hourly_activity(UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_species_breakdown(UUID) TO anon, authenticated;
