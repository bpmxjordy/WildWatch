import { createServerClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import MapClient from "./MapClient";

export const revalidate = 30;

export const metadata: Metadata = {
  title: "Map — WildWatch",
  description: "Geographic view of all wildlife cameras and detection activity.",
};

export default async function MapPage() {
  const supabase = await createServerClient();
  const { data: streams } = await supabase
    .from("streams")
    .select("*")
    .eq("is_active", true)
    .order("latest_detection_at", { ascending: false, nullsFirst: false });

  return <MapClient streams={streams ?? []} />;
}
