import type { MetadataRoute } from "next";
import { createServerClient } from "@/lib/supabase/server";

// Refresh the generated sitemap hourly so new streams/species appear.
export const revalidate = 3600;

const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "https://thewildwatch.vercel.app"
).replace(/\/$/, "");

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "hourly", priority: 1 },
    { url: `${SITE_URL}/map`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/explore`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/species`, lastModified: now, changeFrequency: "daily", priority: 0.6 },
    { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
  ];

  let dynamicRoutes: MetadataRoute.Sitemap = [];
  try {
    const supabase = await createServerClient();
    const [{ data: streams }, { data: species }] = await Promise.all([
      supabase.from("streams").select("slug, updated_at").eq("is_active", true),
      supabase.from("species_events").select("common_name"),
    ]);

    const streamRoutes: MetadataRoute.Sitemap = (streams ?? []).map((s) => ({
      url: `${SITE_URL}/stream/${s.slug}`,
      lastModified: s.updated_at ? new Date(s.updated_at) : now,
      changeFrequency: "hourly",
      priority: 0.7,
    }));

    const speciesNames = Array.from(
      new Set((species ?? []).map((e) => e.common_name).filter(Boolean))
    );
    const speciesRoutes: MetadataRoute.Sitemap = speciesNames.map((name) => ({
      url: `${SITE_URL}/species/${encodeURIComponent(name)}`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.5,
    }));

    dynamicRoutes = [...streamRoutes, ...speciesRoutes];
  } catch {
    // If Supabase is unreachable at build time, still emit the static routes.
  }

  return [...staticRoutes, ...dynamicRoutes];
}
