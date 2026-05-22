-- Add 4 YouTube wildlife live streams
INSERT INTO streams (slug, name, description, source_url, embed_url, platform, location_name, country_code, latitude, longitude, is_active, is_live)
VALUES
  ('birds-in-the-forest-germany', 'Birds in the Forest', 'Live bird feeder and forest wildlife cam in Germany.', 'https://www.youtube.com/watch?v=RnCAl0mQgqA', 'https://www.youtube.com/embed/RnCAl0mQgqA', 'youtube', 'Germany', 'DE', 51.16, 10.45, true, true),
  ('badgers-badgerwood', 'Badgers Live at BadgerWood', 'Live badger sett camera in the Peak District, UK.', 'https://www.youtube.com/watch?v=Y_Mkegk-K4E', 'https://www.youtube.com/embed/Y_Mkegk-K4E', 'youtube', 'Peak District, UK', 'GB', 53.30, -1.80, true, true),
  ('namibia-namib-desert', 'Namibia: Live Stream Namib Desert', 'Live stream from the Namib Desert, Namibia — oryx, springbok, and desert wildlife.', 'https://www.youtube.com/watch?v=ydYDqZQpim8', 'https://www.youtube.com/embed/ydYDqZQpim8', 'youtube', 'Namib Desert, Namibia', 'NA', -24.75, 15.74, true, true),
  ('masai-mara-safari', 'Live Safari Masai Mara', 'Live safari cam from the Masai Mara National Reserve, Kenya.', 'https://www.youtube.com/watch?v=xXZqU5vnEug', 'https://www.youtube.com/embed/xXZqU5vnEug', 'youtube', 'Masai Mara, Kenya', 'KE', -1.50, 35.15, true, true)
ON CONFLICT (slug) DO NOTHING;
