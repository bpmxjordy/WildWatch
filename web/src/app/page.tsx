import { createServerClient } from "@/lib/supabase/server";
import StreamGrid from "@/components/StreamGrid";

export const revalidate = 0;

export default async function HomePage() {
  const supabase = await createServerClient();
  const { data: streams } = await supabase
    .from("streams")
    .select("*")
    .eq("is_active", true)
    .order("latest_detection_at", { ascending: false, nullsFirst: false });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Wildlife Livestreams</h1>
        <p className="mt-2 text-gray-400">
          Real-time AI detection across 100+ wildlife cameras. See which streams have animals right now.
        </p>
      </div>
      <StreamGrid initialStreams={streams ?? []} />
    </div>
  );
}
