-- Add Ozolio Bear Yard cam
INSERT INTO streams (slug, name, description, source_url, embed_url, platform, location_name, country_code, latitude, longitude, is_active, is_live)
VALUES
  ('grouse-mountain-bear-yard', 'Bear Yard Cam', 'Grizzly bear yard cam at Grouse Mountain, British Columbia.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_SGPR0000096C', 'https://www.ozolio.com/explore/SGPR0000096C', 'jpeg', 'Grouse Mountain, BC', 'CA', 49.38, -123.08, true, true)
ON CONFLICT (slug) DO NOTHING;
