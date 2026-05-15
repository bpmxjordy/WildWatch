-- WildWatch initial schema

-- Streams table
CREATE TABLE streams (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    embed_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    platform TEXT DEFAULT 'youtube',
    location_name TEXT,
    country_code TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    thumbnail_url TEXT,
    is_active BOOLEAN DEFAULT true,
    is_live BOOLEAN DEFAULT true,

    latest_detection_species TEXT,
    latest_detection_common_name TEXT,
    latest_detection_confidence DOUBLE PRECISION,
    latest_detection_category TEXT,
    latest_detection_thumbnail_url TEXT,
    latest_detection_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_streams_active ON streams(is_active) WHERE is_active = true;
CREATE INDEX idx_streams_latest_detection ON streams(latest_detection_at DESC NULLS LAST);
CREATE INDEX idx_streams_category ON streams(latest_detection_category);
CREATE INDEX idx_streams_slug ON streams(slug);

-- Detections table
CREATE TABLE detections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    species_label TEXT,
    common_name TEXT,
    category TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    classification_confidence DOUBLE PRECISION,
    prediction_source TEXT,
    bbox_x1 DOUBLE PRECISION,
    bbox_y1 DOUBLE PRECISION,
    bbox_x2 DOUBLE PRECISION,
    bbox_y2 DOUBLE PRECISION,
    thumbnail_path TEXT,
    inference_time_ms DOUBLE PRECISION,
    detected_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_detections_stream ON detections(stream_id, detected_at DESC);
CREATE INDEX idx_detections_category ON detections(category) WHERE category = 'animal';
CREATE INDEX idx_detections_species ON detections(common_name) WHERE common_name IS NOT NULL;

-- Species events table
CREATE TABLE species_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    species_label TEXT NOT NULL,
    common_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    peak_confidence DOUBLE PRECISION,
    frame_count INTEGER DEFAULT 1,
    best_thumbnail_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_species_events_stream ON species_events(stream_id, started_at DESC);
CREATE INDEX idx_species_events_species ON species_events(common_name);
CREATE INDEX idx_species_events_active ON species_events(ended_at) WHERE ended_at IS NULL;

-- Row Level Security
ALTER TABLE streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE species_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read streams" ON streams FOR SELECT USING (true);
CREATE POLICY "Public read detections" ON detections FOR SELECT USING (true);
CREATE POLICY "Public read species_events" ON species_events FOR SELECT USING (true);

CREATE POLICY "Service write streams" ON streams FOR ALL TO service_role USING (true);
CREATE POLICY "Service write detections" ON detections FOR ALL TO service_role USING (true);
CREATE POLICY "Service write species_events" ON species_events FOR ALL TO service_role USING (true);

-- Storage bucket for thumbnails
INSERT INTO storage.buckets (id, name, public) VALUES ('thumbnails', 'thumbnails', true);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER streams_updated_at
    BEFORE UPDATE ON streams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
