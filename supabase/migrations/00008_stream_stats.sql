-- Pre-calculated stream activity stats (refreshed daily by the agent)
CREATE TABLE IF NOT EXISTS stream_stats (
  stream_id UUID PRIMARY KEY REFERENCES streams(id) ON DELETE CASCADE,
  stats JSONB NOT NULL DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Allow public read access
ALTER TABLE stream_stats ENABLE ROW LEVEL SECURITY;
CREATE POLICY "stream_stats_public_read" ON stream_stats
  FOR SELECT USING (true);
