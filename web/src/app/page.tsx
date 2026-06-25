import { createServerClient } from "@/lib/supabase/server";
import StreamGrid from "@/components/StreamGrid";

export const revalidate = 30;

export default async function HomePage() {
  const supabase = await createServerClient();
  const { data: streams } = await supabase
    .from("streams")
    .select("*")
    .eq("is_active", true)
    .order("latest_detection_at", { ascending: false, nullsFirst: false });

  const liveCount = streams?.filter((s) => s.is_live).length ?? 0;

  return (
    <div>
      <div className="mb-8">
        <span className="mb-2 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-accent-deep before:inline-block before:h-px before:w-4 before:bg-accent-deep">
          Live cameras
        </span>
        <h1 className="font-serif text-[clamp(34px,3.6vw,56px)] font-medium leading-none tracking-tight text-ink">
          Wildlife <em className="font-normal not-italic text-accent-deep">Livestreams</em>
        </h1>
        <p className="mt-3 max-w-[42ch] text-[15.5px] leading-relaxed text-ink-2">
          Real-time AI detection across {streams?.length ?? 0} wildlife cameras.
          <span className="ml-1 font-mono text-[11px] uppercase tracking-wider text-muted">
            {liveCount} live now
          </span>
        </p>
      </div>
      <StreamGrid initialStreams={streams ?? []} />
    </div>
  );
}
