import { notFound } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import StreamDetailClient from "./StreamDetailClient";

export const revalidate = 30;

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  const supabase = await createServerClient();
  const { data: stream } = await supabase
    .from("streams")
    .select("name, description, location_name")
    .eq("slug", slug)
    .single();

  if (!stream) return { title: "Stream Not Found" };

  return {
    title: `${stream.name} — WildWatch`,
    description: stream.description || `Live wildlife cam at ${stream.location_name}`,
  };
}

export default async function StreamPage({ params }: PageProps) {
  const { slug } = await params;
  const supabase = await createServerClient();

  const { data: stream } = await supabase
    .from("streams")
    .select("*")
    .eq("slug", slug)
    .single();

  if (!stream) notFound();

  const { data: detections } = await supabase
    .from("detections")
    .select("*")
    .eq("stream_id", stream.id)
    .order("detected_at", { ascending: false })
    .limit(5);

  return <StreamDetailClient stream={stream} detections={detections ?? []} />;
}
