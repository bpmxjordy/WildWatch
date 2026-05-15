import { notFound } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import StreamDetailClient from "./StreamDetailClient";

export const revalidate = 0;

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

  return <StreamDetailClient stream={stream} />;
}
