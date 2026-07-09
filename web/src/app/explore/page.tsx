import { createServerClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import ExploreClient from "./ExploreClient";

export const revalidate = 30;

export const metadata: Metadata = {
  title: "Explore — WildWatch",
  description: "Interactive wildlife stream explorer with live detection data.",
};

export default async function ExplorePage() {
  const supabase = await createServerClient();

  const { data: streams } = await supabase
    .from("streams")
    .select("*")
    .eq("is_active", true)
    .order("latest_detection_at", { ascending: false, nullsFirst: false });

  const { data: statsRows } = await supabase
    .from("stream_stats")
    .select("*");

  const statsMap: Record<string, any> = {};
  for (const row of statsRows ?? []) {
    statsMap[row.stream_id] =
      typeof row.stats === "string" ? JSON.parse(row.stats) : row.stats;
  }

  return <ExploreClient streams={streams ?? []} statsMap={statsMap} />;
}
