-- Add 7 Ozolio webcams as jpeg-platform sources
INSERT INTO streams (slug, name, description, source_url, embed_url, platform, location_name, country_code, latitude, longitude, is_active, is_live)
VALUES
  ('grouse-mountain-bears-front', 'Bear Habitat Cam Front', 'Grizzly bear habitat at Grouse Mountain, British Columbia.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_LCTK0000070A', 'https://www.ozolio.com/explore/LCTK0000070A', 'jpeg', 'Grouse Mountain, BC', 'CA', 49.38, -123.08, true, true),
  ('grouse-mountain-bear-pond', 'Bear Pond', 'Bear pond cam at Grouse Mountain, Vancouver.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_HQCJ000005B6', 'https://www.ozolio.com/explore/HQCJ000005B6', 'jpeg', 'Grouse Mountain, BC', 'CA', 49.38, -123.08, true, true),
  ('ozolio-madagascar', 'Madagascar Habitat', 'Live cam of lemurs and Madagascar wildlife.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_CIBE00000EA8', 'https://www.ozolio.com/explore/CIBE00000EA8', 'jpeg', 'Zoo Exhibit', 'US', 40.0, -74.0, true, true),
  ('ozolio-sea-otters', 'Sea Otters', 'Live cam of sea otters.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_MDTW00001862', 'https://www.ozolio.com/explore/MDTW00001862', 'jpeg', 'Zoo Exhibit', 'US', 40.0, -74.0, true, true),
  ('oakland-giraffe-habitat', 'Giraffe Habitat', 'Live giraffe habitat cam at Oakland Zoo.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_NRKX000015DD', 'https://www.ozolio.com/explore/NRKX000015DD', 'jpeg', 'Oakland, CA', 'US', 37.75, -122.13, true, true),
  ('african-savanna-palm-desert', 'African Savanna Live', 'African savanna exhibit cam in Palm Desert, California.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_NJNR00000DFE', 'https://www.ozolio.com/explore/NJNR00000DFE', 'jpeg', 'Palm Desert, CA', 'US', 33.72, -116.37, true, true),
  ('georgia-aquarium', 'Georgia Aquarium', 'Live cam from the Georgia Aquarium.', 'https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_ZMZA0000060B', 'https://www.ozolio.com/explore/ZMZA0000060B', 'jpeg', 'Atlanta, GA', 'US', 33.76, -84.39, true, true)
ON CONFLICT (slug) DO NOTHING;
